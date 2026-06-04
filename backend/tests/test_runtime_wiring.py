from app.services.model_adapters.omnivoice_adapter import (
    OmniVoiceAdapter,
    OmniVoiceSingingAdapter,
)


def test_wire_runtime_registers_family_adapters():
    from app.services.runtime import runtime
    from app.services.model_wiring import wire_runtime

    wire_runtime()

    assert isinstance(runtime.get_adapter("omnivoice-base"), OmniVoiceAdapter)
    assert isinstance(runtime.get_adapter("omnivoice-singing"), OmniVoiceSingingAdapter)
    # The base adapter is NOT the singing subclass — distinct adapter classes, one contract.
    assert not isinstance(runtime.get_adapter("omnivoice-base"), OmniVoiceSingingAdapter)


def test_wire_registry_registers_singing_provider():
    from app.services.model_registry import model_registry
    from app.services.model_wiring import wire_registry

    wire_registry()
    # Both provider factories are registered (not instantiated — that would require torch).
    assert callable(model_registry._provider_factories.get("omnivoice"))
    assert callable(model_registry._provider_factories.get("omnivoice-singing"))


async def test_wire_registry_from_database_preserves_persisted_status(tmp_path):
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.migrations import run_migrations
    from app.services.model_registry import model_registry
    from app.services.model_wiring import wire_registry_from_database

    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/wire.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text("UPDATE models SET status='inactive' WHERE id='fish-audio-s2'"))
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        await wire_registry_from_database(session)
    await eng.dispose()

    assert model_registry.get("fish-audio-s2").status == "inactive"
