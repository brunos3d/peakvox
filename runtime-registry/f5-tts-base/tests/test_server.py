"""Contract + regression tests for the peakvox/f5-tts-runtime server.

The F5-TTS model is mocked; the tests exercise the HTTP shape, the
readiness state machine, and — critically — the T24 regressions:

  1. ref_text is NEVER empty when a reference clip is supplied.
     f5-tts 1.0.3 reacts to ref_text="" by auto-transcribing the
     clip with Whisper ASR, which crashes on torch 2.12 with
     "Cannot copy out of meta tensor; no data!". The server must
     fall back to the stored transcript, then to a neutral
     placeholder — never to "".
  2. Voice-optional mode: when no ref_audio_path is supplied, the
     bundled default reference clip + its known transcript are used
     (supports_voice_optional capability).
  3. f5-tts 1.0.3 API: ``pipeline.infer(gen_text=..., ref_file=...,
     ref_text=...)`` — the kwarg is ``ref_file``, not ``ref_audio``.

torch is stubbed in ``sys.modules`` before the server module loads
(server.py imports torch at module level for the CUDA load path,
which these tests never exercise).
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient


_SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"

_BUNDLED_REF = (
    "/opt/conda/lib/python3.11/site-packages/f5_tts/infer/examples/basic/basic_ref_en.wav"
)
_BUNDLED_REF_TEXT = "Some call me nature, others call me mother nature."
_CLONING_PLACEHOLDER = "Voice cloning reference audio sample."


def _ensure_fake_torch() -> None:
    """server.py does ``import torch`` at module level. Provide a stub
    exposing the names the module touches outside the load path."""
    if "torch" in sys.modules:
        return
    fake = types.ModuleType("torch")
    fake.cuda = types.SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]
    fake.device = lambda *a, **k: a  # type: ignore[attr-defined]
    sys.modules["torch"] = fake


def _load_server_module():
    """Load server.py under a unique module name (no bare ``import server``,
    which would collide with the other runtimes' server modules when several
    runtime test suites run in one pytest session)."""
    _ensure_fake_torch()
    spec = importlib.util.spec_from_file_location("f5_tts_base_server", _SERVER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["f5_tts_base_server"] = mod
    spec.loader.exec_module(mod)
    return mod


srv = _load_server_module()


# ---------------------------------------------------------------------------
# Fake F5-TTS pipeline
# ---------------------------------------------------------------------------


class _MockF5Pipeline:
    """Stand-in for ``f5_tts.api.F5TTS``.

    ``infer(**kwargs)`` records its kwargs and returns the 1.0.3 triple
    (wav, sample_rate, spec): a 1-second 24 kHz float32 waveform.
    """

    SAMPLE_RATE = 24000

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def infer(self, **kwargs: Any):
        self.calls.append(kwargs)
        wav = np.zeros(self.SAMPLE_RATE, dtype=np.float32)
        wav[: self.SAMPLE_RATE // 2] = 0.1
        return wav, self.SAMPLE_RATE, None


@pytest.fixture
def pipeline() -> _MockF5Pipeline:
    return _MockF5Pipeline()


@pytest.fixture
def client(pipeline):
    srv._pipeline = pipeline
    srv._sample_rate = _MockF5Pipeline.SAMPLE_RATE
    srv._load_state = "ready"
    with TestClient(srv.app) as c:
        yield c
    srv._pipeline = None
    srv._sample_rate = None
    srv._load_state = "unloaded"
    srv._load_error = None


def _payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "voice_id": "voice_test",
        "text": "Hello, world.",
        "language": "en",
        "params": {},
        "request_id": "req_t24_f5_001",
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Contract surface
# ---------------------------------------------------------------------------


def test_health_returns_200(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_ready_returns_200_when_loaded(client) -> None:
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_ready_returns_503_with_cuda_reason_when_load_failed() -> None:
    srv._pipeline = None
    srv._load_state = "failed"
    srv._load_error = "cuda_unavailable: F5-TTS requires a CUDA device"
    with TestClient(srv.app) as c:
        r = c.get("/ready")
        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "not_ready"
        assert "cuda_unavailable" in body["reason"]
    srv._load_state = "unloaded"
    srv._load_error = None


def test_metadata_returns_canonical_body(client) -> None:
    r = client.get("/v1/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["runtime_id"] == "f5-tts-base"
    assert body["model_id"] == "f5-tts-base"
    assert "voice_cloning" in body["capabilities"]
    assert body["substrate"] == "gpu"


def test_build_variant_returns_501(client) -> None:
    r = client.post("/v1/variants/build", json={
        "voice_id": "voice_test",
        "reference_audio_storage_key": "voices/x/ref.wav",
        "request_id": "req_t24_f5_b01",
    })
    assert r.status_code == 501


def test_generate_returns_nonempty_wav(client) -> None:
    r = client.post("/v1/generate", json=_payload())
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.headers["X-Peakvox-Request-Id"] == "req_t24_f5_001"
    assert int(r.headers["X-Peakvox-Duration-Ms"]) == 1000
    assert r.content[:4] == b"RIFF"
    assert len(r.content) > 44


# ---------------------------------------------------------------------------
# T24 regression 1: ref_text must never reach the model empty
# ---------------------------------------------------------------------------


def test_cloning_with_no_transcript_gets_placeholder_not_empty(client, pipeline) -> None:
    """THE meta-tensor regression: ref audio + no transcript anywhere.

    ref_text="" triggers Whisper ASR auto-transcription inside f5-tts,
    which crashes on torch 2.12. The server must substitute the neutral
    placeholder instead."""
    r = client.post("/v1/generate", json=_payload(
        params={"ref_audio_path": "/data/tmp/fireship.wav"},
    ))
    assert r.status_code == 200
    call = pipeline.calls[0]
    assert call["ref_file"] == "/data/tmp/fireship.wav"
    assert call["ref_text"] == _CLONING_PLACEHOLDER
    assert call["ref_text"] != ""


def test_cloning_with_null_transcript_gets_placeholder(client, pipeline) -> None:
    """variant_params_extra serializes {"transcript": None} — the JSON null
    must be treated as missing, not stringified or forwarded."""
    r = client.post("/v1/generate", json=_payload(
        params={"ref_audio_path": "/data/tmp/fireship.wav", "transcript": None},
    ))
    assert r.status_code == 200
    assert pipeline.calls[0]["ref_text"] == _CLONING_PLACEHOLDER


def test_cloning_with_stored_transcript_uses_it(client, pipeline) -> None:
    r = client.post("/v1/generate", json=_payload(
        params={"ref_audio_path": "/data/tmp/bruno.wav", "transcript": "olá, tudo bem?"},
    ))
    assert r.status_code == 200
    assert pipeline.calls[0]["ref_text"] == "olá, tudo bem?"


def test_cloning_with_explicit_ref_text_wins_over_transcript(client, pipeline) -> None:
    r = client.post("/v1/generate", json=_payload(
        params={
            "ref_audio_path": "/data/tmp/bruno.wav",
            "ref_text": "explicit",
            "transcript": "stored",
        },
    ))
    assert r.status_code == 200
    assert pipeline.calls[0]["ref_text"] == "explicit"


def test_no_call_ever_sends_empty_ref_text(client, pipeline) -> None:
    """Sweep the param combinations that historically produced ref_text=""."""
    cases = [
        {},
        {"ref_audio_path": "/data/tmp/a.wav"},
        {"ref_audio_path": "/data/tmp/a.wav", "transcript": None},
        {"ref_audio_path": "/data/tmp/a.wav", "transcript": ""},
        {"ref_audio_path": "/data/tmp/a.wav", "ref_text": ""},
    ]
    for params in cases:
        r = client.post("/v1/generate", json=_payload(params=params))
        assert r.status_code == 200
    assert all(c["ref_text"] for c in pipeline.calls), (
        f"empty ref_text leaked to the model: {pipeline.calls}"
    )


# ---------------------------------------------------------------------------
# T24 regression 2: voice-optional mode
# ---------------------------------------------------------------------------


def test_voice_optional_uses_bundled_default_reference(client, pipeline) -> None:
    """No ref_audio_path → bundled clip + its known transcript (no ASR)."""
    r = client.post("/v1/generate", json=_payload(params={}))
    assert r.status_code == 200
    call = pipeline.calls[0]
    assert call["ref_file"] == _BUNDLED_REF
    assert call["ref_text"] == _BUNDLED_REF_TEXT


# ---------------------------------------------------------------------------
# T24 regression 3: f5-tts 1.0.3 kwarg names
# ---------------------------------------------------------------------------


def test_infer_uses_ref_file_kwarg_not_ref_audio(client, pipeline) -> None:
    """f5-tts 1.0.3 renamed ref_audio → ref_file; the old name raises
    TypeError at inference time."""
    r = client.post("/v1/generate", json=_payload(
        params={"ref_audio_path": "/data/tmp/a.wav", "transcript": "hi"},
    ))
    assert r.status_code == 200
    call = pipeline.calls[0]
    assert "ref_file" in call
    assert "ref_audio" not in call
    assert call["gen_text"] == "Hello, world."


def test_tunable_params_forwarded_when_present(client, pipeline) -> None:
    r = client.post("/v1/generate", json=_payload(
        params={"speed": 1.2, "nfe_step": 16, "cfg_strength": 2.5},
    ))
    assert r.status_code == 200
    call = pipeline.calls[0]
    assert call["speed"] == 1.2
    assert call["nfe_step"] == 16
    assert call["cfg_strength"] == 2.5


def test_null_tunable_params_are_omitted(client, pipeline) -> None:
    """Frontends send explicit nulls; float(None) would raise TypeError."""
    r = client.post("/v1/generate", json=_payload(
        params={"speed": None, "nfe_step": None, "cfg_strength": None},
    ))
    assert r.status_code == 200
    call = pipeline.calls[0]
    assert "speed" not in call
    assert "nfe_step" not in call
    assert "cfg_strength" not in call
