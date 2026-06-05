import struct
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.config import settings
from app.core.migrations import run_migrations
from app.models.db import VoiceVariant
from app.services.model_adapter import ModelAdapter
from app.services.model_adapters.fish_adapter import FishAudioAdapter
from app.services.model_adapters.omnivoice_adapter import OmniVoiceAdapter
from app.services.model_catalog import builtin_by_id
from app.services.runtime import PeakVoxRuntime
from app.services.voice_variant_repository import (
    get_voice_identity_by_public_id,
    resolve_variant,
)

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/fish.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


def _fish():
    return FishAudioAdapter(builtin_by_id("fish-audio-s2"))


def test_fish_implements_the_same_contract():
    assert isinstance(_fish(), ModelAdapter)


def test_fish_is_ce_only_and_declares_its_capabilities():
    desc = builtin_by_id("fish-audio-s2")
    assert desc is not None
    assert desc.provider == "fish-audio"
    assert desc.editions == ["community"]
    caps = _fish().get_capabilities()
    assert caps.supports_voice_cloning is True
    assert caps.supports_reference_audio is True


def test_fish_declares_reference_sample_realization():
    assert _fish().supported_realization_types == ["reference_sample"]


async def test_fish_build_variant_creates_fish_variant_for_existing_voice(session):
    voice = await get_voice_identity_by_public_id(session, "voice_ABC123")
    variant = await _fish().build_variant(db=session, voice=voice)
    assert variant.model_id == "fish-audio-s2"
    # Fish uses reference_sample realization (same as OmniVoice), not embedding.
    assert variant.artifact_type == "reference_sample"
    resolved = await resolve_variant(session, voice_id=voice.id, model_id="fish-audio-s2")
    assert resolved is not None


async def test_runtime_resolves_fish_with_no_runtime_change(session):
    rt = PeakVoxRuntime()
    rt.register_adapter(OmniVoiceAdapter(builtin_by_id("omnivoice-base")))
    rt.register_adapter(_fish())

    voice = await get_voice_identity_by_public_id(session, "voice_ABC123")
    await rt.get_adapter("fish-audio-s2").build_variant(db=session, voice=voice)

    fish = await rt.resolve(session, public_voice_id="voice_ABC123", model_id="fish-audio-s2")
    assert fish.model.id == "fish-audio-s2"
    assert isinstance(fish.adapter, FishAudioAdapter)
    assert fish.voice.public_voice_id == "voice_ABC123"


def test_fish_unavailable_in_cloud_edition():
    rt = PeakVoxRuntime()
    rt.register_adapter(_fish())
    assert rt.is_available("fish-audio-s2", edition="community") is True
    assert rt.is_available("fish-audio-s2", edition="cloud") is False


# --- HTTP client tests ---------------------------------------------------------


def _mock_response(status=200, json_data=None, content=b"RIFF...WAV..."):
    m = MagicMock(spec=httpx.Response)
    m.status_code = status
    m.json = MagicMock(return_value=json_data or {"status": "ok"})
    m.content = content
    m.text = "ok" if status < 400 else "error"
    if status < 400:
        m.raise_for_status = MagicMock()
    else:
        m.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=m)
        )
    return m


async def test_load_marks_healthy_when_server_responds():
    adapter = _fish()
    adapter._server_healthy = False
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(200, {"status": "ok"})
        await adapter.load()
    assert adapter._server_healthy is True


async def test_load_marks_unhealthy_when_server_unreachable():
    adapter = _fish()
    adapter._server_healthy = True
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("refused")):
        await adapter.load()
    assert adapter._server_healthy is False


async def test_health_check_returns_true_when_healthy():
    adapter = _fish()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(200, {"status": "ok"})
        assert await adapter.health_check() is True


async def test_health_check_returns_false_when_unreachable():
    adapter = _fish()
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("refused")):
        assert await adapter.health_check() is False


async def test_generate_raises_when_server_not_healthy(tmp_path):
    adapter = _fish()
    adapter._server_healthy = False
    with pytest.raises(RuntimeError, match="server is not healthy"):
        await adapter.generate(text="hello", output_path=tmp_path / "out.wav",
                               ref_audio_path="/nonexistent/test.wav")


async def test_generate_raises_when_no_ref_audio(tmp_path):
    adapter = _fish()
    adapter._server_healthy = True
    with pytest.raises(ValueError, match="requires reference audio"):
        await adapter.generate(text="hello", output_path=tmp_path / "out.wav")


async def test_generate_sends_request_and_writes_audio(tmp_path):
    adapter = _fish()
    adapter._server_healthy = True
    ref_path = tmp_path / "ref.wav"
    ref_path.write_bytes(b"dummy_wav_content")

    # Build a real WAV for the mocked server response: 1 sec at 16000 Hz mono 16-bit
    real_wav_path = tmp_path / "real.wav"
    with wave.open(str(real_wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00" * 16000)
    real_wav_bytes = real_wav_path.read_bytes()

    out_path = tmp_path / "out.wav"

    with patch.object(adapter, "_client") as mock_client_factory:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client_factory.return_value = mock_client
        mock_client.post = AsyncMock()
        mock_client.post.return_value = _mock_response(200, content=real_wav_bytes)

        duration, logs = await adapter.generate(
            text="hello world",
            output_path=out_path,
            ref_audio_path=str(ref_path),
            ref_text="hello",
        )

    assert out_path.exists()
    assert out_path.read_bytes() == real_wav_bytes
    assert duration > 0
    assert any("generated" in l for l in logs)


async def test_unload_clears_healthy_flag():
    adapter = _fish()
    adapter._server_healthy = True
    adapter.unload()
    assert adapter._server_healthy is False
