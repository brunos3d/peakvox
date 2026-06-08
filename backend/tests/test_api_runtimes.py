"""TDD: GET /api/runtimes — runtime-registry surface (Task 3).

A new endpoint surfaces the runtime-registry as the
authoritative source of runtime metadata. The Models page
renders from this endpoint when
``RUNTIME_SERVICE_ENABLED=true`` (R3).

Each runtime card carries:

  - descriptor metadata (id, name, provider, version, edition)
  - image (repository, tag, digest)
  - service contract (protocol, port, paths)
  - capabilities, requirements
  - model_binding (catalog id, is_default, priority)
  - lifecycle (install_policy, idle_timeout)
  - state (the manager's cached RuntimeInstance)

The endpoint is gated: when no manager is attached (CE
default), the response is 503 with a clear error. The
fallback (CE legacy) is the existing /api/models
endpoint.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.runtime import runtime as runtime_module
from app.services.runtime_manager import RuntimeManager
from app.services.runtime_registry import RuntimeRegistryLoader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_registry_dir(tmp_path: Path) -> Path:
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
            "image": {
                "repository": "peakvox/kokoro-runtime",
                "tag": "0.1.0",
            },
            "build": {
                "entrypoint": "server.py",
                "build_context": ".",
                "dockerfile": "Dockerfile",
            },
            "service": {
                "protocol": "http",
                "port": 8000,
            },
            "capabilities": ["tts"],
            "requirements": {
                "gpu": "optional",
                "min_vram_gb": 0,
                "cpu_cores": 1,
                "memory_gb": 2,
                "edition": ["ce"],
            },
            "model_binding": {
                "model_id": "kokoro-base",
                "is_default": True,
                "priority": 100,
            },
            "lifecycle": {
                "install_policy": "pull-on-install",
                "idle_timeout": "15m",
            },
        },
    }
    (d / "descriptor.json").write_text(json.dumps(descriptor))
    return tmp_path


@pytest.fixture
def client_with_manager_attached(tmp_registry_dir, monkeypatch):
    """A TestClient with a RuntimeManager attached. The
    manager's instance cache is empty (R6 — lazy activation)."""
    from fastapi import FastAPI
    from app.api.runtime_api import router as runtimes_router

    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(tmp_registry_dir))

    # Construct a manager and attach it. We do this directly
    # rather than calling wire_runtime_services (which would
    # construct the DockerRuntimeDriver and may not work in
    # the test environment).
    from app.services.runtime_driver import RuntimeDriver
    from app.services.runtime_events import RuntimeEventBus

    class _NoOpDriver(RuntimeDriver):
        async def install_runtime(self, runtime_id, descriptor): return None
        async def start_runtime(self, runtime_id): return None
        async def stop_runtime(self, runtime_id): return None
        async def update_runtime(self, runtime_id, descriptor): return None
        async def remove_runtime(self, runtime_id): return None
        async def restart_runtime(self, runtime_id): return None
        async def runtime_status(self, runtime_id): return None
        async def runtime_logs(self, runtime_id, since=None): return iter([])
        async def runtime_health(self, runtime_id): return None
        async def runtime_metrics(self, runtime_id): return None

    registry = RuntimeRegistryLoader().load_from_directory(tmp_registry_dir)
    driver = _NoOpDriver()
    manager = RuntimeManager(registry=registry, driver=driver, events=RuntimeEventBus())
    runtime_module.attach_runtime_manager(manager)

    app = FastAPI()
    app.include_router(runtimes_router)
    with TestClient(app) as c:
        yield c, manager
    # Reset for subsequent tests.
    runtime_module._runtime_manager = None


@pytest.fixture
def client_no_manager():
    """A TestClient with no manager attached (CE default)."""
    from fastapi import FastAPI
    from app.api.runtime_api import router as runtimes_router
    runtime_module._runtime_manager = None
    app = FastAPI()
    app.include_router(runtimes_router)
    with TestClient(app) as c:
        yield c
    runtime_module._runtime_manager = None


# ---------------------------------------------------------------------------
# /api/runtimes (list)
# ---------------------------------------------------------------------------


def test_list_runtimes_returns_503_when_no_manager_attached(
    client_no_manager,
) -> None:
    """When no manager is attached (CE default, RUNTIME_SERVICE_ENABLED=false),
    /api/runtimes returns 503. The legacy /api/models endpoint is the
    fallback."""
    r = client_no_manager.get("/api/runtimes")
    assert r.status_code == 503
    body = r.json()
    assert "RUNTIME_SERVICE_ENABLED" in body.get("detail", {}).get("message", "")


def test_list_runtimes_returns_kokoro_when_manager_attached(
    client_with_manager_attached,
) -> None:
    """When a manager is attached, /api/runtimes returns the
    Kokoro runtime from the runtime-registry."""
    c, manager = client_with_manager_attached
    r = c.get("/api/runtimes")
    assert r.status_code == 200
    body = r.json()
    assert "runtimes" in body
    assert len(body["runtimes"]) == 1
    runtime = body["runtimes"][0]
    assert runtime["runtime_id"] == "kokoro-82m"
    assert runtime["name"] == "Kokoro 82M Runtime"
    assert runtime["provider"] == "kokoro"
    assert runtime["image"]["repository"] == "peakvox/kokoro-runtime"
    assert runtime["image"]["tag"] == "0.1.0"
    assert runtime["service"]["port"] == 8000
    assert runtime["lifecycle"]["idle_timeout"] == "15m"
    assert runtime["model_binding"]["model_id"] == "kokoro-base"
    assert runtime["model_binding"]["is_default"] is True


def test_list_runtimes_state_phase_is_not_installed_at_startup(
    client_with_manager_attached,
) -> None:
    """At backend startup, the runtime is NotInstalled (R6 —
    lazy activation; the manager's cache is empty)."""
    c, manager = client_with_manager_attached
    r = c.get("/api/runtimes")
    body = r.json()
    runtime = body["runtimes"][0]
    assert runtime["state"]["phase"] == "NotInstalled"


# ---------------------------------------------------------------------------
# /api/runtimes/{id}/descriptor
# ---------------------------------------------------------------------------


def test_get_runtime_descriptor_returns_full_descriptor(
    client_with_manager_attached,
) -> None:
    """GET /api/runtimes/{id}/descriptor returns the full
    on-disk descriptor (not a transformed view)."""
    c, manager = client_with_manager_attached
    r = c.get("/api/runtimes/kokoro-82m/descriptor")
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["id"] == "kokoro-82m"
    assert body["spec"]["image"]["repository"] == "peakvox/kokoro-runtime"


def test_get_runtime_descriptor_404_for_unknown_runtime(
    client_with_manager_attached,
) -> None:
    """An unknown runtime id returns 404."""
    c, manager = client_with_manager_attached
    r = c.get("/api/runtimes/unknown-runtime/descriptor")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /api/runtimes/{id}/state
# ---------------------------------------------------------------------------


def test_get_runtime_state_returns_state_payload(
    client_with_manager_attached,
) -> None:
    """GET /api/runtimes/{id}/state returns the state of a single runtime."""
    c, manager = client_with_manager_attached
    r = c.get("/api/runtimes/kokoro-82m/state")
    assert r.status_code == 200
    body = r.json()
    assert body["runtime_id"] == "kokoro-82m"
    assert "phase" in body
    assert body["phase"] == "NotInstalled"  # at startup, R6
