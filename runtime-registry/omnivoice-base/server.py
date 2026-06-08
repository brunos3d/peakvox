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
from typing import Annotated, Any, Iterator, Literal, Optional

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

    The first call imports ``omnivoice`` and constructs a
    pipeline. Subsequent calls return the cached pipeline.
    The function is the single load point; tests patch
    ``_pipeline`` and ``_load_state`` to inject a mock without
    exercising this code path.
    """
    global _pipeline, _sample_rate
    from omnivoice import OmniVoicePipeline  # type: ignore

    _pipeline = OmniVoicePipeline.from_pretrained("k2-fsa/OmniVoice")
    # OmniVoice outputs at 24kHz by default; the actual sample
    # rate is exposed via the pipeline. The PeakVox runtime
    # contract returns audio/wav with the pipeline's native rate.
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
    """Run OmniVoice inference. Returns (audio, sample_rate)."""
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="pipeline not loaded")
    # OmniVoice's pipeline takes (text, voice_id, ref_audio, params).
    # The adapter is responsible for translating PeakVox voice_id
    # and the optional variant/artifact into OmniVoice's expected
    # inputs; for Phase 3 the voice_id is the catalog voice id
    # and ref_audio is read from the variant artifact.
    generator: Iterator[tuple[str, np.ndarray]] = _pipeline.synthesize(
        text=req.text,
        voice_id=req.voice_id,
        params=req.params,
    )
    chunks = [audio for _, audio in generator]
    if not chunks:
        raise HTTPException(status_code=500, detail="inference produced no audio")
    audio = np.concatenate(chunks)
    sample_rate = _sample_rate or 24000
    return audio, sample_rate


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="peakvox/omnivoice-runtime",
    version="0.1.0",
    description=(
        "Runtime service for the OmniVoice 0.6B TTS model. "
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
