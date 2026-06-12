"""Contract + behavior tests for the peakvox/xtts-runtime server.

The Coqui TTS engine is mocked; the tests exercise the HTTP shape, the readiness
state machine, and the XTTS-specific behaviors:

  1. CPU fallback (the divergence from F5-TTS): a missing GPU is NOT a failure.
     _select_device returns "cpu" and the server loads/serves normally.
  2. Voice cloning: params.ref_audio_path is forwarded as speaker_wav.
  3. Voice-optional: with no ref_audio_path a built-in studio speaker is used.
  4. Unsupported language → 422 (clear validation error, not an engine crash).
  5. Inference is serialized (max_concurrent_requests: 1) — the XTTS GPT backbone
     is not concurrency-safe.

torch is stubbed in sys.modules before the server module loads (server.py
imports torch at module level for the device-selection path).
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

# Toggled by tests to simulate GPU present/absent for _select_device.
_CUDA_AVAILABLE = {"value": False}


def _ensure_fake_torch() -> None:
    """server.py does ``import torch`` at module level. Provide a stub exposing
    the names the module touches (torch.cuda.is_available)."""
    if "torch" in sys.modules and getattr(sys.modules["torch"], "_peakvox_fake", False):
        return
    fake = types.ModuleType("torch")
    fake._peakvox_fake = True  # type: ignore[attr-defined]
    fake.cuda = types.SimpleNamespace(  # type: ignore[attr-defined]
        is_available=lambda: _CUDA_AVAILABLE["value"]
    )
    sys.modules["torch"] = fake


def _load_server_module():
    """Load server.py under a unique module name (no bare ``import server``,
    which would collide with the other runtimes' server modules when several
    runtime test suites run in one pytest session)."""
    _ensure_fake_torch()
    spec = importlib.util.spec_from_file_location("xtts_v2_server", _SERVER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["xtts_v2_server"] = mod
    spec.loader.exec_module(mod)
    return mod


srv = _load_server_module()


# ---------------------------------------------------------------------------
# Fake Coqui TTS engine
# ---------------------------------------------------------------------------


class _MockTTS:
    """Stand-in for ``TTS.api.TTS``.

    ``tts(**kwargs)`` records its kwargs and returns a 1-second 24 kHz float32
    waveform (as a Python list, matching the real engine which returns a list).
    """

    SAMPLE_RATE = 24000

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.speakers = ["Claribel Dervla", "Daisy Studious"]
        self._active = False
        self.overlap_detected = False
        self.device: str | None = None

    def to(self, device: str) -> "_MockTTS":
        self.device = device
        return self

    def tts(self, **kwargs: Any):
        if self._active:
            self.overlap_detected = True
        self._active = True
        try:
            import time as _time

            _time.sleep(0.05)
            self.calls.append(kwargs)
            wav = np.zeros(self.SAMPLE_RATE, dtype=np.float32)
            wav[: self.SAMPLE_RATE // 2] = 0.1
            return wav.tolist()
        finally:
            self._active = False


@pytest.fixture
def engine() -> _MockTTS:
    return _MockTTS()


@pytest.fixture
def client(engine):
    srv._tts = engine
    srv._device = "cpu"
    srv._load_state = "ready"
    with TestClient(srv.app) as c:
        yield c
    srv._tts = None
    srv._device = "cpu"
    srv._load_state = "unloaded"
    srv._load_error = None


def _payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "voice_id": "voice_test",
        "text": "Hello, world.",
        "language": "en",
        "params": {},
        "request_id": "req_xtts_001",
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


def test_ready_returns_503_when_load_failed() -> None:
    srv._tts = None
    srv._load_state = "failed"
    srv._load_error = "boom"
    with TestClient(srv.app) as c:
        r = c.get("/ready")
        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "not_ready"
        assert "boom" in body["reason"]
    srv._load_state = "unloaded"
    srv._load_error = None


def test_metadata_returns_canonical_body(client) -> None:
    r = client.get("/v1/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["runtime_id"] == "xtts-v2"
    assert body["model_id"] == "xtts-v2"
    assert "voice_cloning" in body["capabilities"]
    assert "multilingual" in body["capabilities"]
    assert "en" in body["supported_languages"]
    assert len(body["supported_languages"]) == 17


def test_metadata_substrate_reflects_live_device(client) -> None:
    """substrate must report the live device so the platform shows the real
    execution mode (honoring Use GPU). Loaded on cpu -> 'cpu'."""
    srv._device = "cpu"
    assert client.get("/v1/metadata").json()["substrate"] == "cpu"
    srv._device = "cuda"
    assert client.get("/v1/metadata").json()["substrate"] == "gpu"
    srv._device = "cpu"


def test_build_variant_returns_501(client) -> None:
    r = client.post("/v1/variants/build", json={
        "voice_id": "voice_test",
        "reference_audio_storage_key": "voices/x/ref.wav",
        "request_id": "req_xtts_b01",
    })
    assert r.status_code == 501


def test_generate_returns_nonempty_wav(client) -> None:
    r = client.post("/v1/generate", json=_payload())
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.headers["X-Peakvox-Request-Id"] == "req_xtts_001"
    assert int(r.headers["X-Peakvox-Duration-Ms"]) == 1000
    assert r.content[:4] == b"RIFF"
    assert len(r.content) > 44


# ---------------------------------------------------------------------------
# Voice cloning vs. voice-optional
# ---------------------------------------------------------------------------


def test_cloning_forwards_ref_audio_as_speaker_wav(client, engine) -> None:
    r = client.post("/v1/generate", json=_payload(
        params={"ref_audio_path": "/data/tmp/bruno.wav"},
    ))
    assert r.status_code == 200
    call = engine.calls[0]
    assert call["speaker_wav"] == "/data/tmp/bruno.wav"
    assert "speaker" not in call  # cloning, not built-in
    assert call["language"] == "en"
    assert call["text"] == "Hello, world."


def test_voice_optional_uses_builtin_speaker(client, engine) -> None:
    """No ref_audio_path → first built-in studio speaker (no crash, no ref)."""
    r = client.post("/v1/generate", json=_payload(params={}))
    assert r.status_code == 200
    call = engine.calls[0]
    assert call["speaker"] == "Claribel Dervla"
    assert "speaker_wav" not in call


def test_voice_optional_errors_clearly_when_no_builtin_speaker(client, engine) -> None:
    engine.speakers = []
    r = client.post("/v1/generate", json=_payload(params={}))
    assert r.status_code == 422
    assert "no reference audio" in r.json()["error"]["message"]


# ---------------------------------------------------------------------------
# Language validation
# ---------------------------------------------------------------------------


def test_unsupported_language_returns_422(client) -> None:
    r = client.post("/v1/generate", json=_payload(language="xx"))
    assert r.status_code == 422
    assert "unsupported language" in r.json()["error"]["message"]


def test_supported_language_passes_through(client, engine) -> None:
    r = client.post("/v1/generate", json=_payload(language="pt", params={
        "ref_audio_path": "/data/tmp/a.wav",
    }))
    assert r.status_code == 200
    assert engine.calls[0]["language"] == "pt"


# ---------------------------------------------------------------------------
# Tunable params
# ---------------------------------------------------------------------------


def test_tunable_params_forwarded_when_present(client, engine) -> None:
    r = client.post("/v1/generate", json=_payload(params={
        "ref_audio_path": "/data/tmp/a.wav",
        "temperature": 0.9, "top_k": 30, "top_p": 0.8,
        "repetition_penalty": 4.0, "length_penalty": 1.2, "speed": 1.1,
    }))
    assert r.status_code == 200
    call = engine.calls[0]
    assert call["temperature"] == 0.9
    assert call["top_k"] == 30
    assert call["top_p"] == 0.8
    assert call["repetition_penalty"] == 4.0
    assert call["length_penalty"] == 1.2
    assert call["speed"] == 1.1


def test_null_tunable_params_are_omitted(client, engine) -> None:
    """Frontends send explicit nulls; float(None) would raise TypeError."""
    r = client.post("/v1/generate", json=_payload(params={
        "ref_audio_path": "/data/tmp/a.wav",
        "temperature": None, "top_k": None, "top_p": None,
        "repetition_penalty": None, "length_penalty": None, "speed": None,
    }))
    assert r.status_code == 200
    call = engine.calls[0]
    for k in ("temperature", "top_k", "top_p", "repetition_penalty", "length_penalty", "speed"):
        assert k not in call


# ---------------------------------------------------------------------------
# CPU fallback — THE divergence from F5-TTS
# ---------------------------------------------------------------------------


def test_select_device_returns_cpu_without_cuda() -> None:
    """XTTS supports CPU: no GPU is a fallback, not a failure. _select_device
    must return 'cpu' (and NEVER raise) when CUDA is unavailable."""
    _CUDA_AVAILABLE["value"] = False
    assert srv._select_device() == "cpu"


def test_select_device_returns_cuda_when_available() -> None:
    _CUDA_AVAILABLE["value"] = True
    assert srv._select_device() == "cuda"
    _CUDA_AVAILABLE["value"] = False


def test_lazy_load_succeeds_on_cpu(monkeypatch) -> None:
    """End-to-end of the lazy loader on CPU: a missing GPU must still reach
    _load_state == 'ready'. F5-TTS would fail here; XTTS must not."""
    _CUDA_AVAILABLE["value"] = False
    srv._tts = None
    srv._load_state = "unloaded"
    srv._load_error = None

    mock_engine = _MockTTS()
    fake_api = types.ModuleType("TTS.api")
    fake_api.TTS = lambda *a, **k: mock_engine  # type: ignore[attr-defined]
    fake_pkg = types.ModuleType("TTS")
    monkeypatch.setitem(sys.modules, "TTS", fake_pkg)
    monkeypatch.setitem(sys.modules, "TTS.api", fake_api)

    assert srv._ensure_model_loaded() is True
    assert srv._load_state == "ready"
    assert srv._device == "cpu"
    assert mock_engine.device == "cpu"

    srv._tts = None
    srv._load_state = "unloaded"


# ---------------------------------------------------------------------------
# Concurrency: inference is serialized (max_concurrent_requests: 1)
# ---------------------------------------------------------------------------


def test_concurrent_generates_never_overlap(client, engine) -> None:
    """The XTTS GPT backbone is not concurrency-safe; the server holds
    _inference_lock around engine.tts to enforce max_concurrent_requests: 1."""
    import threading

    statuses: list[int] = []

    def fire(req_id: str) -> None:
        r = client.post("/v1/generate", json=_payload(
            request_id=req_id, params={"ref_audio_path": "/data/tmp/a.wav"},
        ))
        statuses.append(r.status_code)

    threads = [threading.Thread(target=fire, args=(f"req_conc_{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert statuses == [200, 200, 200, 200]
    assert len(engine.calls) == 4
    assert engine.overlap_detected is False, "two inferences ran concurrently"


def test_inference_lock_exists_at_module_level() -> None:
    import threading

    assert isinstance(srv._inference_lock, type(threading.Lock()))
