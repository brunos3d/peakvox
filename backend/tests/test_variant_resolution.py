import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.variant_resolution import resolve_generation_inputs, VariantUnavailableError

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{\"num_step\":32}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/gr.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def test_resolves_inputs_for_omnivoice(session):
    inputs = await resolve_generation_inputs(
        session, public_voice_id="voice_ABC123", model_id="omnivoice-base"
    )
    assert inputs.voice_id == "uuid-1"
    assert inputs.ref_audio_key == "voices/uuid-1/reference.wav"
    assert inputs.ref_text == "olá"
    assert inputs.generation_defaults["num_step"] == 32


async def test_unknown_voice_raises(session):
    with pytest.raises(VariantUnavailableError):
        await resolve_generation_inputs(session, public_voice_id="voice_NOPE", model_id="omnivoice-base")


async def test_missing_variant_raises(session):
    with pytest.raises(VariantUnavailableError):
        await resolve_generation_inputs(session, public_voice_id="voice_ABC123", model_id="kokoro")
