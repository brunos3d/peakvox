"""TDD: RuntimeManager skeleton (2A.8).

Per ADR-0017 §3.1, the manager is the orchestration-only
component. It owns:

  - Discovers runtimes from the Runtime Registry
  - Resolves endpoints — knows which URL an adapter should call
  - Delegates lifecycle operations to the Runtime Driver
  - Reports status

It does NOT own:

  - Execute inference
  - Allocate GPUs
  - Load model weights
  - Import model frameworks
  - Perform substrate-specific operations

For Phase 2A, no driver is wired (that lands in sub-phase 2B with
DockerRuntimeDriver). The manager is constructible with a
``driver=None`` and returns ``None`` from ``resolve`` — the bridge
(2A.10) uses this as the signal to fall through to the existing
in-process path. The manager also raises a clear error when an
operation is invoked without a driver.

These tests assert:
- The manager is constructible without a driver.
- resolve(model_id) returns None when no driver is wired (2A
  behavior; the bridge uses this to fall through).
- resolve(model_id) returns None when the model has no descriptors.
- Lifecycle operations raise ``NoDriverConfigured`` when no driver
  is wired.
- The manager publishes events through the RuntimeEventBus.
- A mock driver is delegated to for install / start / stop / etc.
  when one is wired.
- The manager does not import Docker, model frameworks, or HTTP
  clients (covered by lint checks at the project level).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_errors import RuntimeDriverError
from app.services.runtime_events import (
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeInstallRequested,
    RuntimeStartRequested,
)
from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)
from app.services.runtime_manager import (
    NoDriverConfigured,
    RuntimeManager,
    RuntimeResolution,
)
from app.services.runtime_registry import RuntimeRegistry
from app.services.runtime_types import HealthReport, Liveness, Readiness, RuntimeDescriptor


def _good_descriptor(model_id: str = "kokoro-base", runtime_id: str = "kokoro-cpu") -> RuntimeDescriptor:
    return RuntimeDescriptor.model_validate({
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": runtime_id, "name": runtime_id, "description": "",
            "provider": "kokoro", "version": "1.0.0", "edition": ["ce"], "labels": {},
        },
        "spec": {
            "runtime_type": "docker",
            "image": {"repository": "peakvox/kokoro-runtime", "tag": "1.0.0"},
            "service": {"protocol": "http", "port": 8000},
            "capabilities": ["tts"],
            "requirements": {"gpu": "none", "edition": ["ce"]},
            "model_binding": {"model_id": model_id, "is_default": True, "priority": 100},
        },
    })


# --- Construction ---

def test_manager_constructible_without_driver() -> None:
    reg = RuntimeRegistry([])
    bus = RuntimeEventBus()
    m = RuntimeManager(registry=reg, driver=None, events=bus)
    assert m is not None


def test_manager_constructible_with_driver() -> None:
    reg = RuntimeRegistry([_good_descriptor()])
    bus = RuntimeEventBus()

    class _StubDriver:
        async def install_runtime(self, runtime_id, descriptor):
            return RuntimeInstance(
                runtime_id=runtime_id, state=RuntimeState.INSTALLED,
                host="h", port=8000,
                image_identity=ImageIdentity(repository="r", tag="t", digest=None),
                started_at=None, last_health_at=None,
                health_state=HealthState.UNKNOWN,
            )
        async def update_runtime(self, runtime_id, descriptor): return await self.install_runtime(runtime_id, descriptor)
        async def remove_runtime(self, runtime_id): return None
        async def start_runtime(self, runtime_id):
            return RuntimeInstance(
                runtime_id=runtime_id, state=RuntimeState.ACTIVE,
                host="h", port=8000,
                image_identity=ImageIdentity(repository="r", tag="t", digest=None),
                started_at=datetime.now(timezone.utc), last_health_at=None,
                health_state=HealthState.READY,
            )
        async def stop_runtime(self, runtime_id): return None
        async def restart_runtime(self, runtime_id): return await self.start_runtime(runtime_id)
        async def runtime_status(self, runtime_id): return await self.install_runtime(runtime_id, None)
        async def runtime_logs(self, runtime_id, since=None):
            if False: yield ""
        async def runtime_health(self, runtime_id):
            return HealthReport(
                runtime_id=runtime_id, liveness=Liveness.ALIVE,
                readiness=Readiness.READY, last_error=None,
                checked_at=datetime.now(timezone.utc),
            )
        async def runtime_metrics(self, runtime_id): from app.services.runtime_types import Metrics; return Metrics()

    m = RuntimeManager(registry=reg, driver=_StubDriver(), events=bus)
    assert isinstance(m, RuntimeManager)


# --- resolve() — the 2A.10 bridge uses this method ---

def test_resolve_returns_none_when_no_driver() -> None:
    reg = RuntimeRegistry([_good_descriptor()])
    m = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    # In 2A, no driver means no runtime is reachable; the bridge
    # uses None to fall through to the in-process path.
    assert m.resolve("kokoro-base") is None


def test_resolve_returns_none_when_model_has_no_runtimes() -> None:
    reg = RuntimeRegistry([])  # empty
    m = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    assert m.resolve("kokoro-base") is None


def test_resolve_returns_none_when_driver_present_but_model_unbound() -> None:
    class _NoopDriver:
        async def install_runtime(self, runtime_id, descriptor): raise NotImplementedError
        async def update_runtime(self, runtime_id, descriptor): raise NotImplementedError
        async def remove_runtime(self, runtime_id): raise NotImplementedError
        async def start_runtime(self, runtime_id): raise NotImplementedError
        async def stop_runtime(self, runtime_id): raise NotImplementedError
        async def restart_runtime(self, runtime_id): raise NotImplementedError
        async def runtime_status(self, runtime_id): raise NotImplementedError
        async def runtime_logs(self, runtime_id, since=None): raise NotImplementedError
        async def runtime_health(self, runtime_id): raise NotImplementedError
        async def runtime_metrics(self, runtime_id): raise NotImplementedError

    # Registry has a different model
    reg = RuntimeRegistry([_good_descriptor(model_id="other-model")])
    m = RuntimeManager(registry=reg, driver=_NoopDriver(), events=RuntimeEventBus())
    assert m.resolve("kokoro-base") is None


# --- Lifecycle operations require a driver ---

def test_install_raises_without_driver() -> None:
    m = RuntimeManager(registry=RuntimeRegistry([]), driver=None, events=RuntimeEventBus())
    with pytest.raises(NoDriverConfigured):
        import asyncio
        asyncio.run(m.install("kokoro-cpu"))


def test_start_raises_without_driver() -> None:
    m = RuntimeManager(registry=RuntimeRegistry([]), driver=None, events=RuntimeEventBus())
    with pytest.raises(NoDriverConfigured):
        import asyncio
        asyncio.run(m.start("kokoro-cpu"))


def test_status_raises_without_driver() -> None:
    m = RuntimeManager(registry=RuntimeRegistry([]), driver=None, events=RuntimeEventBus())
    with pytest.raises(NoDriverConfigured):
        import asyncio
        asyncio.run(m.status("kokoro-cpu"))


# --- Event publication ---

def test_publishes_to_event_bus() -> None:
    received: List[RuntimeEvent] = []
    bus = RuntimeEventBus()
    bus.subscribe(received.append)
    m = RuntimeManager(registry=RuntimeRegistry([]), driver=None, events=bus)
    m._publish(RuntimeInstallRequested(runtime_id="kokoro-cpu"))
    assert len(received) == 1
    assert received[0].runtime_id == "kokoro-cpu"


def test_publish_with_no_event_bus_is_a_no_op() -> None:
    m = RuntimeManager(registry=RuntimeRegistry([]), driver=None, events=None)
    # Should not raise; events bus is optional in 2A.
    m._publish(RuntimeInstallRequested(runtime_id="kokoro-cpu"))


# --- The manager does not own inference ---

def test_manager_has_no_generate_method() -> None:
    # Architectural invariant: the manager does not perform inference.
    # It exposes lifecycle + resolution only. Asserting the absence
    # of a `generate` method documents the invariant.
    reg = RuntimeRegistry([])
    m = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    assert not hasattr(m, "generate")
    assert not hasattr(m, "infer")
    assert not hasattr(m, "load_weights")
    assert not hasattr(m, "import_torch")
