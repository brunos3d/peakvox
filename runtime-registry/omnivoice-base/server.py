"""peakvox/omnivoice-runtime — FastAPI server.

The second Runtime Service PeakVox ships. This server implements
the 5-endpoint Runtime Service Contract (ADR-0017 §6) over
HTTP/JSON. The OmniVoice model is loaded lazily on the first
inference request; until then, the server reports not-ready
(503 on /ready) but stays alive (200 on /health).

This file is the canonical copy-from-Kokoro template: every
contract-level surface (/health, /ready, /v1/metadata,
/v1/generate, /v1/variants/build, error envelope, response
headers) is identical to the Kokoro runtime. Only the
inference backend changes (OmniVoice's diffusion pipeline
vs. Kokoro's KPipeline).

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
import threading
import time
import wave
from datetime import datetime, timezone
from typing import Annotated, Any, Literal, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


logger = logging.getLogger("peakvox.omnivoice_runtime")


# ---------------------------------------------------------------------------
# Module-level state (the "model is loaded" singleton)
# ---------------------------------------------------------------------------
#
# The OmniVoice model is heavy. We load it once on the first
# /v1/generate call (lazy), guarded by a lock so that
# concurrent first requests share the same load. After load,
# the pipeline is reused for every subsequent request.
#
# _load_state transitions:
#   "unloaded"  → "loading"  → "ready"     (success)
#                              → "failed"   (load error; error message in _load_error)


_pipeline: Any = None
_sample_rate: Optional[int] = None
_load_state: Literal["unloaded", "loading", "ready", "failed"] = "unloaded"
_load_error: Optional[str] = None
_load_lock = threading.Lock()


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
    language: str = "auto"
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
# OmniVoice integration (lazy + injectable for tests)
# ---------------------------------------------------------------------------


def _load_omnivoice_pipeline() -> Any:
    """Load the OmniVoice pipeline.

    The first call imports ``omnivoice`` and constructs the model.
    Subsequent calls return the cached pipeline. The function is
    the single load point; tests patch ``_pipeline`` and
    ``_load_state`` to inject a mock without exercising this code.
    """
    global _pipeline, _sample_rate
    import torch
    from omnivoice import OmniVoice  # type: ignore  # correct class (not OmniVoicePipeline)

    # Use the documentation-recommended loading pattern for optimal GPU usage.
    # device_map="cuda:0" handles the placement, and float16 reduces VRAM usage.
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    _pipeline = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map=device,
        dtype=dtype
    )
    
    logger.info(f"OmniVoice model loaded on {device} with dtype={dtype}")

    # Prefer the model's declared sampling rate; fall back to 24kHz.
    try:
        _sample_rate = _pipeline.config.sampling_rate
    except AttributeError:
        _sample_rate = 24000
    return _pipeline


def _ensure_pipeline_loaded() -> bool:
    """Make sure the pipeline is loaded; trigger lazy load if not.

    Returns True if the pipeline is ready; False if the load
    failed (caller should return 503). Idempotent; thread-safe.
    """
    global _load_state, _load_error
    if _load_state == "ready":
        return True
    if _load_state == "loading":
        # Another thread is loading; wait for it.
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
            _load_omnivoice_pipeline()
            _load_state = "ready"
            return True
        except Exception as exc:  # noqa: BLE001
            _load_state = "failed"
            _load_error = str(exc)
            logger.exception("omnivoice pipeline load failed")
            return False


# ---------------------------------------------------------------------------
# Audio encoding
# ---------------------------------------------------------------------------


def _float32_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Encode a float32 mono waveform as 16-bit PCM WAV bytes."""
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


