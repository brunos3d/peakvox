import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.voice_variant_repository import resolve_variant_stamp

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/stamp.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def test_stamp_for_omnivoice_returns_voice_and_variant(session):
    voice_id, variant_id = await resolve_variant_stamp(
        session, voice_internal_id="uuid-1", model_id="omnivoice-base"
    )
    assert voice_id == "uuid-1"
    assert variant_id is not None


async def test_stamp_for_unbuilt_model_has_no_variant(session):
    voice_id, variant_id = await resolve_variant_stamp(
        session, voice_internal_id="uuid-1", model_id="kokoro"
    )
    assert voice_id == "uuid-1"
    assert variant_id is None
