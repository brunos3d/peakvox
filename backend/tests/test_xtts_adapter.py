"""Tests for the XTTS adapter (Task 30, ADR-0021).

XTTSAdapter is a sibling of F5TTSAdapter: reference_sample realization,
runtime-routed generation (no in-process execution), SOURCE_ASSET build
strategy, and a 600s transport timeout. Coverage:

- generate() raises without a runtime_endpoint (no in-process execution)
- cloning mode forwards ref_audio_path in params
- voice-optional mode omits ref_audio_path (runtime uses a built-in speaker)
- request body shape (text/voice_id/language/params/request_id)
- language passthrough
- supports_voice_optional capability is declared
- build strategy declares SOURCE_ASSET can_build
- realization type is reference_sample
- transport timeout is 600s
"""

from __future__ import annotations

import io
import wave
from unittest.mock import AsyncMock, patch

import pytest

from app.services.model_adapters.xtts_adapter import XTTSAdapter
from app.services.model_catalog import builtin_by_id


def _adapter() -> XTTSAdapter:
    return XTTSAdapter(builtin_by_id("xtts-v2"))


def _make_wav_bytes(duration_s: float = 1.0, sample_rate: int = 24000) -> bytes:
    n_frames = int(duration_s * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


async def _generate_and_capture_body(tmp_path, **kwargs) -> dict:
    adapter = _adapter()
    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9400"
    mock_transport.post_binary = AsyncMock(
        return_value=(_make_wav_bytes(), {"x-peakvox-duration-ms": "1000"})
    )

    with patch(
        "app.services.model_adapters.xtts_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        await adapter.generate(
            text="Hello world.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint="http://localhost:9400",
            **kwargs,
        )

    return mock_transport.post_binary.call_args[0][1]


# --- Guard: no in-process execution ----------------------------------------


async def test_generate_raises_when_no_runtime_endpoint(tmp_path):
    adapter = _adapter()
    with pytest.raises(RuntimeError, match="runtime container"):
        await adapter.generate(
            text="Hello.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint=None,
        )


# --- Request body / cloning vs. voice-optional -----------------------------


async def test_cloning_forwards_ref_audio_path(tmp_path):
    body = await _generate_and_capture_body(
        tmp_path,
        ref_audio_path="/data/tmp/ref.wav",
        language="pt",
    )
    assert body["params"]["ref_audio_path"] == "/data/tmp/ref.wav"
    assert body["language"] == "pt"
    assert body["text"] == "Hello world."


async def test_voice_optional_omits_ref_audio_path(tmp_path):
    """No ref audio → no ref_audio_path; the runtime falls back to a built-in
    studio speaker (supports_voice_optional)."""
    body = await _generate_and_capture_body(tmp_path)
    assert "ref_audio_path" not in body["params"]


async def test_request_body_has_request_id_and_voice_id(tmp_path):
    body = await _generate_and_capture_body(
        tmp_path, voice_id="voice_abc", job_id="job_xyz"
    )
    assert body["voice_id"] == "voice_abc"
    assert body["request_id"] == "job_xyz"


async def test_default_language_is_en(tmp_path):
    body = await _generate_and_capture_body(tmp_path)
    assert body["language"] == "en"


# --- Capability / strategy / realization -----------------------------------


async def test_voice_optional_capability_is_declared():
    assert _adapter().get_capabilities().supports_voice_optional is True


def test_supports_multilingual_and_cloning():
    caps = _adapter().get_capabilities()
    assert caps.supports_voice_cloning is True
    assert caps.supports_multilingual is True
    assert caps.supports_reference_audio is True


def test_does_not_overclaim_streaming_or_training():
    caps = _adapter().get_capabilities()
    assert caps.supports_streaming is False
    assert caps.supports_custom_training is False
    assert caps.supports_emotion_tags is False


def test_build_strategy_declares_source_asset():
    strategies = XTTSAdapter.get_build_strategies()
    assert any(
        s.creation_source == "SOURCE_ASSET" and s.can_build for s in strategies
    )


def test_realization_type_is_reference_sample():
    assert _adapter().supported_realization_types == ["reference_sample"]


# --- Transport timeout ------------------------------------------------------


def test_transport_timeout_is_600s():
    """XTTS on CPU is slow; the transport must not time out and retry mid-run
    (which would also re-enter the serialized engine). Mirrors F5-TTS."""
    adapter = _adapter()
    created = []

    class CapturingTransport:
        def __init__(self, base_url, bearer_token, timeout_seconds=30.0):
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            created.append(self)

    with patch(
        "app.services.model_adapters.xtts_adapter.HTTPTransport",
        CapturingTransport,
    ):
        adapter._get_transport("http://localhost:9400")

    assert len(created) == 1
    assert created[0].timeout_seconds == 600.0
