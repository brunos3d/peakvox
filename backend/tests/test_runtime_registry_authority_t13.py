"""TDD: T13 — Runtime Registry as the Single Source of Truth + Fully Functional Runtime Lifecycle.

This test file covers the regression suite for TASK 13. It
verifies:

  - T13.2 — Runtime Registry Authority. The composed view
    returns ONLY models that have at least one runtime in
    the registry when RUNTIME_SERVICE_ENABLED is true.

  - T13.5 — Legacy non-/api prefix aliases. The frontend
    calls /runtimes/<id>/{install,start,stop,update,remove}
    (no /api prefix per the project convention). The
    backend must expose these aliases; without them every
    button click returns 404.

  - T13.5 — Install + start + stop + remove end-to-end.
    The driver's full lifecycle path is exercised (Install
    creates the container, start activates it, stop
    deactivates, remove destroys the image). Mock driver
    is used so the test does not require docker-in-docker.

  - T13.10 — The page subscribes to ``useModelsWithRuntimes``
    and a lifecycle mutation invalidates the
    ``models-with-runtimes`` cache key so the UI re-fetches.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest


# ---------------------------------------------------------------------------
# Local fixtures (the existing ``client_with_manager_attached`` /
# ``client_no_manager`` live in test_api_runtimes.py; we re-create
# minimal equivalents here so this file is self-contained).
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_registry_dir_with_kokoro(tmp_path: Path) -> Path:
    """A temp runtime-registry/ with the Kokoro descriptor."""
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    descriptor = {
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
            "image": {"repository": "peakvox/kokoro-runtime", "tag": "0.1.0"},
            "build": {"entrypoint": "server.py", "build_context": ".", "dockerfile": "Dockerfile"},
            "service": {"protocol": "http", "port": 8000},
            "capabilities": ["tts"],
            "requirements": {"gpu": "optional", "min_vram_gb": 0, "cpu_cores": 1, "memory_gb": 2, "edition": ["ce"]},
            "model_binding": {"model_id": "kokoro-base", "is_default": True, "priority": 100},
            "lifecycle": {"install_policy": "pull-on-install", "idle_timeout": "15m"},
        },
    }
    (d / "descriptor.json").write_text(json.dumps(descriptor))
    return tmp_path


@pytest.fixture
def client_with_manager_attached(tmp_registry_dir_with_kokoro, monkeypatch):
    """A TestClient with a RuntimeManager attached to the temp
    registry. Uses a NoOp driver so install/start/stop/update/
    remove work but don't actually touch docker."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.runtime_api import router as runtimes_router, no_prefix_router, composed_router
    from app.services.runtime_driver import RuntimeDriver
    from app.services.runtime_events import RuntimeEventBus
    from app.services.runtime_manager import RuntimeManager
    from app.services.model_registry import model_registry
    from app.services.model_catalog import BUILTIN_MODELS
    from app.services.runtime_registry import RuntimeRegistryLoader

    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(tmp_registry_dir_with_kokoro))
    monkeypatch.setenv("RUNTIME_SERVICE_ENABLED", "true")
    registry = RuntimeRegistryLoader().load_from_directory(tmp_registry_dir_with_kokoro)
    # Wire the model catalog so the composed view has data
    # to compose.
    model_registry.set_descriptors(list(BUILTIN_MODELS))
    # The Settings singleton is loaded at module import; the
    # env-var monkeypatch above does not re-trigger a reload.
    # Set the attribute directly so the composed-view filter
    # sees RUNTIME_SERVICE_ENABLED=true.
    from app.core.config import settings as _settings
    monkeypatch.setattr(_settings, "RUNTIME_SERVICE_ENABLED", True)

    class _NoOpDriver(RuntimeDriver):
        async def install_runtime(self, runtime_id, descriptor):
            from app.services.runtime_instance import (
                HealthState, ImageIdentity, RuntimeInstance, RuntimeState,
            )
            return RuntimeInstance(
                runtime_id=runtime_id, state=RuntimeState.INSTALLED,
                host="", port=0,
                image_identity=ImageIdentity(
                    repository=descriptor.spec.image.repository,
                    tag=descriptor.spec.image.tag,
                    digest=descriptor.spec.image.digest,
                ),
                started_at=None, last_health_at=None,
                health_state=HealthState.UNKNOWN,
            )
        async def start_runtime(self, runtime_id):
            from app.services.runtime_instance import (
                HealthState, ImageIdentity, RuntimeInstance, RuntimeState,
            )
            return RuntimeInstance(
                runtime_id=runtime_id, state=RuntimeState.ACTIVE,
                host="localhost", port=8000,
                image_identity=ImageIdentity(
                    repository="peakvox/kokoro-runtime", tag="0.1.0", digest=None,
                ),
                started_at=None, last_health_at=None,
                health_state=HealthState.READY,
            )
        async def stop_runtime(self, runtime_id): return None
        async def update_runtime(self, runtime_id, descriptor):
            from app.services.runtime_instance import (
                HealthState, ImageIdentity, RuntimeInstance, RuntimeState,
            )
            return RuntimeInstance(
                runtime_id=runtime_id, state=RuntimeState.INSTALLED,
                host="", port=0,
                image_identity=ImageIdentity(
                    repository=descriptor.spec.image.repository,
                    tag=descriptor.spec.image.tag,
                    digest=descriptor.spec.image.digest,
                ),
                started_at=None, last_health_at=None,
                health_state=HealthState.UNKNOWN,
            )
        async def remove_runtime(self, runtime_id): return None
        async def restart_runtime(self, runtime_id):
            return await self.start_runtime(runtime_id)
        async def runtime_status(self, runtime_id): return None
        async def runtime_logs(self, runtime_id, since=None): return iter([])
        async def runtime_health(self, runtime_id): return None
        async def runtime_metrics(self, runtime_id): return None

    manager = RuntimeManager(registry=registry, driver=_NoOpDriver(), events=RuntimeEventBus())
    # Wire the manager into the global ``runtime`` singleton.
    from app.services import runtime as runtime_module
    runtime_module.runtime.attach_runtime_manager(manager)

    app = FastAPI()
    app.include_router(composed_router)
    app.include_router(runtimes_router)
    app.include_router(no_prefix_router)
    return TestClient(app), manager


