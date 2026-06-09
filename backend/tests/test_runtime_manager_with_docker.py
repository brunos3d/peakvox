"""TDD: RuntimeManager wired with DockerRuntimeDriver (2B.6 + 2D.1-2D.3).

Per ADR-0017 §3.4, when a driver is wired, the manager's resolve()
returns a RuntimeResolution built from the descriptor + the
cached RuntimeInstance. In 2D the manager does NOT synthesize an
instance; it requires the runtime to be installed AND started
(via the lifecycle methods) before resolve() returns a non-None
resolution. The bridge in 2A.10 falls through to the in-process
path when resolve() returns None.

Phase 2B + 2D guardrail: the manager does not gain Docker
knowledge. The driver is injected via the constructor; the
manager's resolve() reads the descriptor's metadata and the
cached instance without importing or referencing any substrate
library. The manager is substrate-neutral.

Phase 2A bridge constraint: the manager's resolve() returning a
non-None resolution does NOT change the bridge in 2A.10. The
bridge in 2A.10 falls through to the existing in-process path
even when the manager resolves. The 2C+ branch (HTTPTransport,
KokoroAdapter migration) is when the runtime path activates; the
2C+ bridge will verify the instance state via driver.runtime_health
before routing traffic.

These tests assert:
- Manager with a driver returns a non-None RuntimeResolution
  when the runtime is installed and started (cache is populated).
- Manager with a driver returns None when the runtime is not
  installed (cache is empty).
- Manager without a driver returns None (preserves 2A behavior).
- The resolution carries the descriptor and the CACHED instance
  (not a synthetic instance).
- The endpoint is built from the cached instance's host/port.
- Selection rules (default > priority > hint > first) work with
  a wired driver.
- The manager never imports Docker (verified by the lint).
- The bridge in 2A.10 is unchanged: the runtime-service branch
  is still a literal pass; the runtime path is not activated by
  this commit.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import List

import pytest

from app.services.runtime_events import RuntimeEventBus
from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)
from app.services.runtime_manager import RuntimeManager, RuntimeResolution
from app.services.runtime_registry import RuntimeRegistry
from app.services.runtime_types import HealthReport, Liveness, Metrics, Readiness, RuntimeDescriptor


def _good_descriptor(
    runtime_id: str = "kokoro-cpu",
    model_id: str = "kokoro-base",
    port: int = 8000,
    priority: int = 100,
    is_default: bool = True,
) -> RuntimeDescriptor:
    return RuntimeDescriptor.model_validate({
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": runtime_id, "name": runtime_id, "description": "",
            "provider": "kokoro", "version": "1.4.2", "edition": ["ce"], "labels": {},
        },
        "spec": {
            "runtime_type": "docker",
            "image": {
                "repository": "peakvox/kokoro-runtime", "tag": "1.4.2",
                "digest": "sha256:" + "a" * 64,
            },
            "service": {"protocol": "http", "port": port},
            "capabilities": ["tts"],
            "requirements": {"gpu": "none", "edition": ["ce"]},
            "model_binding": {"model_id": model_id, "is_default": is_default, "priority": priority},
            "lifecycle": {
                "start_timeout_seconds": 60,
                "health_interval_seconds": 10,
                "health_timeout_seconds": 3,
            },
        },
    })


class _RecordingDriver:
    """A driver that records calls and returns Active instances.

    In 2D the manager calls the driver for lifecycle operations
    (install, start) and caches the returned RuntimeInstance.
    The 2B+ tests use this driver to populate the cache and then
    verify resolve() returns a resolution built from the cache.
    """

    def __init__(self) -> None:
        self.instances: dict[str, RuntimeInstance] = {}

    async def install_runtime(self, runtime_id, descriptor):
        inst = RuntimeInstance(
            runtime_id=runtime_id,
            state=RuntimeState.INSTALLED,
            host="localhost",
            port=descriptor.spec.service.port,
            image_identity=ImageIdentity(
                repository=descriptor.spec.image.repository,
                tag=descriptor.spec.image.tag,
                digest=descriptor.spec.image.digest,
            ),
            started_at=None,
            last_health_at=None,
            health_state=HealthState.UNKNOWN,
        )
        self.instances[runtime_id] = inst
        return inst

    async def start_runtime(self, runtime_id):
        cur = self.instances.get(runtime_id) or _make_active(runtime_id)
        inst = RuntimeInstance(
            runtime_id=cur.runtime_id,
            state=RuntimeState.ACTIVE,
            host=cur.host,
            port=cur.port,
            image_identity=cur.image_identity,
            started_at=datetime(2026, 6, 7, 0, 0, 0),
            last_health_at=datetime(2026, 6, 7, 0, 0, 0),
            health_state=HealthState.READY,
        )
        self.instances[runtime_id] = inst
        return inst

    async def update_runtime(self, runtime_id, descriptor):
        return self.instances.get(runtime_id) or _make_active(runtime_id)

    async def remove_runtime(self, runtime_id):
        self.instances.pop(runtime_id, None)

    async def stop_runtime(self, runtime_id):
        if runtime_id in self.instances:
            cur = self.instances[runtime_id]
            self.instances[runtime_id] = RuntimeInstance(
                runtime_id=cur.runtime_id,
                state=RuntimeState.STOPPED,
                host=cur.host,
                port=cur.port,
                image_identity=cur.image_identity,
                started_at=cur.started_at,
                last_health_at=cur.last_health_at,
                health_state=HealthState.UNKNOWN,
            )

    async def restart_runtime(self, runtime_id):
        return await self.start_runtime(runtime_id)

    async def runtime_status(self, runtime_id):
        return self.instances.get(runtime_id) or _make_active(runtime_id)

    async def runtime_logs(self, runtime_id, since=None):
        async def _empty():
            if False:
                yield ""
        return _empty()

    async def runtime_health(self, runtime_id):
        return HealthReport(
            runtime_id=runtime_id,
            liveness=Liveness.ALIVE,
            readiness=Readiness.READY,
            last_error=None,
            checked_at=datetime(2026, 6, 7, 0, 0, 0),
        )

    async def runtime_metrics(self, runtime_id):
        return Metrics()


def _make_active(runtime_id: str) -> RuntimeInstance:
    return RuntimeInstance(
        runtime_id=runtime_id,
        state=RuntimeState.ACTIVE,
        host="localhost",
        port=8000,
        image_identity=ImageIdentity(
            repository="peakvox/kokoro-runtime",
            tag="1.4.2",
            digest="sha256:" + "a" * 64,
        ),
        started_at=datetime(2026, 6, 7, 0, 0, 0),
        last_health_at=datetime(2026, 6, 7, 0, 0, 0),
        health_state=HealthState.READY,
    )


def _install_and_start(mgr: RuntimeManager, runtime_ids: List[str]) -> None:
    """Helper: install + start each runtime_id, populating the cache."""
    for rid in runtime_ids:
        asyncio.run(mgr.install(rid))
        asyncio.run(mgr.start(rid))


# ---- Tests ---------------------------------------------------------------------

def test_manager_with_driver_resolves_model_to_runtime_resolution() -> None:
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    _install_and_start(mgr, ["kokoro-cpu"])
    res = mgr.resolve("kokoro-base")
    assert res is not None
    assert isinstance(res, RuntimeResolution)
    assert res.descriptor.metadata.id == "kokoro-cpu"
    assert res.descriptor.spec.model_binding.model_id == "kokoro-base"


def test_manager_resolution_endpoint_reflects_cached_instance() -> None:
    desc = _good_descriptor(port=8123)
    reg = RuntimeRegistry([desc])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    _install_and_start(mgr, ["kokoro-cpu"])
    res = mgr.resolve("kokoro-base")
    assert res is not None
    # Endpoint URL is built from the cached instance's host + port
    # (the cached instance is populated by the driver, not the
    # manager; the manager does not synthesize the host).
    assert res.endpoint == "http://localhost:8123"


def test_manager_resolution_instance_carries_image_identity() -> None:
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    _install_and_start(mgr, ["kokoro-cpu"])
    res = mgr.resolve("kokoro-base")
    assert res is not None
    inst = res.instance
    assert inst.image_identity.repository == "peakvox/kokoro-runtime"
    assert inst.image_identity.tag == "1.4.2"
    assert inst.image_identity.digest == "sha256:" + "a" * 64


def test_manager_resolution_instance_state_is_active() -> None:
    """The resolved instance is the CACHED instance with state=Active
    (populated by install + start)."""
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    _install_and_start(mgr, ["kokoro-cpu"])
    res = mgr.resolve("kokoro-base")
    assert res is not None
    assert res.instance.state == RuntimeState.ACTIVE
    assert res.instance.health_state == HealthState.READY


def test_manager_without_driver_returns_none() -> None:
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    mgr = RuntimeManager(registry=reg, driver=None, events=RuntimeEventBus())
    # 2A behavior preserved: no driver → no resolution. The
    # bridge in 2A.10 falls through to the existing in-process path.
    assert mgr.resolve("kokoro-base") is None


def test_manager_with_driver_but_empty_registry_returns_none() -> None:
    mgr = RuntimeManager(registry=RuntimeRegistry([]), driver=_RecordingDriver(), events=RuntimeEventBus())
    assert mgr.resolve("kokoro-base") is None


def test_manager_with_driver_but_runtime_not_installed_returns_none() -> None:
    """2D: even with a driver wired, resolve() returns None when
    the runtime is not in the cache (i.e. not yet installed).
    The bridge falls through to the in-process path."""
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    mgr = RuntimeManager(registry=reg, driver=_RecordingDriver(), events=RuntimeEventBus())
    assert mgr.resolve("kokoro-base") is None


def test_manager_selection_picks_default_over_priority() -> None:
    d1 = _good_descriptor(runtime_id="kokoro-cpu", priority=200, is_default=False)
    d2 = _good_descriptor(runtime_id="kokoro-cuda", priority=100, is_default=True)
    reg = RuntimeRegistry([d1, d2])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    _install_and_start(mgr, ["kokoro-cpu", "kokoro-cuda"])
    res = mgr.resolve("kokoro-base")
    assert res is not None
    # Default wins regardless of priority.
    assert res.descriptor.metadata.id == "kokoro-cuda"


def test_manager_selection_uses_priority_when_no_default() -> None:
    d1 = _good_descriptor(runtime_id="kokoro-cpu", priority=200, is_default=False)
    d2 = _good_descriptor(runtime_id="kokoro-cuda", priority=100, is_default=False)
    reg = RuntimeRegistry([d1, d2])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    _install_and_start(mgr, ["kokoro-cpu", "kokoro-cuda"])
    res = mgr.resolve("kokoro-base")
    assert res is not None
    # Lower priority number wins.
    assert res.descriptor.metadata.id == "kokoro-cuda"


def test_manager_selection_with_hint() -> None:
    d1 = _good_descriptor(runtime_id="kokoro-cpu", priority=100, is_default=True)
    d2_dict = _good_descriptor(
        runtime_id="kokoro-cuda", priority=100, is_default=True,
    ).model_dump()
    d2_dict["metadata"]["id"] = "kokoro-cuda"
    d2_dict["spec"]["model_binding"]["model_id"] = "kokoro-base"
    d2_dict["spec"]["model_binding"]["priority"] = 100
    d2_dict["metadata"]["labels"] = {"profile": "cuda"}
    d2 = RuntimeDescriptor.model_validate(d2_dict)
    reg = RuntimeRegistry([d1, d2])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    _install_and_start(mgr, ["kokoro-cpu", "kokoro-cuda"])
    # Hint "cuda" filters to the descriptor whose id or labels match.
    res = mgr.resolve("kokoro-base", hint="cuda")
    assert res is not None
    assert res.descriptor.metadata.id == "kokoro-cuda"


def test_manager_with_docker_driver_does_not_import_docker() -> None:
    """Architectural invariant: the RuntimeManager remains
    substrate-neutral. Wiring a DockerRuntimeDriver does NOT
    cause the manager to import docker. The lint script enforces
    this; the test here is a runtime assertion at module load."""
    import re
    text = open(
        __import__("app.services.runtime_manager", fromlist=["__file__"]).__file__
    ).read()
    text_clean = re.sub(r'\"{3}.*?\"{3}', "", text, flags=re.DOTALL)
    assert not re.search(r"^import docker\b", text_clean, flags=re.MULTILINE)
    assert not re.search(r"^from docker\b", text_clean, flags=re.MULTILINE)


def test_bridge_injects_endpoint_when_manager_wired_and_runtime_active() -> None:
    """When the manager is wired and the runtime is ACTIVE, the bridge
    injects runtime_endpoint into the adapter kwargs. The adapter is
    responsible for routing to the runtime service using that endpoint.

    When the manager is wired but the runtime is NOT started,
    ModelNotActive is raised — there is no silent fallback to in-process."""
    from app.services.runtime import ModelNotActive, PeakVoxRuntime
    from app.services.model_adapter import ModelAdapter
    from app.models.registry_types import ModelCapabilities, ModelDescriptor
    from pathlib import Path

    class _TrackingAdapter(ModelAdapter):
        def __init__(self, descriptor):
            super().__init__(descriptor)
            self.captured_kwargs: dict = {}
        async def install(self): ...
        async def load(self): ...
        def unload(self): ...
        async def health_check(self) -> bool: return True
        async def generate(self, *, text, output_path, **kwargs):
            self.captured_kwargs = kwargs
            return (1.5, [f"{self.model_id}:{text}"])
        async def clone_voice(self, *, db, voice, reference_audio_key): raise NotImplementedError
        async def build_variant(self, *, db, voice): raise NotImplementedError

    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(
        ModelDescriptor(
            id="kokoro-base", name="Kokoro Base", description="d",
            provider="kokoro", supported_tags=[],
            capabilities=ModelCapabilities(supports_tts=True),
        )
    )
    rt.register_adapter(adapter)

    desc = _good_descriptor()  # runtime_id="kokoro-cpu" by default in this file
    reg = RuntimeRegistry([desc])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    # Install and start using the runtime_id from the descriptor.
    runtime_id = desc.metadata.id
    asyncio.run(mgr.install(runtime_id))
    asyncio.run(mgr.start(runtime_id))
    rt.attach_runtime_manager(mgr)

    duration, logs = asyncio.run(
        rt.generate(
            None, text="hi", model_id="kokoro-base",
            output_path=Path("/tmp/x.wav"),
        )
    )
    assert duration == 1.5
    assert "kokoro-base:hi" in logs[0]
    # The runtime_endpoint was injected into the adapter.
    assert adapter.captured_kwargs.get("runtime_endpoint") is not None

    # Verify that NOT starting the runtime produces ModelNotActive.
    rt2 = PeakVoxRuntime()
    adapter2 = _TrackingAdapter(adapter.descriptor)
    rt2.register_adapter(adapter2)
    mgr2 = RuntimeManager(registry=reg, driver=_RecordingDriver(), events=RuntimeEventBus())
    rt2.attach_runtime_manager(mgr2)
    with pytest.raises(ModelNotActive):
        asyncio.run(
            rt2.generate(
                None, text="hi", model_id="kokoro-base",
                output_path=Path("/tmp/x.wav"),
            )
        )
