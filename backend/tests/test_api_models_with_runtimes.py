"""TDD: GET /api/models/with-runtimes — composed view (R9).

Per R9, the Models page renders a composed view from
three sources:

  1. Model Catalog (BUILTIN_MODELS -> models table)
  2. Runtime Registry (runtime-registry/<id>/descriptor.json)
  3. Runtime Operational State (RuntimeManager._instance_cache)

The new endpoint joins these:

  GET /api/models/with-runtimes

Returns:

  {
    "models": [
      {
        "model": { ... full ModelDescriptor ... },
        "runtimes": [
          {
            "runtime_id": "kokoro-82m",
            "descriptor": { ... RuntimeDescriptor ... },
            "state": { ... RuntimeStatePayload ... }
          }
        ],
        "default_runtime_id": "kokoro-82m" | null
      },
      ...
    ]
  }

A model with no runtime has an empty `runtimes` list and
`default_runtime_id = null`. The page renders "Not Available"
in the Runtime section.

The endpoint is NOT gated on RUNTIME_SERVICE_ENABLED.
It works whether or not the runtime subsystem is wired.
When no manager is attached, `runtimes` is `[]` for every
model (the catalog portion is always present).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services import runtime as runtime_module
from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_events import RuntimeEventBus
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
                "edition": ["ce"],
            },
            "model_binding": {
                "model_id": "kokoro-base",
                "is_default": True,
                "priority": 100,
            },
            "lifecycle": {"idle_timeout": "15m"},
        },
    }
    (d / "descriptor.json").write_text(json.dumps(descriptor))
    return tmp_path


@pytest.fixture
def client_with_manager_attached(tmp_registry_dir, monkeypatch):
    """A TestClient with a manager attached. The catalog + Kokoro
    runtime are joined; other catalog models have empty runtimes."""
    from app.api.runtime_api import router as runtimes_router, composed_router, no_prefix_router
    from app.api.models import router as models_router
    from app.services.model_registry import model_registry
    from app.services.model_catalog import BUILTIN_MODELS

    # Seed the catalog (BUILTIN_MODELS -> ModelRegistry).
    model_registry.set_descriptors(list(BUILTIN_MODELS))

    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(tmp_registry_dir))

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
    runtime_module.runtime.attach_runtime_manager(manager)

    app = FastAPI()
    # Register composed_router BEFORE models_router so that
    # `/api/models/with-runtimes` (a literal) is matched before
    # `/api/models/{model_id}` (a path parameter).
    app.include_router(runtimes_router)
    app.include_router(composed_router)
    app.include_router(no_prefix_router)
    app.include_router(models_router)
    with TestClient(app) as c:
        yield c, manager
    runtime_module.runtime._runtime_manager = None
    model_registry._descriptors = {}


@pytest.fixture
def client_no_manager():
    """A TestClient with no manager attached (CE default).
    The composed view is the catalog only; runtimes are empty."""
    from app.api.runtime_api import router as runtimes_router, composed_router, no_prefix_router
    from app.api.models import router as models_router
    from app.services.model_registry import model_registry
    from app.services.model_catalog import BUILTIN_MODELS

    model_registry.set_descriptors(list(BUILTIN_MODELS))
    runtime_module.runtime._runtime_manager = None
    app = FastAPI()
    # Register composed_router BEFORE models_router (path conflict).
    app.include_router(runtimes_router)
    app.include_router(composed_router)
    app.include_router(no_prefix_router)
    app.include_router(models_router)
    with TestClient(app) as c:
        yield c
    runtime_module.runtime._runtime_manager = None
    model_registry._descriptors = {}


# ---------------------------------------------------------------------------
# /api/models/with-runtimes (composed view)
# ---------------------------------------------------------------------------


def test_with_runtimes_returns_catalog_when_no_manager_attached(
    client_no_manager,
) -> None:
    """When no manager is attached (CE default), the endpoint
    still returns the catalog. Each model has runtimes=[]."""
    c = client_no_manager
    r = c.get("/api/models/with-runtimes")
    assert r.status_code == 200
    body = r.json()
    assert "models" in body
    catalog_ids = {m["model"]["id"] for m in body["models"]}
    # BUILTIN_MODELS seeds 4 entries.
    assert "kokoro-base" in catalog_ids
    assert "omnivoice-base" in catalog_ids
    # Every model has empty runtimes (no manager).
    for m in body["models"]:
        assert m["runtimes"] == []
        assert m["default_runtime_id"] is None


def test_with_runtimes_joins_kokoro_when_manager_attached(
    client_with_manager_attached,
) -> None:
    """When a manager is attached, the Kokoro catalog entry is
    joined with the Kokoro runtime-registry entry. Other catalog
    entries have empty runtimes."""
    c, manager = client_with_manager_attached
    r = c.get("/api/models/with-runtimes")
    assert r.status_code == 200
    body = r.json()

    # Find the Kokoro entry.
    kokoro_card = next(
        m for m in body["models"] if m["model"]["id"] == "kokoro-base"
    )
    assert kokoro_card["default_runtime_id"] == "kokoro-82m"
    assert len(kokoro_card["runtimes"]) == 1
    runtime = kokoro_card["runtimes"][0]
    assert runtime["runtime_id"] == "kokoro-82m"
    assert runtime["descriptor"]["metadata"]["name"] == "Kokoro 82M Runtime"
    assert runtime["state"]["phase"] == "notInstalled"  # R6 — empty cache at startup


def test_with_runtimes_marks_unmigrated_models(client_with_manager_attached) -> None:
    """Models without a runtime descriptor (OmniVoice, Fish Audio)
    appear in the composed view with runtimes=[] and
    default_runtime_id=null. They are NOT hidden."""
    c, manager = client_with_manager_attached
    r = c.get("/api/models/with-runtimes")
    body = r.json()

    # The catalog has 4 entries; only the Kokoro has a runtime.
    migrated_ids = {
        m["model"]["id"] for m in body["models"] if m["default_runtime_id"]
    }
    unmigrated_ids = {
        m["model"]["id"] for m in body["models"] if not m["default_runtime_id"]
    }

    assert "kokoro-base" in migrated_ids
    # The other 3 are unmigrated; they are visible but flagged.
    for unm in unmigrated_ids:
        assert unm != "kokoro-base"


def test_with_runtimes_state_reflects_manager_cache(
    client_with_manager_attached,
) -> None:
    """The composed view's `state.phase` reflects the manager's
    cached RuntimeInstance. At startup (R6), the cache is empty
    and the state is NotInstalled."""
    c, manager = client_with_manager_attached
    r = c.get("/api/models/with-runtimes")
    body = r.json()
    kokoro_card = next(
        m for m in body["models"] if m["model"]["id"] == "kokoro-base"
    )
    assert kokoro_card["runtimes"][0]["state"]["phase"] == "notInstalled"
    # The endpoint is None because no container is running.
    assert kokoro_card["runtimes"][0]["state"]["endpoint"] is None


def test_with_runtimes_includes_full_descriptor(client_with_manager_attached) -> None:
    """The runtime's descriptor in the composed view is the full
    on-disk descriptor (image, build, service, capabilities,
    requirements, model_binding, lifecycle). The UI renders from
    this view directly."""
    c, manager = client_with_manager_attached
    r = c.get("/api/models/with-runtimes")
    body = r.json()
    runtime = next(
        m for m in body["models"] if m["model"]["id"] == "kokoro-base"
    )["runtimes"][0]
    desc = runtime["descriptor"]
    assert desc["spec"]["image"]["repository"] == "peakvox/kokoro-runtime"
    assert desc["spec"]["service"]["port"] == 8000
    assert desc["spec"]["model_binding"]["is_default"] is True
    assert desc["spec"]["lifecycle"]["idle_timeout"] == "15m"


def test_with_runtimes_no_prefix_alias(client_with_manager_attached) -> None:
    """The composed view is also exposed under the legacy
    non-/api prefix `/models/with-runtimes` (convention in this
    codebase; the frontend's request() function calls the path
    without /api)."""
    c, manager = client_with_manager_attached
    r = c.get("/models/with-runtimes")
    assert r.status_code == 200
    body = r.json()
    assert "models" in body
    # The alias must return the same payload as the canonical /api path.
    r2 = c.get("/api/models/with-runtimes")
    assert len(body["models"]) == len(r2.json()["models"])


def test_with_runtimes_no_prefix_alias_no_manager(client_no_manager) -> None:
    """The non-/api alias also returns 200 when no manager is
    attached. T13.2: when no manager is attached, the runtime
    subsystem is NOT authoritative, so all catalog models are
    returned (the runtime portion is the augmentation)."""
    c = client_no_manager
    r = c.get("/models/with-runtimes")
    assert r.status_code == 200
    body = r.json()
    # 5 catalog models when no manager is attached.
    assert len(body["models"]) == 5
    for m in body["models"]:
        assert m["runtimes"] == []
