import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

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
    assert desc.editions == ["community"]  # CE-only (ADR-0005)
    caps = _fish().get_capabilities()
    assert caps.supports_voice_cloning is True
    assert caps.supports_reference_audio is True


async def test_fish_build_variant_creates_fish_variant_for_existing_voice(session):
    voice = await get_voice_identity_by_public_id(session, "voice_ABC123")
    variant = await _fish().build_variant(db=session, voice=voice)
    assert variant.model_id == "fish-audio-s2"
    # Fish uses a different realization format than OmniVoice — encapsulated in the variant.
    assert variant.artifact_type == "embedding"
    resolved = await resolve_variant(session, voice_id=voice.id, model_id="fish-audio-s2")
    assert resolved is not None


async def test_runtime_resolves_fish_with_no_runtime_change(session):
    # The SAME PeakVoxRuntime resolves a non-OmniVoice provider — proving extensibility.
    rt = PeakVoxRuntime()
    rt.register_adapter(OmniVoiceAdapter(builtin_by_id("omnivoice-base")))
    rt.register_adapter(_fish())

    voice = await get_voice_identity_by_public_id(session, "voice_ABC123")
    await rt.get_adapter("fish-audio-s2").build_variant(db=session, voice=voice)

    fish = await rt.resolve(session, public_voice_id="voice_ABC123", model_id="fish-audio-s2")
    assert fish.model.id == "fish-audio-s2"
    assert isinstance(fish.adapter, FishAudioAdapter)
    assert fish.voice.public_voice_id == "voice_ABC123"  # identity preserved across providers


def test_fish_unavailable_in_cloud_edition():
    rt = PeakVoxRuntime()
    rt.register_adapter(_fish())
    assert rt.is_available("fish-audio-s2", edition="community") is True
    assert rt.is_available("fish-audio-s2", edition="cloud") is False
