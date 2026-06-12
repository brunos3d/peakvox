"""peakvox/xtts-runtime — FastAPI server.

The fourth Runtime Service PeakVox ships. This server implements the
5-endpoint Runtime Service Contract (ADR-0017 §6) over HTTP/JSON for
Coqui XTTS v2 (``coqui/XTTS-v2``). The model is loaded lazily on the
first inference request; until then the server reports not-ready (503
on /ready) but stays alive (200 on /health).

This file is a near-verbatim sibling of the F5-TTS runtime
(``runtime-registry/f5-tts-base/server.py``): every contract-level
surface (/health, /ready, /v1/metadata, /v1/generate,
/v1/variants/build, error envelope, response headers) is identical.
Only the inference backend changes (Coqui ``TTS`` vs. F5-TTS's
flow-matching pipeline).

THE ONE DELIBERATE DIVERGENCE FROM F5 (Task 30 / ADR-0021):
  XTTS v2 is **CPU-capable**. F5-TTS is CUDA-only and raises
  "cuda_unavailable" when no GPU is present; XTTS does NOT. It selects
  ``cuda`` when ``torch.cuda.is_available()`` and otherwise falls back
  to ``cpu`` (slower, but functional). The descriptor declares
  ``gpu: "optional"`` so the Docker driver honors the global
  "Use GPU (CUDA)" setting: GPU OFF ⇒ the driver hides the device ⇒
  this server transparently runs on CPU. The live device is reported
  as ``substrate`` on /v1/metadata. No setting is ever silently ignored.

Endpoints
---------

  GET  /health                  liveness
  GET  /ready                   readiness (model loaded?)
  POST /v1/generate             inference (returns audio/wav)
  POST /v1/variants/build       501 (deferred to in-process adapter)
  GET  /v1/metadata             capabilities + supported surface
"""

from __future__ import annotations

import io
import logging
import os
import threading
import time
import wave
from datetime import datetime, timezone
from typing import Any, Literal, Optional

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


logger = logging.getLogger("peakvox.xtts_runtime")

# XTTS weights are under the Coqui Public Model License (CPML). The Coqui TTS
# engine prompts interactively for ToS acceptance unless this is set. The
# operator accepts the CPML by installing/enabling the CE-disabled XTTS model
# (the catalog records commercial_use=False); set it here so the container
# starts non-interactively. See ADR-0021 §License.
os.environ.setdefault("COQUI_TOS_AGREED", "1")

_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
_SAMPLE_RATE = 24000  # XTTS v2 outputs 24 kHz mono.

# 17 languages supported by XTTS v2 (coqui/XTTS-v2 model card).
_SUPPORTED_LANGUAGES = [
    "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru",
    "nl", "cs", "ar", "zh-cn", "hu", "ko", "ja", "hi",
]


# ---------------------------------------------------------------------------
# Module-level state (the "model is loaded" singleton)
# ---------------------------------------------------------------------------
#
# _load_state transitions:
#   "unloaded" → "loading" → "ready"   (success)
#                          → "failed"  (load error; message in _load_error)

_tts: Any = None
_device: str = "cpu"
_load_state: Literal["unloaded", "loading", "ready", "failed"] = "unloaded"
_load_error: Optional[str] = None
_load_lock = threading.Lock()

# Serializes inference (enforces max_concurrent_requests: 1). The XTTS GPT
# backbone shares conditioning state across a call and is not safe to run
# concurrently in one process; overlapping calls corrupt each other. FastAPI
# runs sync handlers in a threadpool, so without this lock requests genuinely
# run in parallel. Same posture as the F5-TTS runtime.
_inference_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    """POST /v1/generate request body (ADR-0017 §6.3)."""

    voice_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    artifact_id: Optional[str] = None
    artifact_version: Optional[int] = None
    text: str = Field(..., min_length=1)
    language: str = "en"
    params: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(..., min_length=1)
    callback_url: Optional[str] = None


class BuildVariantRequest(BaseModel):
    """POST /v1/variants/build request body (ADR-0017 §6.4)."""

    voice_id: str = Field(..., min_length=1)
    reference_audio_storage_key: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# XTTS integration (lazy + injectable for tests)
# ---------------------------------------------------------------------------


