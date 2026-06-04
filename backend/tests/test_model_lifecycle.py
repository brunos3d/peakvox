import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.model_lifecycle import (
    activate_model, deactivate_model, deprecate_model, ModelNotFoundError,
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/lc.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def _status(session, model_id):
    res = await session.execute(text("SELECT status FROM models WHERE id=:id"), {"id": model_id})
    return res.scalar()


async def test_deactivate_then_activate(session):
    await deactivate_model(session, "omnivoice-base")
    assert await _status(session, "omnivoice-base") == "inactive"
    await activate_model(session, "omnivoice-base")
    assert await _status(session, "omnivoice-base") == "available"


async def test_deprecate_sets_status_and_timestamp(session):
    await deprecate_model(session, "omnivoice-base")
    assert await _status(session, "omnivoice-base") == "deprecated"
    res = await session.execute(text("SELECT deprecated_at FROM models WHERE id='omnivoice-base'"))
    assert res.scalar() is not None


async def test_unknown_model_raises(session):
    with pytest.raises(ModelNotFoundError):
        await activate_model(session, "does-not-exist")
