"""Regression tests for Task 24: OmniVoice adapter HTTP routing.

Root cause fixed in T24: OmniVoiceAdapter.generate() unconditionally raised
RuntimeError instead of routing through HTTPTransport when runtime_endpoint
was provided. This file ensures that regression never recurs.

Coverage:
- generate() raises when runtime_endpoint=None (no in-process execution)
- generate() routes via HTTPTransport when runtime_endpoint is set
- Transport timeout is 600s (CPU inference is slow, 30s default is too short)
- Duration is read from X-Peakvox-Duration-Ms header when present
- Duration falls back to WAV introspection when header is absent
- ref_audio_path / ref_text / instruct are forwarded in params
- Transport is reused (cached) for the same base_url
"""

from __future__ import annotations

import io
import wave
from unittest.mock import AsyncMock, patch

import pytest

from app.services.model_adapters.omnivoice_adapter import OmniVoiceAdapter
from app.services.model_catalog import builtin_by_id


def _adapter() -> OmniVoiceAdapter:
    return OmniVoiceAdapter(builtin_by_id("omnivoice-base"))


def _make_wav_bytes(duration_s: float = 1.0, sample_rate: int = 24000) -> bytes:
    """Return minimal valid 16-bit PCM WAV bytes for duration_s seconds."""
    n_frames = int(duration_s * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Guard: no in-process execution
# ---------------------------------------------------------------------------


async def test_generate_raises_when_no_runtime_endpoint(tmp_path):
    """generate() must raise RuntimeError if runtime_endpoint is None.

    The OmniVoice adapter has no in-process inference path. Callers
    that omit runtime_endpoint get a clear error pointing to the Models
    page, not a silent fallback.
    """
    adapter = _adapter()
    with pytest.raises(RuntimeError, match="runtime container"):
        await adapter.generate(
            text="Hello.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint=None,
        )


async def test_generate_raises_message_includes_model_id(tmp_path):
    """The RuntimeError message names the model so the user knows which container to start."""
    adapter = _adapter()
    with pytest.raises(RuntimeError, match="omnivoice-base"):
        await adapter.generate(
            text="Hello.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint=None,
        )


# ---------------------------------------------------------------------------
# HTTP routing
# ---------------------------------------------------------------------------


async def test_generate_routes_via_http_transport(tmp_path):
    """generate() must POST to /v1/generate on the runtime container."""
    adapter = _adapter()
    wav = _make_wav_bytes(2.0)

    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9200"
    mock_transport.post_binary = AsyncMock(
        return_value=(wav, {"x-peakvox-duration-ms": "2000"})
    )

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        duration, logs = await adapter.generate(
            text="Hello.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint="http://localhost:9200",
        )

    mock_transport.post_binary.assert_called_once()
    call_args = mock_transport.post_binary.call_args
    assert call_args[0][0] == "/v1/generate"
    body = call_args[0][1]
    assert body["text"] == "Hello."
    assert duration == 2.0


async def test_generate_writes_wav_bytes_to_output_path(tmp_path):
    """generate() must write the runtime's response bytes to output_path."""
    adapter = _adapter()
    wav = _make_wav_bytes(1.0)
    out = tmp_path / "speech.wav"

    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9200"
    mock_transport.post_binary = AsyncMock(return_value=(wav, {}))

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        await adapter.generate(
            text="Hi.",
            output_path=out,
            runtime_endpoint="http://localhost:9200",
        )

    assert out.read_bytes() == wav


async def test_generate_duration_from_header(tmp_path):
    """Duration is taken from X-Peakvox-Duration-Ms when the header is present."""
    adapter = _adapter()
    wav = _make_wav_bytes(0.5)

    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9200"
    mock_transport.post_binary = AsyncMock(
        return_value=(wav, {"x-peakvox-duration-ms": "3750"})
    )

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        duration, _ = await adapter.generate(
            text="Hi.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint="http://localhost:9200",
        )

    assert duration == pytest.approx(3.75)


async def test_generate_duration_fallback_to_wav_introspection(tmp_path):
    """Duration falls back to WAV frame count / sample_rate when header absent."""
    adapter = _adapter()
    wav = _make_wav_bytes(2.5)  # exactly 2.5 seconds

    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9200"
    # No duration header
    mock_transport.post_binary = AsyncMock(return_value=(wav, {}))

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        duration, _ = await adapter.generate(
            text="Test.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint="http://localhost:9200",
        )

    assert duration == pytest.approx(2.5, abs=0.01)


# ---------------------------------------------------------------------------
# Param forwarding
# ---------------------------------------------------------------------------


async def test_generate_forwards_ref_audio_path(tmp_path):
    """ref_audio_path is placed inside the params dict sent to the runtime."""
    adapter = _adapter()
    wav = _make_wav_bytes()

    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9200"
    mock_transport.post_binary = AsyncMock(return_value=(wav, {}))

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        await adapter.generate(
            text="Hi.",
            output_path=tmp_path / "out.wav",
            ref_audio_path="/data/voices/sample.wav",
            runtime_endpoint="http://localhost:9200",
        )

    body = mock_transport.post_binary.call_args[0][1]
    assert body["params"]["ref_audio_path"] == "/data/voices/sample.wav"


async def test_generate_forwards_instruct(tmp_path):
    """instruct is placed inside the params dict sent to the runtime."""
    adapter = _adapter()
    wav = _make_wav_bytes()

    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9200"
    mock_transport.post_binary = AsyncMock(return_value=(wav, {}))

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        await adapter.generate(
            text="Hi.",
            output_path=tmp_path / "out.wav",
            instruct="male, elderly, moderate pitch",
            runtime_endpoint="http://localhost:9200",
        )

    body = mock_transport.post_binary.call_args[0][1]
    assert body["params"]["instruct"] == "male, elderly, moderate pitch"


# ---------------------------------------------------------------------------
# Transport timeout
# ---------------------------------------------------------------------------


def test_transport_timeout_is_600s():
    """HTTPTransport must be created with timeout_seconds=600 for OmniVoice.

    OmniVoice is a 0.6B LLM running on CPU in CE; inference takes ~3.5 min.
    The default 30s timeout causes spurious HTTP 0 (network timeout) errors.
    """
    adapter = _adapter()
    created_transports = []

    class CapturingTransport:
        def __init__(self, base_url, bearer_token, timeout_seconds=30.0):
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            created_transports.append(self)

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        CapturingTransport,
    ):
        adapter._get_transport("http://localhost:9200")

    assert len(created_transports) == 1
    assert created_transports[0].timeout_seconds == 600.0


def test_transport_is_reused_for_same_base_url():
    """_get_transport() returns the same object for the same base_url."""
    adapter = _adapter()

    class MinimalTransport:
        def __init__(self, base_url, bearer_token, timeout_seconds=30.0):
            self.base_url = base_url

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        MinimalTransport,
    ):
        t1 = adapter._get_transport("http://localhost:9200")
        t2 = adapter._get_transport("http://localhost:9200")

    assert t1 is t2


async def test_generate_raises_runtime_error_on_transport_failure(tmp_path):
    """HTTPTransportError is wrapped in RuntimeError with a human-readable message."""
    from app.services.adapter_transport.http_transport import HTTPTransportError

    adapter = _adapter()

    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9200"
    mock_transport.post_binary = AsyncMock(
        side_effect=HTTPTransportError(500, {"error": {"category": "internal", "message": "upstream error"}})
    )

    with patch(
        "app.services.model_adapters.omnivoice_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        with pytest.raises(RuntimeError, match="OmniVoice runtime error"):
            await adapter.generate(
                text="Hi.",
                output_path=tmp_path / "out.wav",
                runtime_endpoint="http://localhost:9200",
            )