def _select_device() -> str:
    """Pick the inference device. CUDA when visible, else CPU.

    This is the deliberate divergence from F5-TTS: XTTS supports CPU, so a
    missing GPU is a (slower) fallback, NOT a failure. The Docker driver makes
    the device authoritative — with "Use GPU (CUDA)" OFF the GPU is hidden and
    ``torch.cuda.is_available()`` returns False here, so we run on CPU.
    """
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_xtts() -> Any:
    """Load the Coqui XTTS v2 model onto the selected device.

    The first call imports ``TTS`` and constructs the model + vocoder.
    Subsequent calls return the cached instance. Tests patch ``_tts`` and
    ``_load_state`` to inject a mock without exercising this code path.
    """
    global _tts, _device

    _device = _select_device()
    from TTS.api import TTS  # type: ignore

    logger.info("loading XTTS v2 on device=%s", _device)
    model = TTS(_MODEL_NAME)
    model.to(_device)
    _tts = model
    return _tts


def _ensure_model_loaded() -> bool:
    """Make sure the model is loaded; trigger lazy load if not.

    Returns True if ready; False if the load failed (caller returns 503).
    Idempotent; thread-safe.
    """
    global _load_state, _load_error
    if _load_state == "ready":
        return True
    if _load_state == "loading":
        while _load_state == "loading":
            time.sleep(0.05)
        return _load_state == "ready"
    if _load_state == "failed":
        return False

    with _load_lock:
        if _load_state in ("ready", "loading"):
            return _load_state == "ready"
        _load_state = "loading"
        _load_error = None
        try:
            _load_xtts()
            _load_state = "ready"
            return True
        except Exception as exc:  # noqa: BLE001
            _load_state = "failed"
            _load_error = str(exc)
            logger.exception("xtts model load failed")
            return False


# ---------------------------------------------------------------------------
# Audio encoding
# ---------------------------------------------------------------------------


def _float32_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Encode a float32 mono waveform as 16-bit PCM WAV bytes."""
    audio = np.asarray(audio, dtype=np.float32)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def _default_builtin_speaker() -> Optional[str]:
    """A built-in XTTS studio speaker to use in voice-optional mode.

    XTTS v2 ships studio speakers; when no reference audio is supplied
    (supports_voice_optional) we synthesize with the first available one rather
    than requiring the caller to pick a voice. Returns None if the model
    exposes no speaker list (the caller then errors clearly).
    """
    speakers = getattr(_tts, "speakers", None)
    if speakers:
        try:
            return list(speakers)[0]
        except Exception:  # noqa: BLE001
            return None
    return None


def _run_inference(req: GenerateRequest) -> tuple[np.ndarray, int]:
    """Run XTTS inference. Returns (audio, sample_rate).

    Voice-cloning mode: a reference clip (``params.ref_audio_path``) is passed
    as ``speaker_wav``; XTTS computes conditioning latents and clones the voice.

    Voice-optional mode: with no reference clip, a built-in studio speaker is
    used (supports_voice_optional=True). This mirrors F5-TTS's bundled-default
    fallback, keeping the generate button usable with no voice selected.
    """
    if _tts is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    language = req.language or "en"
    if language not in _SUPPORTED_LANGUAGES:
        # XTTS rejects unknown language codes; fail clearly instead of crashing
        # deep in the engine.
        raise HTTPException(
            status_code=422,
            detail=f"unsupported language {language!r}; supported: {_SUPPORTED_LANGUAGES}",
        )

    params = req.params or {}
    ref_file = params.get("ref_audio_path") or None

    tts_kwargs: dict[str, Any] = {"text": req.text, "language": language}
    if ref_file is not None:
        tts_kwargs["speaker_wav"] = ref_file
    else:
        speaker = _default_builtin_speaker()
        if speaker is None:
            raise HTTPException(
                status_code=422,
                detail="no reference audio supplied and no built-in speaker available",
            )
        tts_kwargs["speaker"] = speaker

    # User-tunable XTTS generation parameters (guard against null values).
    if params.get("temperature") is not None:
        tts_kwargs["temperature"] = float(params["temperature"])
    if params.get("length_penalty") is not None:
        tts_kwargs["length_penalty"] = float(params["length_penalty"])
    if params.get("repetition_penalty") is not None:
        tts_kwargs["repetition_penalty"] = float(params["repetition_penalty"])
    if params.get("top_k") is not None:
        tts_kwargs["top_k"] = int(params["top_k"])
    if params.get("top_p") is not None:
        tts_kwargs["top_p"] = float(params["top_p"])
    if params.get("speed") is not None:
        tts_kwargs["speed"] = float(params["speed"])

    with _inference_lock:
        wav = _tts.tts(**tts_kwargs)

    audio = np.asarray(wav, dtype=np.float32)
    if audio.size == 0:
        raise HTTPException(status_code=500, detail="inference produced no audio")
    return audio, _SAMPLE_RATE


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="peakvox/xtts-runtime",
    version="0.1.0",
    description=(
        "Runtime service for Coqui XTTS v2 — multilingual zero-shot voice "
        "cloning. Implements the 5-endpoint Runtime Service Contract "
        "(ADR-0017 §6). Mirrors the F5-TTS shape with an 'optional' GPU "
        "posture: CUDA when available, CPU fallback otherwise (Task 30)."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe (ADR-0017 §6.1)."""
    return {"status": "alive"}


