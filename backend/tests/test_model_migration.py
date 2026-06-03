import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.migrations import run_migrations


@pytest.fixture
async def engine(tmp_path):
    db_path = tmp_path / "models.db"
    eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    yield eng
    await eng.dispose()


async def _columns(engine, table):
    async with engine.begin() as conn:
        res = await conn.execute(text(f"PRAGMA table_info({table})"))
        return {row[1] for row in res.fetchall()}


async def _fetchall(engine, sql):
    async with engine.begin() as conn:
        res = await conn.execute(text(sql))
        return res.fetchall()


async def test_models_table_created_and_seeded(engine):
    async with engine.begin() as conn:
        await run_migrations(conn)

    rows = await _fetchall(engine, "SELECT id, is_default, status FROM models")
    ids = {r[0] for r in rows}
    assert {"omnivoice-base", "omnivoice-distilled", "omnivoice-singing"} <= ids

    defaults = [r[0] for r in rows if r[1]]
    assert defaults == ["omnivoice-base"]


async def test_generation_jobs_has_model_id_column(engine):
    async with engine.begin() as conn:
        await run_migrations(conn)
    assert "model_id" in await _columns(engine, "generation_jobs")


async def test_seed_is_idempotent_and_preserves_user_models(engine):
    async with engine.begin() as conn:
        await run_migrations(conn)
        # Simulate a user-registered custom model.
        await conn.execute(text(
            "INSERT INTO models (id, name, provider, version, status, is_default, is_builtin, "
            "created_at, updated_at) "
            "VALUES ('my-custom', 'Custom', 'omnivoice', '1.0.0', 'available', 0, 0, "
            "'2026-01-01', '2026-01-01')"
        ))

    # Re-run migrations: built-ins re-upserted, custom model untouched.
    async with engine.begin() as conn:
        await run_migrations(conn)

    rows = await _fetchall(engine, "SELECT id FROM models WHERE id='my-custom'")
    assert len(rows) == 1

    base = await _fetchall(engine, "SELECT supported_tags FROM models WHERE id='omnivoice-base'")
    assert base and base[0][0]  # supported_tags persisted as JSON, non-empty
