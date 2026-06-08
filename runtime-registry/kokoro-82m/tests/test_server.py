"""Contract tests for the peakvox/kokoro-runtime server.

These tests verify that the FastAPI server implements the
5-endpoint Runtime Service Contract (ADR-0017 §6). The Kokoro
model is mocked; the tests exercise the HTTP shape, the
readiness state machine, the request/response bodies, and
the error envelope.

Test surface
------------

  /health                  — liveness; always 200
  /ready                   — readiness; 200 when model loaded, 503 otherwise
  /v1/metadata             — capabilities, languages, tags; canonical body
  /v1/generate             — audio/wav bytes; X-Peakvox-* headers
  /v1/variants/build       — 501 in Phase 3 (deferred to in-process adapter)
"""

from __future__ import annotations

from typing import Iterator, Tuple

import numpy as np
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _MockKokoroPipeline:
    """A simple stand-in for ``kokoro.KPipeline``.

    Mimics the call interface: ``pipeline(text, voice=...)`` returns
    a generator of (graphemes, phonemes, audio) tuples. Audio is a
    1-second 24kHz mono float32 waveform (a 440Hz sine).
    """

    SAMPLE_RATE = 24000

    def __call__(self, text: str, voice: str = "af_bella") -> Iterator[Tuple[str, str, np.ndarray]]:
        duration_seconds = 1
        t = np.linspace(0, duration_seconds, self.SAMPLE_RATE, endpoint=False)
        audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        yield (text, text, audio)


@pytest.fixture
def mock_kokoro_pipeline() -> Tuple[_MockKokoroPipeline, int]:
    """The mock pipeline and its sample rate."""
    return _MockKokoroPipeline(), _MockKokoroPipeline.SAMPLE_RATE


@pytest.fixture
def client(mock_kokoro_pipeline):
    """A TestClient with the model loader patched to return the mock."""
    pipeline, sample_rate = mock_kokoro_pipeline
    import server as srv
    srv._pipeline = pipeline
    srv._sample_rate = sample_rate
    srv._load_state = "ready"
    with TestClient(srv.app) as c:
        yield c
    # Reset module state.
    srv._pipeline = None
    srv._sample_rate = None
    srv._load_state = "unloaded"


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_returns_200(client) -> None:
    """GET /health returns 200 with {"status": "alive"}."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_health_does_not_require_model_loaded() -> None:
    """GET /health returns 200 even when the model is not yet loaded."""
    import server as srv
    srv._pipeline = None
    srv._load_state = "unloaded"
    with TestClient(srv.app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "alive"}


# ---------------------------------------------------------------------------
# /ready
# ---------------------------------------------------------------------------


def test_ready_returns_200_when_model_loaded(client) -> None:
    """GET /ready returns 200 with {"status": "ready"} when model is loaded."""
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_ready_returns_503_when_model_unloaded() -> None:
    """GET /ready returns 503 with reason when model is still loading."""
    import server as srv
    srv._pipeline = None
    srv._load_state = "loading"
    with TestClient(srv.app) as c:
        r = c.get("/ready")
        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "not_ready"
        assert "reason" in body
    # Reset for subsequent tests.
    srv._load_state = "unloaded"


# ---------------------------------------------------------------------------
# /v1/metadata
# ---------------------------------------------------------------------------


def test_metadata_returns_canonical_body(client) -> None:
    """GET /v1/metadata returns the canonical body (ADR-0017 §6.5)."""
    r = client.get("/v1/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["runtime_id"] == "kokoro-82m"
    assert body["model_id"] == "kokoro-base"
    assert "tts" in body["capabilities"]
    assert isinstance(body["supported_languages"], list)
    assert isinstance(body["supported_tags"], list)
    assert "max_concurrent_requests" in body
    assert "max_text_length" in body


# ---------------------------------------------------------------------------
# /v1/generate
# ---------------------------------------------------------------------------


def test_generate_returns_audio_wav_bytes(client) -> None:
    """POST /v1/generate returns 200 with audio/wav body."""
    payload = {
        "voice_id": "af_bella",
        "variant_id": "variant_xyz",
        "artifact_id": "artifact_abc",
        "artifact_version": 1,
        "text": "Hello, world.",
        "language": "en",
        "params": {"speed": 1.0},
        "request_id": "req_test_001",
    }
    r = client.post("/v1/generate", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert "X-Peakvox-Request-Id" in r.headers
    assert r.headers["X-Peakvox-Request-Id"] == "req_test_001"
    assert "X-Peakvox-Duration-Ms" in r.headers
    # The body must be a non-empty WAV (RIFF header + non-zero data).
    assert r.content[:4] == b"RIFF"
    assert len(r.content) > 44  # WAV header is 44 bytes


def test_generate_returns_503_when_model_unloaded() -> None:
    """POST /v1/generate returns 503 with the canonical error body
    when the model is not yet loaded."""
    import server as srv
    srv._pipeline = None
    srv._load_state = "failed"
    srv._load_error = "test: simulating load failure"
    with TestClient(srv.app) as c:
        r = c.post("/v1/generate", json={
            "voice_id": "af_bella",
            "text": "Hello.",
            "request_id": "req_test_002",
        })
        assert r.status_code == 503
        body = r.json()
        assert "error" in body
        assert body["error"]["category"] in {"not_ready", "substrate"}


def test_generate_returns_422_on_missing_text(client) -> None:
    """POST /v1/generate with missing 'text' returns 422 (FastAPI's
    standard validation error). The body is FastAPI's default
    validation envelope; a future revision may wrap it in the
    canonical error envelope (§6.6)."""
    r = client.post("/v1/generate", json={
        "voice_id": "af_bella",
        "request_id": "req_test_003",
    })
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /v1/variants/build
# ---------------------------------------------------------------------------


def test_variants_build_returns_501_in_phase3(client) -> None:
    """POST /v1/variants/build returns 501 in Phase 3 (deferred)."""
    r = client.post("/v1/variants/build", json={
        "voice_id": "voice_abc",
        "reference_audio_storage_key": "voice_assets/voice_abc/source.wav",
        "request_id": "req_build_001",
    })
    assert r.status_code == 501
    body = r.json()
    assert "error" in body
    assert body["error"]["category"] in {"not_implemented", "substrate"}


# ---------------------------------------------------------------------------
# Error envelope
# ---------------------------------------------------------------------------


def test_error_envelope_shape() -> None:
    """All non-validation 4xx/5xx errors use the canonical error envelope
    (ADR-0017 §6.6). The 422 validation path uses FastAPI's default
    envelope; the 503 not-ready path uses the canonical envelope."""
    import server as srv
    srv._pipeline = None
    srv._load_state = "failed"
    srv._load_error = "test: simulating load failure"
    with TestClient(srv.app) as c:
        r = c.post("/v1/generate", json={
            "voice_id": "af_bella",
            "text": "Hello.",
            "request_id": "req_envelope_test",
        })
        assert r.status_code == 503
        body = r.json()
        assert "error" in body
        assert "category" in body["error"]
        assert "message" in body["error"]
        assert body["error"]["request_id"] == "req_envelope_test"
        assert "timestamp" in body["error"]
