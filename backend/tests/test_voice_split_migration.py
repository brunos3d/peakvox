import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.migrations import run_migrations


@pytest.fixture
async def engine(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/split.db", future=True)
    yield eng
    await eng.dispose()


async def _seed_profile(engine):
    async with engine.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(
            "INSERT INTO voice_profiles "
            "(id, public_voice_id, owner_id, name, audio_filename, transcript, "
            " generation_defaults, is_public, is_community_voice, is_preset_voice, "
            " is_favorite, status, usage_count, created_at, updated_at) "
            "VALUES ('uuid-1', 'voice_ABC123', 'owner-1', 'Bruno', "
            " 'voices/uuid-1/reference.wav', 'olá', '{\"num_step\": 32}', 0, 0, 0, 0, 'ready', 3, "
            " '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        ))


async def test_backfill_creates_voice_and_variant(engine):
    await _seed_profile(engine)
    async with engine.begin() as conn:
        await run_migrations(conn)  # second run performs the split

    async with engine.begin() as conn:
        v = (await conn.execute(text(
            "SELECT id, public_voice_id, name FROM voices WHERE public_voice_id='voice_ABC123'"
        ))).first()
        assert v is not None
        assert v[0] == "uuid-1" and v[2] == "Bruno"

        var = (await conn.execute(text(
            "SELECT model_id, artifacts, params FROM voice_variants WHERE voice_id='uuid-1'"
        ))).first()
        assert var is not None
        assert var[0] == "omnivoice-base"
        assert "voices/uuid-1/reference.wav" in var[1]


async def test_backfill_is_idempotent(engine):
    await _seed_profile(engine)
    async with engine.begin() as conn:
        await run_migrations(conn)
    async with engine.begin() as conn:
        await run_migrations(conn)  # must not duplicate
    async with engine.begin() as conn:
        count = (await conn.execute(text(
            "SELECT COUNT(*) FROM voices WHERE public_voice_id='voice_ABC123'"
        ))).scalar()
        assert count == 1
        vcount = (await conn.execute(text(
            "SELECT COUNT(*) FROM voice_variants WHERE voice_id='uuid-1'"
        ))).scalar()
        assert vcount == 1