@app.get("/ready")
def ready() -> Response:
    """Readiness probe (ADR-0017 §6.2)."""
    if _load_state == "ready":
        return JSONResponse(status_code=200, content={"status": "ready"})
    reason = {
        "unloaded": "model_not_loaded",
        "loading": "weights_loading",
        "failed": f"load_failed: {_load_error or 'unknown'}",
    }.get(_load_state, "unknown")
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "reason": reason},
    )


@app.get("/v1/metadata")
def metadata() -> dict[str, Any]:
    """Runtime metadata (ADR-0017 §6.5).

    ``substrate`` reports the LIVE device (``gpu`` when CUDA is active, else
    ``cpu``) so the platform can show the real execution mode — honoring the
    "Use GPU (CUDA)" setting, never silently ignoring it.
    """
    live_substrate = "gpu" if (_load_state == "ready" and _device == "cuda") else (
        "cpu" if _load_state == "ready" else "gpu-optional"
    )
    return {
        "runtime_id": "xtts-v2",
        "model_id": "xtts-v2",
        "capabilities": [
            "tts",
            "voice_cloning",
            "multilingual",
            "reference_audio",
        ],
        "supported_languages": list(_SUPPORTED_LANGUAGES),
        "supported_tags": [],
        "supported_voice_design": [],
        "realization_types": ["source_asset"],
        "build_strategies": [
            {
                "creation_source": "SOURCE_ASSET",
                "can_build": True,
                "requires": ["reference_audio_storage_key"],
            },
        ],
        "max_concurrent_requests": 1,
        "max_text_length": 5000,
        "substrate": live_substrate,
        "min_vram_gb": 4,
    }


def _error_response(
    status_code: int,
    category: str,
    message: str,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """Build the canonical error envelope (ADR-0017 §6.6)."""
    body: dict[str, Any] = {
        "error": {
            "category": category,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    if request_id is not None:
        body["error"]["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


@app.post("/v1/generate")
def generate(req: GenerateRequest) -> Response:
    """Inference endpoint (ADR-0017 §6.3)."""
    if not _ensure_model_loaded():
        return _error_response(
            status_code=503,
            category="not_ready",
            message=f"runtime is not ready: {_load_error or 'model not loaded'}",
            request_id=req.request_id,
        )
    try:
        audio, sample_rate = _run_inference(req)
    except HTTPException as exc:
        category = "validation" if exc.status_code == 422 else "substrate"
        return _error_response(
            status_code=exc.status_code,
            category=category,
            message=str(exc.detail),
            request_id=req.request_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("inference failed")
        return _error_response(
            status_code=500,
            category="internal",
            message=f"inference failed: {exc}",
            request_id=req.request_id,
        )

    wav = _float32_to_wav_bytes(audio, sample_rate)
    duration_ms = int(1000.0 * len(audio) / sample_rate)
    return Response(
        content=wav,
        media_type="audio/wav",
        headers={
            "X-Peakvox-Request-Id": req.request_id,
            "X-Peakvox-Duration-Ms": str(duration_ms),
        },
    )


@app.post("/v1/variants/build")
def build_variant(req: BuildVariantRequest) -> JSONResponse:
    """Variant build endpoint (ADR-0017 §6.4).

    Returns 501 — variant build is delegated to the in-process XTTS adapter
    (same posture as the F5-TTS runtime). A future phase may move speaker-latent
    precomputation into the runtime container.
    """
    return _error_response(
        status_code=501,
        category="not_implemented",
        message=(
            "variant build is not implemented in this runtime; the in-process "
            "XTTS adapter handles build_variant requests"
        ),
        request_id=req.request_id,
    )
