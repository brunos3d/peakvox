import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.models.db import Voice
from app.services.model_adapter import ModelAdapter
from app.services.model_adapters.omnivoice_adapter import (
    OmniVoiceAdapter,
    OmniVoiceSingingAdapter,
)
from app.services.model_catalog import builtin_by_id
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
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/ad.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)  # backfill base variant
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


def _base():
    return OmniVoiceAdapter(builtin_by_id("omnivoice-base"))


def _singing():
    return OmniVoiceSingingAdapter(builtin_by_id("omnivoice-singing"))


def test_both_implement_the_contract():
    assert isinstance(_base(), ModelAdapter)
    assert isinstance(_singing(), ModelAdapter)


def test_capabilities_differ_by_model_not_class_name():
    assert _base().get_capabilities().supports_singing is False
    assert _singing().get_capabilities().supports_singing is True
    assert _singing().get_capabilities().supports_emotion_tags is True


def test_supported_tags_come_from_descriptor():
    assert "singing" in _singing().get_supported_tags()
    assert "singing" not in _base().get_supported_tags()


async def test_build_variant_creates_singing_variant_reusing_reference(session):
    voice = await get_voice_identity_by_public_id(session, "voice_ABC123")
    variant = await _singing().build_variant(db=session, voice=voice)
    assert variant.model_id == "omnivoice-singing"
    assert variant.artifacts["audio"] == "voices/uuid-1/reference.wav"

    # Resolvable afterwards
    resolved = await resolve_variant(session, voice_id=voice.id, model_id="omnivoice-singing")
    assert resolved is not None


async def test_build_variant_is_idempotent(session):
    voice = await get_voice_identity_by_public_id(session, "voice_ABC123")
    await _singing().build_variant(db=session, voice=voice)
    await _singing().build_variant(db=session, voice=voice)
    from sqlalchemy import select
    from app.models.db import VoiceVariant
    rows = (await session.execute(
        select(VoiceVariant).where(
            VoiceVariant.voice_id == voice.id, VoiceVariant.model_id == "omnivoice-singing"
        )
    )).scalars().all()
    assert len(rows) == 1
