import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.model_lifecycle import (
    activate_model, deactivate_model, install_model, remove_model, update_model, ModelNotFoundError,
)
from app.services.model_registry import ModelRegistry


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/mgmt.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def _status(session, model_id):
    res = await session.execute(text("SELECT status FROM models WHERE id=:id"), {"id": model_id})
    return res.scalar()


async def test_install_marks_model_installed_inactive(session):
    # Fish ships disabled; "install" (mock download/verify) makes it installed but inactive.
    await install_model(session, "fish-audio-s2")
    assert await _status(session, "fish-audio-s2") == "inactive"


async def test_activate_and_deactivate_toggle_activation(session):
    await install_model(session, "fish-audio-s2")
    await activate_model(session, "fish-audio-s2")
    assert await _status(session, "fish-audio-s2") == "available"
    await deactivate_model(session, "fish-audio-s2")
    assert await _status(session, "fish-audio-s2") == "inactive"


async def test_remove_builtin_disables_it(session):
    await install_model(session, "omnivoice-singing")
    await remove_model(session, "omnivoice-singing")
    assert await _status(session, "omnivoice-singing") == "disabled"


async def test_update_bumps_and_keeps_available(session):
    await update_model(session, "omnivoice-base")
    assert await _status(session, "omnivoice-base") == "available"


async def test_update_preserves_inactive_status(session):
    await install_model(session, "fish-audio-s2")
    await update_model(session, "fish-audio-s2")
    assert await _status(session, "fish-audio-s2") == "inactive"


async def test_unknown_model_raises(session):
    with pytest.raises(ModelNotFoundError):
        await install_model(session, "ghost-model")


def test_registry_set_descriptors_isolates_from_catalog_and_syncs_status():
    from app.services.model_catalog import builtin_by_id
    reg = ModelRegistry()
    reg.set_descriptors([builtin_by_id("omnivoice-base")])
    reg.set_status("omnivoice-base", "disabled")
    # Registry copy mutated...
    assert reg.get("omnivoice-base").status == "disabled"
    # ...but the static catalog object is untouched (no global leakage).
    assert builtin_by_id("omnivoice-base").status == "available"
