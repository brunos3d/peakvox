import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.voice_variant_repository import (
    get_voice_identity_by_public_id, resolve_variant,
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
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/vr.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)  # backfill the split
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def test_get_identity_by_public_id(session):
    voice = await get_voice_identity_by_public_id(session, "voice_ABC123")
    assert voice is not None
    assert voice.id == "uuid-1"
    assert voice.public_voice_id == "voice_ABC123"


async def test_resolve_existing_omnivoice_variant(session):
    variant = await resolve_variant(session, voice_id="uuid-1", model_id="omnivoice-base")
    assert variant is not None
    assert variant.artifacts["audio"] == "voices/uuid-1/reference.wav"


async def test_resolve_missing_variant_returns_none(session):
    variant = await resolve_variant(session, voice_id="uuid-1", model_id="kokoro")
    assert variant is None