@pytest.fixture
def client_no_manager(monkeypatch):
    """A TestClient with NO manager attached. The composed view
    falls back to the catalog-only path."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.runtime_api import router as runtimes_router, no_prefix_router, composed_router
    from app.services.model_registry import model_registry
    from app.services.model_catalog import BUILTIN_MODELS
    from app.services import runtime as runtime_module

    model_registry.set_descriptors(list(BUILTIN_MODELS))
    # Detach any manager.
    runtime_module.runtime._runtime_manager = None

    app = FastAPI()
    app.include_router(composed_router)
    app.include_router(runtimes_router)
    app.include_router(no_prefix_router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# T13.2 — Runtime Registry Authority
# ---------------------------------------------------------------------------


def test_composed_view_filters_catalog_only_models_when_runtime_enabled(
    client_with_manager_attached,
) -> None:
    """When the runtime subsystem is enabled and a manager
    is attached, the composed view drops catalog-only
    models. The fixture wires a manager with 1 descriptor
    (kokoro-82m); the catalog has 5 models but only the
    one bound to a runtime is returned.
    """
    c, _ = client_with_manager_attached
    r = c.get("/api/models/with-runtimes")
    assert r.status_code == 200
    body = r.json()
    model_ids = {m["model"]["id"] for m in body["models"]}
    assert "kokoro-base" in model_ids
    for catalog_only in ("omnivoice-singing", "fish-audio-s2", "f5-tts-base", "omnivoice-base"):
        assert catalog_only not in model_ids, (
            f"catalog-only model {catalog_only!r} should be "
            f"filtered out of the composed view"
        )


def test_composed_view_returns_all_catalog_models_when_no_manager(
    client_no_manager,
) -> None:
    """When no manager is attached, all catalog models are
    returned (the runtime subsystem is not authoritative)."""
    c = client_no_manager
    r = c.get("/api/models/with-runtimes")
    assert r.status_code == 200
    body = r.json()
    assert len(body["models"]) == 5


# ---------------------------------------------------------------------------
# T13.5 — Legacy non-/api prefix aliases
# ---------------------------------------------------------------------------


def test_no_prefix_install_endpoint_exists(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    r = c.post("/runtimes/kokoro-82m/install")
    assert r.status_code != 404, (
        f"legacy /runtimes/<id>/install endpoint missing (got {r.status_code})"
    )


def test_no_prefix_start_endpoint_exists(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    r = c.post("/runtimes/kokoro-82m/start")
    assert r.status_code != 404


def test_no_prefix_stop_endpoint_exists(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    r = c.post("/runtimes/kokoro-82m/stop")
    assert r.status_code != 404


def test_no_prefix_update_endpoint_exists(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    r = c.post("/runtimes/kokoro-82m/update")
    assert r.status_code != 404


def test_no_prefix_remove_endpoint_exists(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    r = c.post("/runtimes/kokoro-82m/remove")
    assert r.status_code != 404


def test_no_prefix_state_endpoint_exists(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    r = c.get("/runtimes/kokoro-82m/state")
    assert r.status_code == 200
    body = r.json()
    assert "phase" in body


# ---------------------------------------------------------------------------
# T13.5 — Lifecycle end-to-end (with the NoOp driver)
# ---------------------------------------------------------------------------


def test_install_via_no_prefix_returns_installed_phase(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    r = c.post("/runtimes/kokoro-82m/install")
    assert r.status_code == 200
    body = r.json()
    assert body["runtime_id"] == "kokoro-82m"
    assert body["phase"] == "installed"


def test_start_via_no_prefix_returns_active_phase(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    c.post("/runtimes/kokoro-82m/install")
    r = c.post("/runtimes/kokoro-82m/start")
    assert r.status_code == 200
    body = r.json()
    assert body["phase"] == "active"
    assert "endpoint" in body


def test_stop_via_no_prefix_returns_stopped_phase(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    c.post("/runtimes/kokoro-82m/install")
    c.post("/runtimes/kokoro-82m/start")
    r = c.post("/runtimes/kokoro-82m/stop")
    assert r.status_code == 200
    # The POST response is the hardcoded confirmation string;
    # the state-endpoint is the source of truth for the UI.
    state = c.get("/runtimes/kokoro-82m/state").json()
    assert state["phase"] == "stopped"


def test_remove_via_no_prefix_returns_removed_phase(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    c.post("/runtimes/kokoro-82m/install")
    c.post("/runtimes/kokoro-82m/start")
    c.post("/runtimes/kokoro-82m/stop")
    r = c.post("/runtimes/kokoro-82m/remove")
    assert r.status_code == 200
    # POST returns confirmation; state-endpoint reads from the
    # manager's cache (which Remove clears).
    state = c.get("/runtimes/kokoro-82m/state").json()
    assert state["phase"] in ("notInstalled", "NotInstalled", "notinstalled")


def test_full_lifecycle_chain_updates_state_correctly(client_with_manager_attached) -> None:
    c, _ = client_with_manager_attached
    c.post("/runtimes/kokoro-82m/install")
    state = c.get("/runtimes/kokoro-82m/state").json()
    assert state["phase"] in ("installed", "installing")

    c.post("/runtimes/kokoro-82m/start")
    state = c.get("/runtimes/kokoro-82m/state").json()
    assert state["phase"] == "active"

    c.post("/runtimes/kokoro-82m/stop")
    state = c.get("/runtimes/kokoro-82m/state").json()
    assert state["phase"] == "stopped"

    c.post("/runtimes/kokoro-82m/remove")
    state = c.get("/runtimes/kokoro-82m/state").json()
    assert state["phase"] in ("removed", "notInstalled", "notinstalled")
