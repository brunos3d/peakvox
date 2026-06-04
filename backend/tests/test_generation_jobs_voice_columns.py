import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.migrations import run_migrations


@pytest.fixture
async def engine(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/jobs.db", future=True)
    yield eng
    await eng.dispose()


async def test_generation_jobs_has_voice_columns(engine):
    async with engine.begin() as conn:
        await run_migrations(conn)
        res = await conn.execute(text("PRAGMA table_info(generation_jobs)"))
        cols = {row[1] for row in res.fetchall()}
    assert {"voice_id", "voice_variant_id"} <= cols
