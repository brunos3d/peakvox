"""ADR-0009 — voice_variant_artifacts table + active_artifact_id backfill migration."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def engine(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/art.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)  # split → omnivoice-base variant + artifact backfill
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s


async def test_artifacts_table_and_pointer_exist(session):
    cols = {
        r[1]
        for r in (await session.execute(text("PRAGMA table_info(voice_variants)"))).fetchall()
    }
    assert "active_artifact_id" in cols
    assert "error_message" in cols
    # The new table exists.
    await session.execute(text("SELECT * FROM voice_variant_artifacts LIMIT 1"))


async def test_backfill_creates_v1_artifact_and_sets_active_pointer(session):
    variant = (
        await session.execute(
            text(
                "SELECT id, artifacts, active_artifact_id, status FROM voice_variants "
                "WHERE model_id = 'omnivoice-base'"
            )
        )
    ).mappings().one()
    assert variant["status"] == "ready"
    assert variant["active_artifact_id"] is not None

    art = (
        await session.execute(
            text(
                "SELECT version, storage_keys FROM voice_variant_artifacts "
                "WHERE id = :aid"
            ),
            {"aid": variant["active_artifact_id"]},
        )
    ).mappings().one()
    assert art["version"] == 1
    # The v1 artifact carries the same storage keys the inline column held.
    assert "voices/uuid-1/reference.wav" in art["storage_keys"]


async def test_migration_is_idempotent(engine):
    # Re-running must not create a second artifact row for the same variant.
    async with engine.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        count = (
            await s.execute(text("SELECT COUNT(*) FROM voice_variant_artifacts"))
        ).scalar_one()
        assert count == 1


async def test_legacy_status_values_are_remapped(engine):
    # Simulate an ADR-0006-era variant row with a superseded status value.
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        await s.execute(
            text(
                "INSERT INTO voice_variants (id, voice_id, model_id, artifact_type, "
                "artifacts, params, source, status, created_at, updated_at) VALUES "
                "('vv-legacy','uuid-1','omnivoice-singing','reference_sample','{}','{}',"
                "'cloned','stale','2026-01-01','2026-01-01')"
            )
        )
        await s.commit()
    async with engine.begin() as conn:
        await run_migrations(conn)
    async with maker() as s:
        status = (
            await s.execute(
                text("SELECT status FROM voice_variants WHERE id = 'vv-legacy'")
            )
        ).scalar_one()
        assert status == "deprecated"
