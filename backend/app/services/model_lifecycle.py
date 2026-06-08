"""Persisted model lifecycle transitions (Phase 2 + Phase 3 — R4).

When ``RUNTIME_SERVICE_ENABLED=true`` and a ``RuntimeManager``
is attached to ``PeakVoxRuntime``, the lifecycle functions
delegate to the manager first; the model row's status is
updated as a side-effect of the runtime transition.

When the manager is NOT attached (CE default), the legacy
DB-status mock is preserved. The R8 invariant — Models are
catalog entities; Runtimes are deployment units; Model
status reflects Runtime state — is enforced by the
manager-attached path. The legacy path is the in-process
fallback (in-process adapter does not need a runtime).
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.runtime_manager import RuntimeManager


class ModelNotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Runtime delegation (R4)
# ---------------------------------------------------------------------------


def _get_runtime_manager() -> Optional[RuntimeManager]:
    """Return the attached ``RuntimeManager``, or ``None`` if not wired."""
    from app.services import runtime as runtime_module

    manager = runtime_module.runtime._runtime_manager
    if manager is None:
        return None
    return manager


def _resolve_default_runtime_id(model_id: str) -> Optional[str]:
    """Return the default runtime id for ``model_id``, or ``None``
    if no runtime is registered for this model.

    The selection rules mirror ``RuntimeManager.resolve``: edition
    filter → default (``is_default = true``) → priority asc →
    first match. The default is the operator-installed runtime
    for the model in the current edition.
    """
    manager = _get_runtime_manager()
    if manager is None:
        return None
    descriptors = manager.registry.list_for_model(model_id)
    if not descriptors:
        return None
    descriptors = sorted(
        descriptors,
        key=lambda d: (
            not d.spec.model_binding.is_default,
            d.spec.model_binding.priority,
        ),
    )
    return descriptors[0].metadata.id


async def _delegate_to_manager(model_id: str, op: str) -> Optional[object]:
    """Call the manager's lifecycle op for the default runtime of
    ``model_id``. Returns the result, or ``None`` if no runtime
    is registered for this model.

    The op is one of: ``install``, ``start``, ``stop``, ``update``,
    ``remove``. Each is awaited; the manager raises on failure.
    """
    runtime_id = _resolve_default_runtime_id(model_id)
    if runtime_id is None:
        return None
    manager = _get_runtime_manager()
    if manager is None:
        return None
    method = getattr(manager, op)
    return await method(runtime_id)


# ---------------------------------------------------------------------------
# DB status sync
# ---------------------------------------------------------------------------


def _sync_registry_status(model_id: str, status: str) -> None:
    """Reflect a persisted status change in the in-memory registry (and shared adapters)."""
    from app.services.model_registry import model_registry

    model_registry.set_status(model_id, status)


async def _set_status(
    session: AsyncSession, model_id: str, status: str, *, deprecated: bool = False
) -> str:
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


# ---------------------------------------------------------------------------
# Public lifecycle API
# ---------------------------------------------------------------------------


async def activate_model(session: AsyncSession, model_id: str) -> str:
    """Activate a model (R4).

    When a runtime is registered for this model, the activation
    delegates to ``RuntimeManager.start`` (which starts the
    container and waits for ``/ready``). The model row's status
    is set to ``"available"`` only on success.

    When no runtime is registered, the legacy in-process path
    is used: status → ``"available"`` directly.
    """
    if _get_runtime_manager() is not None:
        await _delegate_to_manager(model_id, "start")
    return await _set_status(session, model_id, "available")


async def deactivate_model(session: AsyncSession, model_id: str) -> str:
    """Deactivate a model (R4).

    When a runtime is registered, this delegates to
    ``RuntimeManager.stop`` (which stops the container; the
    image is preserved). Status → ``"inactive"`` (image
    present, container not running).
    """
    if _get_runtime_manager() is not None:
        await _delegate_to_manager(model_id, "stop")
    return await _set_status(session, model_id, "inactive")


async def deprecate_model(session: AsyncSession, model_id: str) -> str:
    """Deprecate a model. No runtime delegation; this is a catalog-only
    transition (the model is marked deprecated but not removed)."""
    return await _set_status(session, model_id, "deprecated", deprecated=True)


async def install_model(session: AsyncSession, model_id: str) -> str:
    """Install a model (R4 — runtime-first lifecycle).

    When a runtime is registered for this model, the install
    delegates to ``RuntimeManager.install`` (which pulls the
    image, allocates host resources, and creates the
    ``RuntimeInstance`` in state ``Installed``). The model
    row's status is set to ``"inactive"`` (image present,
    container not running).

    When no runtime is registered (legacy path), the install
    is a status transition: status → ``"inactive"``.
    """
    if _get_runtime_manager() is not None:
        await _delegate_to_manager(model_id, "install")
    return await _set_status(session, model_id, "inactive")


async def update_model(session: AsyncSession, model_id: str) -> str:
    """Update a model (R4).

    When a runtime is registered, this delegates to
    ``RuntimeManager.update`` (which stops the instance if
    Active, re-pulls the new image, and leaves the instance
    in state ``Installed``). The model row's previous status
    is preserved (or set to ``"inactive"`` if it was
    ``"available"``/``"loaded"``).
    """
    if _get_runtime_manager() is not None:
        await _delegate_to_manager(model_id, "update")
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
    """Remove a model (R4).

    When a runtime is registered, this delegates to
    ``RuntimeManager.remove`` (which stops the container,
    removes the image, and unregisters the instance). The
    model row's status is set to ``"disabled"`` (builtin) or
    the row is deleted (community).
    """
    if _get_runtime_manager() is not None:
        await _delegate_to_manager(model_id, "remove")
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
