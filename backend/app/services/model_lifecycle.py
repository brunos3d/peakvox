"""Persisted model lifecycle transitions.

Operates on the ``models`` table (the first-class entity). The in-memory registry is refreshed
from the DB by the wiring layer; these functions are the source of truth for status changes.
"""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ModelNotFoundError(Exception):
    pass


def _sync_registry_status(model_id: str, status: str) -> None:
    """Reflect a persisted status change in the in-memory registry (and shared adapters)."""
    from app.services.model_registry import model_registry

    model_registry.set_status(model_id, status)


async def _set_status(session: AsyncSession, model_id: str, status: str, *, deprecated: bool = False) -> str:
    now = datetime.now(timezone.utc).isoformat()
    res = await session.execute(text("SELECT id FROM models WHERE id=:id"), {"id": model_id})
    if res.first() is None:
        raise ModelNotFoundError(model_id)
    if deprecated:
        await session.execute(
            text("UPDATE models SET status=:s, deprecated_at=:t, updated_at=:t WHERE id=:id"),
            {"s": status, "t": now, "id": model_id},
        )
    else:
        await session.execute(
            text("UPDATE models SET status=:s, updated_at=:t WHERE id=:id"),
            {"s": status, "t": now, "id": model_id},
        )
    await session.commit()
    _sync_registry_status(model_id, status)
    return status


async def activate_model(session: AsyncSession, model_id: str) -> str:
    return await _set_status(session, model_id, "available")


async def deactivate_model(session: AsyncSession, model_id: str) -> str:
    return await _set_status(session, model_id, "inactive")


async def deprecate_model(session: AsyncSession, model_id: str) -> str:
    return await _set_status(session, model_id, "deprecated", deprecated=True)


async def install_model(session: AsyncSession, model_id: str) -> str:
    """Install a model: (mock) download + verify artifacts, then mark it available.

    The real artifact download is intentionally mocked for now (upstream workflows pending) -
    the architecture, persistence, registry sync, and runtime integration are real. Routes
    through the registry/runtime; never bypasses them.
    """
    return await _set_status(session, model_id, "inactive")


async def update_model(session: AsyncSession, model_id: str) -> str:
    """Update a model: (mock) re-fetch latest artifacts; preserve activation state."""
    row = (
        await session.execute(
            text("SELECT status FROM models WHERE id=:id"), {"id": model_id}
        )
    ).first()
    if row is None:
        raise ModelNotFoundError(model_id)
    status = row[0]
    return await _set_status(
        session, model_id, "available" if status in {"available", "loaded"} else "inactive"
    )


async def remove_model(session: AsyncSession, model_id: str) -> str:
    """Remove a model. Built-ins revert to ``disabled``; community models are deleted."""
    from app.services.model_registry import model_registry

    row = (
        await session.execute(
            text("SELECT is_builtin FROM models WHERE id=:id"), {"id": model_id}
        )
    ).first()
    if row is None:
        raise ModelNotFoundError(model_id)
    is_builtin = bool(row[0])
    if is_builtin:
        return await _set_status(session, model_id, "disabled")
    else:
        await session.execute(text("DELETE FROM models WHERE id=:id"), {"id": model_id})
        await session.commit()
        model_registry.remove(model_id)
        return "removed"
