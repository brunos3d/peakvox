"""Regression tests for Task 24: F5-TTS adapter ref_text resolution (ASR bypass).

Root cause fixed in T24: when a SOURCE_ASSET voice had no stored transcript
(variant params {"transcript": None}), the adapter sent ref_text="" to the
runtime. f5-tts 1.0.3 responds to an empty ref_text by auto-transcribing the
reference clip with Whisper ASR, which crashes on torch 2.12 with
"Cannot copy out of meta tensor; no data!".

The fix: the adapter resolves an *effective* ref_text (explicit arg → stored
variant transcript → upstream ref_text param) and, when reference audio is
present but no transcript exists anywhere, injects a neutral placeholder so
the runtime never enters the ASR path.

Coverage:
- explicit ref_text arg wins
- variant "transcript" param is used when no explicit arg
- upstream "ref_text" param is used as third choice
- placeholder injected when ref audio present and no transcript anywhere
- no ref_text key at all in voice-optional mode (no ref audio)
- transcript=None / transcript="" are treated as missing (falsy guard)
- voice-optional requests omit ref_audio_path entirely
"""

from __future__ import annotations

import io
import wave
from unittest.mock import AsyncMock, patch

import pytest

from app.services.model_adapters.f5_adapter import F5TTSAdapter
from app.services.model_catalog import builtin_by_id


PLACEHOLDER = "Voice cloning reference audio sample."


def _adapter() -> F5TTSAdapter:
    return F5TTSAdapter(builtin_by_id("f5-tts-base"))


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
    """Run adapter.generate() against a mocked transport; return the request body."""
    adapter = _adapter()
    mock_transport = AsyncMock()
    mock_transport.base_url = "http://localhost:9300"
    mock_transport.post_binary = AsyncMock(return_value=(_make_wav_bytes(), {}))

    with patch(
        "app.services.model_adapters.f5_adapter.HTTPTransport",
        return_value=mock_transport,
    ):
        await adapter.generate(
            text="Hello world.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint="http://localhost:9300",
            **kwargs,
        )

    return mock_transport.post_binary.call_args[0][1]


# ---------------------------------------------------------------------------
# Guard: no in-process execution
# ---------------------------------------------------------------------------


async def test_generate_raises_when_no_runtime_endpoint(tmp_path):
    adapter = _adapter()
    with pytest.raises(RuntimeError, match="runtime container"):
        await adapter.generate(
            text="Hello.",
            output_path=tmp_path / "out.wav",
            runtime_endpoint=None,
        )


# ---------------------------------------------------------------------------
# effective_ref_text precedence
# ---------------------------------------------------------------------------


async def test_explicit_ref_text_arg_wins(tmp_path):
    body = await _generate_and_capture_body(
        tmp_path,
        ref_audio_path="/data/tmp/ref.wav",
        ref_text="explicit transcript",
        params={"transcript": "stored transcript"},
    )
    assert body["params"]["ref_text"] == "explicit transcript"


async def test_stored_variant_transcript_used_when_no_explicit_arg(tmp_path):
    """The variant's stored "transcript" param feeds ref_text.

    This is the normal path for sample voices whose transcript was saved at
    variant build time (e.g. Bruno PT-BR).
    """
    body = await _generate_and_capture_body(
        tmp_path,
        ref_audio_path="/data/tmp/ref.wav",
        params={"transcript": "stored transcript"},
    )
    assert body["params"]["ref_text"] == "stored transcript"


async def test_upstream_ref_text_param_is_third_choice(tmp_path):
    body = await _generate_and_capture_body(
        tmp_path,
        ref_audio_path="/data/tmp/ref.wav",
        params={"ref_text": "upstream text"},
    )
    assert body["params"]["ref_text"] == "upstream text"


# ---------------------------------------------------------------------------
# ASR bypass: the T24 crash scenario
# ---------------------------------------------------------------------------


async def test_placeholder_injected_when_transcript_is_none(tmp_path):
    """THE regression: ref audio + {"transcript": None} must NOT yield empty ref_text.

    Empty ref_text triggers Whisper ASR inside f5-tts, which crashes on
    torch 2.12 with a meta-tensor error. The adapter must inject a
    placeholder transcript instead.
    """
    body = await _generate_and_capture_body(
        tmp_path,
        ref_audio_path="/data/tmp/fireship.wav",
        params={"transcript": None},
    )
    assert body["params"]["ref_text"] == PLACEHOLDER


async def test_placeholder_injected_when_transcript_is_empty_string(tmp_path):
    """Empty-string transcript is treated as missing, not forwarded verbatim."""
    body = await _generate_and_capture_body(
        tmp_path,
        ref_audio_path="/data/tmp/fireship.wav",
        params={"transcript": ""},
    )
    assert body["params"]["ref_text"] == PLACEHOLDER


async def test_placeholder_injected_when_no_params_at_all(tmp_path):
    body = await _generate_and_capture_body(
        tmp_path,
        ref_audio_path="/data/tmp/fireship.wav",
    )
    assert body["params"]["ref_text"] == PLACEHOLDER


# ---------------------------------------------------------------------------
# Voice-optional mode (no reference audio)
# ---------------------------------------------------------------------------


async def test_voice_optional_sends_no_ref_audio_and_no_placeholder(tmp_path):
    """Without ref audio, neither ref_audio_path nor a placeholder ref_text is sent.

    The runtime then uses its bundled default voice (supports_voice_optional).
    Injecting the placeholder here would mismatch the default reference clip's
    actual speech and degrade cloning conditioning.
    """
    body = await _generate_and_capture_body(tmp_path)
    assert "ref_audio_path" not in body["params"]
    assert "ref_text" not in body["params"]


async def test_voice_optional_capability_is_declared():
    """F5-TTS declares supports_voice_optional; the UI gates on this capability."""
    caps = _adapter().get_capabilities()
    assert caps.supports_voice_optional is True


def test_omnivoice_does_not_declare_voice_optional():
    """OmniVoice requires a voice input — the per-model UI difference is
    capability-driven (Constitution Art. III §10), not a bug."""
    from app.services.model_adapters.omnivoice_adapter import OmniVoiceAdapter

    caps = OmniVoiceAdapter(builtin_by_id("omnivoice-base")).get_capabilities()
    assert getattr(caps, "supports_voice_optional", False) is False
