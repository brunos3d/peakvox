"""TDD: RuntimeManager wired with DockerRuntimeDriver (2B.6).

Per ADR-0017 §3.4, when a driver is wired, the manager's resolve()
returns a RuntimeResolution with the descriptor, a synthetic
runtime instance, and a reachable endpoint. In 2B the manager
does NOT call the driver to verify the instance state (that is
the 2C+ bridge's job); the resolution is built from the
descriptor's metadata alone.

Phase 2B guardrail: the manager does not gain Docker knowledge.
The driver is injected via the constructor; the manager's
resolve() reads the descriptor's service config and builds the
endpoint URL without importing or referencing any substrate
library. The manager is substrate-neutral.

Phase 2A bridge constraint: the manager's resolve() returning a
non-None resolution does NOT change the bridge in 2A.10. The
bridge in 2A.10 falls through to the existing in-process path
even when the manager resolves. The 2C+ branch (HTTPTransport,
KokoroAdapter migration) is when the runtime path activates; the
2C+ bridge will verify the instance state via driver.runtime_health
before routing traffic.

These tests assert:
- Manager with a driver returns a non-None RuntimeResolution.
- Manager without a driver returns None (preserves 2A behavior).
- The resolution carries the descriptor, a synthetic instance, and
  a reachable endpoint.
- The endpoint is built from the descriptor's service port
  (not from any substrate import).
- Selection rules (default > priority > hint > first) work with a
  wired driver.
- The manager never imports Docker (verified by the lint).
- The bridge in 2A.10 is unchanged: in 2B, the runtime-service
  branch is still a literal pass; the runtime path is not
  activated by this commit.
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


class _StubDriver:
    """A minimal driver stub that the manager depends on through the
    RuntimeDriver Protocol. The manager does not actually call the
    driver in 2B's resolve() (the instance is synthetic); this
    stub exists to satisfy the Protocol surface and to allow the
    test to verify the manager does not call the driver."""

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


# ---- Tests ---------------------------------------------------------------------

def test_manager_with_driver_resolves_model_to_runtime_resolution() -> None:
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    mgr = RuntimeManager(registry=reg, driver=_StubDriver(), events=RuntimeEventBus())
    res = mgr.resolve("kokoro-base")
    assert res is not None
    assert isinstance(res, RuntimeResolution)
    assert res.descriptor.metadata.id == "kokoro-cpu"
    assert res.descriptor.spec.model_binding.model_id == "kokoro-base"


def test_manager_resolution_endpoint_reflects_descriptor_port() -> None:
    desc = _good_descriptor(port=8123)
    reg = RuntimeRegistry([desc])
    mgr = RuntimeManager(registry=reg, driver=_StubDriver(), events=RuntimeEventBus())
    res = mgr.resolve("kokoro-base")
    assert res is not None
    # Endpoint URL is built from the descriptor's service port
    # (and a sensible default host — "localhost" for CE; configurable
    # in 2C+ for Cloud service-DNS).
    assert res.endpoint == "http://localhost:8123"


def test_manager_resolution_instance_carries_image_identity() -> None:
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    mgr = RuntimeManager(registry=reg, driver=_StubDriver(), events=RuntimeEventBus())
    res = mgr.resolve("kokoro-base")
    assert res is not None
    inst = res.instance
    assert inst.image_identity.repository == "peakvox/kokoro-runtime"
    assert inst.image_identity.tag == "1.4.2"
    assert inst.image_identity.digest == "sha256:" + "a" * 64


def test_manager_resolution_instance_state_is_synthetic_active() -> None:
    """In 2B the manager does not verify the instance state via the
    driver (that is the 2C+ bridge's job). The instance returned
    is synthetic with state=Active and health_state=Ready; the
    2C+ bridge will call driver.runtime_health to verify."""
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    mgr = RuntimeManager(registry=reg, driver=_StubDriver(), events=RuntimeEventBus())
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
    mgr = RuntimeManager(registry=RuntimeRegistry([]), driver=_StubDriver(), events=RuntimeEventBus())
    assert mgr.resolve("kokoro-base") is None


def test_manager_selection_picks_default_over_priority() -> None:
    d1 = _good_descriptor(runtime_id="kokoro-cpu", priority=200, is_default=False)
    d2 = _good_descriptor(runtime_id="kokoro-cuda", priority=100, is_default=True)
    reg = RuntimeRegistry([d1, d2])
    mgr = RuntimeManager(registry=reg, driver=_StubDriver(), events=RuntimeEventBus())
    res = mgr.resolve("kokoro-base")
    assert res is not None
    # Default wins regardless of priority.
    assert res.descriptor.metadata.id == "kokoro-cuda"


def test_manager_selection_uses_priority_when_no_default() -> None:
    d1 = _good_descriptor(runtime_id="kokoro-cpu", priority=200, is_default=False)
    d2 = _good_descriptor(runtime_id="kokoro-cuda", priority=100, is_default=False)
    reg = RuntimeRegistry([d1, d2])
    mgr = RuntimeManager(registry=reg, driver=_StubDriver(), events=RuntimeEventBus())
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
    mgr = RuntimeManager(registry=reg, driver=_StubDriver(), events=RuntimeEventBus())
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


def test_bridge_in_2a10_still_falls_through_with_manager_wired() -> None:
    """The bridge in 2A.10 (PeakVoxRuntime.generate) is unchanged in
    2B. The runtime-service branch is still a literal ``pass``;
    the bridge falls through to the existing in-process path
    even when the manager is wired AND resolve() returns a
    non-None resolution. The 2C+ branch is the runtime path;
    that branch is added in sub-phase 2C, not 2B."""
    from app.services.runtime import PeakVoxRuntime
    from app.services.model_adapter import ModelAdapter
    from app.models.registry_types import ModelCapabilities, ModelDescriptor

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

    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    mgr = RuntimeManager(registry=reg, driver=_StubDriver(), events=RuntimeEventBus())
    rt.attach_runtime_manager(mgr)

    # Generate; the adapter is the worker. The bridge is a
    # pass-through even though the manager is wired and resolve()
    # returns a non-None resolution.
    duration, logs = asyncio.run(
        rt.generate(
            None, text="hi", model_id="kokoro-base",
            output_path=__import__("pathlib").Path("/tmp/x.wav"),
        )
    )
    assert duration == 1.5
    assert "kokoro-base:hi" in logs[0]
