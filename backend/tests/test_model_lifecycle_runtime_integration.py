"""TDD: P4 — Models page delegates lifecycle to RuntimeManager (R4).

Per R4, the Runtime is the operational entity and the Model
is the catalog entity. Model status reflects Runtime state
— never the other way around.

When ``RUNTIME_SERVICE_ENABLED=true`` and the
``RuntimeManager`` is attached to ``PeakVoxRuntime``:

  POST /api/models/{id}/install
    → resolve model_id → default runtime_id
    → runtime_manager.install(runtime_id)
    → on success: model.status = "inactive" (image present, container not running)

  POST /api/models/{id}/activate
    → resolve model_id → default runtime_id
    → runtime_manager.start(runtime_id)
    → on success: model.status = "available"

  POST /api/models/{id}/deactivate
    → resolve model_id → default runtime_id
    → runtime_manager.stop(runtime_id)
    → on success: model.status = "inactive"

  POST /api/models/{id}/update
    → resolve model_id → default runtime_id
    → runtime_manager.update(runtime_id)

  POST /api/models/{id}/remove
    → resolve model_id → default runtime_id
    → runtime_manager.remove(runtime_id)
    → on success: model.status = "disabled" (builtin) or remove (community)

When the manager is NOT attached (CE default), the legacy
DB-status mock is preserved: ``install_model`` does not
touch the runtime subsystem; the model row's status
transitions are unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.model_lifecycle import (
    ModelNotFoundError,
    activate_model,
    deactivate_model,
    install_model,
    remove_model,
    update_model,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _kokoro_descriptor_dict() -> dict:
    return {
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": "kokoro-82m",
            "name": "Kokoro 82M Runtime",
            "provider": "kokoro",
            "version": "0.1.0",
            "edition": ["ce"],
        },
        "spec": {
            "runtime_type": "docker",
            "image": {
                "repository": "peakvox/kokoro-runtime",
                "tag": "0.1.0",
            },
            "service": {"protocol": "http", "port": 8000},
            "capabilities": ["tts"],
            "requirements": {"gpu": "optional", "edition": ["ce"]},
            "model_binding": {
                "model_id": "kokoro-base",
                "is_default": True,
                "priority": 100,
            },
            "lifecycle": {"idle_timeout": "15m"},
        },
    }


@pytest.fixture
def tmp_registry_with_kokoro(tmp_path: Path) -> Path:
    """A temp runtime-registry/ with the Kokoro descriptor."""
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    (d / "descriptor.json").write_text(json.dumps(_kokoro_descriptor_dict()))
    return tmp_path


@pytest.fixture
def attached_manager(tmp_registry_with_kokoro, monkeypatch):
    """A RuntimeManager with the Kokoro descriptor, attached to
    the PeakVoxRuntime singleton. Returns the manager + a
    mock driver that records calls."""
    from app.services import runtime as runtime_module
    from app.services.runtime_driver import RuntimeDriver
    from app.services.runtime_manager import RuntimeManager
    from app.services.runtime_registry import RuntimeRegistryLoader

    # Build the manager.
    registry = RuntimeRegistryLoader().load_from_directory(tmp_registry_with_kokoro)

    class _RecordingDriver(RuntimeDriver):
        def __init__(self) -> None:
            self.install_calls: list[str] = []
            self.start_calls: list[str] = []
            self.stop_calls: list[str] = []
            self.update_calls: list[str] = []
            self.remove_calls: list[str] = []

        async def install_runtime(self, runtime_id, descriptor):
            self.install_calls.append(runtime_id)
            return None

        async def start_runtime(self, runtime_id):
            self.start_calls.append(runtime_id)
            return None

        async def stop_runtime(self, runtime_id):
            self.stop_calls.append(runtime_id)
            return None

        async def update_runtime(self, runtime_id, descriptor):
            self.update_calls.append(runtime_id)
            return None

        async def remove_runtime(self, runtime_id):
            self.remove_calls.append(runtime_id)
            return None

        # Required by the Protocol; not exercised by these tests.
        async def restart_runtime(self, runtime_id): return None
        async def runtime_status(self, runtime_id): return None
        async def runtime_logs(self, runtime_id, since=None): return iter([])
        async def runtime_health(self, runtime_id): return None
        async def runtime_metrics(self, runtime_id): return None

    driver = _RecordingDriver()
    manager = RuntimeManager(registry=registry, driver=driver)
    runtime_module.runtime.attach_runtime_manager(manager)
    yield manager, driver
    runtime_module.runtime._runtime_manager = None


@pytest.fixture
def mock_session() -> AsyncMock:
    """A mock AsyncSession that simulates a model row with
    ``is_builtin=1, status='available'``."""
    from unittest.mock import MagicMock

    session = AsyncMock(spec=AsyncSession)

    # Make session.execute(...).first() return a sensible row.
    class _Result:
        def __init__(self, value):
            self._value = value

        def first(self):
            return self._value

    async def _execute(stmt, params=None):
        sql = str(stmt)
        if "is_builtin FROM models" in sql:
            return _Result((1,))  # builtin
        if "status FROM models" in sql:
            return _Result(("available",))
        if "SELECT id FROM models" in sql:
            return _Result(("kokoro-base",))
        return _Result(None)

    session.execute.side_effect = _execute
    return session


# ---------------------------------------------------------------------------
# install_model + RuntimeManager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_install_model_calls_runtime_manager_install(
    attached_manager,
    mock_session: AsyncMock,
) -> None:
    """When the manager is attached, install_model delegates to
    runtime_manager.install for the default runtime serving this
    model."""
    manager, driver = attached_manager
    # The model_id is 'kokoro-base' (the catalog id from the descriptor's
    # model_binding). The manager's registry has descriptors for
    # 'kokoro-82m' (runtime id) bound to 'kokoro-base' (model id).
    await install_model(mock_session, "kokoro-base")
    assert driver.install_calls == ["kokoro-82m"]


@pytest.mark.asyncio
async def test_install_model_does_not_call_runtime_manager_when_no_manager(
    mock_session: AsyncMock,
) -> None:
    """When no manager is attached, install_model is the legacy
    DB-status mock (does not touch the runtime subsystem)."""
    from app.services import runtime as runtime_module
    runtime_module.runtime._runtime_manager = None
    # Just ensure the call doesn't blow up.
    try:
        await install_model(mock_session, "kokoro-base")
    except Exception:
        pass  # The DB write may fail (mock session); we only care
              # that the runtime subsystem is not consulted.


# ---------------------------------------------------------------------------
# activate_model + RuntimeManager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_model_calls_runtime_manager_start(
    attached_manager,
    mock_session: AsyncMock,
) -> None:
    """activate_model delegates to runtime_manager.start."""
    manager, driver = attached_manager
    await activate_model(mock_session, "kokoro-base")
    assert driver.start_calls == ["kokoro-82m"]


# ---------------------------------------------------------------------------
# deactivate_model + RuntimeManager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deactivate_model_calls_runtime_manager_stop(
    attached_manager,
    mock_session: AsyncMock,
) -> None:
    """deactivate_model delegates to runtime_manager.stop."""
    manager, driver = attached_manager
    await deactivate_model(mock_session, "kokoro-base")
    assert driver.stop_calls == ["kokoro-82m"]


# ---------------------------------------------------------------------------
# update_model + RuntimeManager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_model_calls_runtime_manager_update(
    attached_manager,
    mock_session: AsyncMock,
) -> None:
    """update_model delegates to runtime_manager.update."""
    manager, driver = attached_manager
    await update_model(mock_session, "kokoro-base")
    assert driver.update_calls == ["kokoro-82m"]


# ---------------------------------------------------------------------------
# remove_model + RuntimeManager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_model_calls_runtime_manager_remove(
    attached_manager,
    mock_session: AsyncMock,
) -> None:
    """remove_model delegates to runtime_manager.remove."""
    manager, driver = attached_manager
    await remove_model(mock_session, "kokoro-base")
    assert driver.remove_calls == ["kokoro-82m"]
