"""peakvox/f5-tts-runtime — FastAPI server.

The third Runtime Service PeakVox ships. This server implements
the 5-endpoint Runtime Service Contract (ADR-0017 §6) over
HTTP/JSON. The F5-TTS flow-matching model is loaded lazily on
the first inference request; until then, the server reports
not-ready (503 on /ready) but stays alive (200 on /health).

This file is the canonical copy-from-Kokoro template: every
contract-level surface (/health, /ready, /v1/metadata,
/v1/generate, /v1/variants/build, error envelope, response
headers) is identical to the Kokoro runtime. Only the
inference backend changes (F5-TTS's flow-matching pipeline
vs. Kokoro's KPipeline).

F5-TTS is GPU-only (CUDA required for inference). CPU
inference is unsupported upstream; the runtime reports
"load_failed: cuda_unavailable" on /ready when no GPU is
present, and the manager reaps the container on
idle_timeout.

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
from typing import Any, Iterator, Literal, Optional

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


logger = logging.getLogger("peakvox.f5_tts_runtime")


# ---------------------------------------------------------------------------
# Module-level state (the "model is loaded" singleton)
# ---------------------------------------------------------------------------
#
# The F5-TTS model is heavy. We load it once on the first
# /v1/generate call (lazy), guarded by a lock so that
# concurrent first requests share the same load. After load,
# the pipeline is reused for every subsequent request.
#
# _load_state transitions:
#   "unloaded"  → "loading"  → "ready"     (success)
#                              → "failed"   (load error; error message in _load_error)


_pipeline: Any = None
_sample_rate: Optional[int] = None
_device: Optional[torch.device] = None
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
# F5-TTS integration (lazy + injectable for tests)
# ---------------------------------------------------------------------------


def _load_f5_tts_pipeline() -> Any:
    """Load the F5-TTS pipeline.

    The first call imports ``f5_tts`` and constructs the
    flow-matching model + vocoder. Subsequent calls return
    the cached pipeline. The function is the single load
    point; tests patch ``_pipeline`` and ``_load_state`` to
    inject a mock without exercising this code path.
    """
    global _pipeline, _sample_rate, _device

    if not torch.cuda.is_available():
        raise RuntimeError("cuda_unavailable: F5-TTS requires a CUDA device")

    _device = torch.device("cuda:0")
    from f5_tts.api import F5TTS  # type: ignore

    _pipeline = F5TTS(
        model="F5TTS_v1_Base",
        vocoder="vocos",
        device=_device,
    )
    # F5-TTS outputs at 24kHz by default.
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
            _load_f5_tts_pipeline()
            _load_state = "ready"
            return True
        except Exception as exc:  # noqa: BLE001
            _load_state = "failed"
            _load_error = str(exc)
            logger.exception("f5-tts pipeline load failed")
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
    """Run F5-TTS inference. Returns (audio, sample_rate).

    When ref_audio_path is absent or None, the model generates with its own
    internal default voice (supports_voice_optional=True capability). This
    allows F5-TTS to be used without a selected voice in the UI.
    """
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="pipeline not loaded")

    ref_audio = req.params.get("ref_audio_path") or None
    ref_text = req.params.get("ref_text") or ""

    infer_kwargs: dict = {
        "gen_text": req.text,
        "ref_audio": ref_audio,
        "ref_text": ref_text,
    }

    # Expose user-tunable generation parameters.
    params = req.params or {}
    if "speed" in params:
        infer_kwargs["speed"] = float(params["speed"])
    if "nfe_step" in params:
        infer_kwargs["nfe_step"] = int(params["nfe_step"])
    if "cfg_strength" in params:
        infer_kwargs["cfg_strength"] = float(params["cfg_strength"])
    if "cross_fade_duration" in params:
        infer_kwargs["cross_fade_duration"] = float(params["cross_fade_duration"])

    wav, sample_rate, _spec = _pipeline.infer(**infer_kwargs)
    if wav is None or len(wav) == 0:
        raise HTTPException(status_code=500, detail="inference produced no audio")
    return wav, int(sample_rate)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="peakvox/f5-tts-runtime",
    version="0.1.0",
    description=(
        "Runtime service for the F5-TTS flow-matching TTS model. "
        "Implements the 5-endpoint Runtime Service Contract "
        "(ADR-0017 §6). Mirrors the Kokoro reference shape (R8). "
        "GPU-only (CUDA required)."
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
        "runtime_id": "f5-tts-base",
        "model_id": "f5-tts-base",
        "capabilities": [
            "tts",
            "voice_cloning",
            "multilingual",
            "reference_audio",
        ],
        "supported_languages": [
            "en", "zh", "ja", "fr", "de", "es", "ko", "ru",
        ],
        "supported_tags": [],
        "supported_voice_design": [],
        "realization_types": ["source_asset"],
        "build_strategies": [
            {
                "creation_source": "SOURCE_ASSET",
                "can_build": True,
                "requires": ["reference_audio_storage_key", "ref_text"],
            },
        ],
        "max_concurrent_requests": 1,
        "max_text_length": 5000,
        "substrate": "gpu",
        "min_vram_gb": 12,
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
    F5-TTS adapter. A future phase may move the build pipeline
    into the runtime container.
    """
    return _error_response(
        status_code=501,
        category="not_implemented",
        message=(
            "variant build is not implemented in this runtime "
            "in Phase 3; the in-process F5-TTS adapter handles "
            "build_variant requests"
        ),
        request_id=req.request_id,
    )