def _run_inference(req: GenerateRequest) -> tuple[np.ndarray, int]:
    """Run OmniVoice inference. Returns (audio, sample_rate).

    OmniVoice.generate() supports three modes:
      1. Voice clone — ref_audio + ref_text (optional) clone the style.
      2. Voice design — instruct string/list describes the desired voice.
      3. Auto — model picks a voice itself (no ref_audio, no instruct).
    """
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="pipeline not loaded")

    import torch

    params = req.params or {}

    # Extract voice inputs from request params
    ref_audio: Optional[str] = params.get("ref_audio_path") or None
    ref_text: Optional[str] = params.get("ref_text") or params.get("transcript") or None
    # instruct covers explicit user instructions; voice_design tags fall back.
    # OmniVoice.generate() accepts instruct as str or list[str], but the list length
    # must equal the number of texts (1 here). Join a tag list into a single string.
    instruct = params.get("instruct") or None
    if instruct is None:
        voice_design = params.get("voice_design") or (params.get("generation_defaults") or {}).get("voice_design")
        if voice_design:
            instruct = ", ".join(str(v) for v in voice_design) if isinstance(voice_design, list) else str(voice_design)

    gen_kwargs: dict[str, Any] = {"text": req.text}
    if req.language and req.language != "auto":
        gen_kwargs["language"] = req.language
    if ref_audio is not None:
        gen_kwargs["ref_audio"] = ref_audio
    if ref_text is not None:
        gen_kwargs["ref_text"] = ref_text
    if instruct is not None:
        gen_kwargs["instruct"] = instruct
    if params.get("speed") is not None:
        gen_kwargs["speed"] = float(params["speed"])
    if params.get("duration") is not None:
        gen_kwargs["duration"] = float(params["duration"])

    audio_tensors: list = _pipeline.generate(**gen_kwargs)
    if not audio_tensors:
        raise HTTPException(status_code=500, detail="inference produced no audio")

    # Squeeze batch dimension: OmniVoice returns a list of np.ndarrays (v0.1.5);
    # concatenate them and ensure float32 format for the WAV converter.
    import numpy as np
    audio = np.concatenate(audio_tensors).astype(np.float32).squeeze()
    sample_rate = _sample_rate or 24000
    return audio, sample_rate


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="peakvox/omnivoice-runtime",
    version="0.1.5",
    description=(
        "Runtime service for the OmniVoice 0.6B TTS model (v0.1.5). "
        "Implements the 5-endpoint Runtime Service Contract "
        "(ADR-0017 §6). Mirrors the Kokoro reference shape (R8)."
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
    """Runtime metadata (ADR-0017 §6.5)."""
    return {
        "runtime_id": "omnivoice-base",
        "model_id": "omnivoice-base",
        "capabilities": [
            "tts",
            "voice_cloning",
            "multilingual",
            "emotion_tags",
            "voice_design",
            "reference_audio",
        ],
        "supported_languages": [
            # 646 languages per upstream card; a representative subset
            # is listed here for the metadata surface. The runtime
            # auto-detects the language from text when language="auto".
            "en", "zh", "ja", "ko", "es", "fr", "de", "it", "pt",
            "ru", "ar", "hi", "id", "vi", "th", "tr", "pl", "nl",
        ],
        "supported_tags": [
            "laughter", "sigh",
            "confirmation-en", "question-en",
            "question-ah", "question-oh", "question-ei", "question-yi",
            "surprise-ah", "surprise-oh", "surprise-wa", "surprise-yo",
            "dissatisfaction-hnn",
        ],
        "supported_voice_design": [
            "male", "female", "child", "teenager",
            "young adult", "middle-aged", "elderly",
            "very low pitch", "low pitch", "moderate pitch",
            "high pitch", "very high pitch", "whisper",
            "american accent", "british accent", "australian accent",
            "canadian accent", "indian accent",
        ],
        "realization_types": ["source_asset"],
        "build_strategies": [
            {
                "creation_source": "SOURCE_ASSET",
                "can_build": True,
                "requires": ["reference_audio_storage_key"],
            },
        ],
        "max_concurrent_requests": 2,
        "max_text_length": 10000,
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
    if not _ensure_pipeline_loaded():
        return _error_response(
            status_code=503,
            category="not_ready",
            message=f"runtime is not ready: {_load_error or 'model not loaded'}",
            request_id=req.request_id,
        )
    try:
        audio, sample_rate = _run_inference(req)
    except HTTPException as exc:
        return _error_response(
            status_code=exc.status_code,
            category="substrate",
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

    Returns 501 — variant build is delegated to the in-process
    OmniVoice adapter. A future phase may move the build pipeline
    into the runtime container.
    """
    return _error_response(
        status_code=501,
        category="not_implemented",
        message=(
            "variant build is not implemented in this runtime "
            "in Phase 3; the in-process OmniVoice adapter handles "
            "build_variant requests"
        ),
        request_id=req.request_id,
    )
