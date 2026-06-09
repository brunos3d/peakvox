"""TDD: RuntimeManager bridge in PeakVoxRuntime.generate.

The bridge connects PeakVoxRuntime to RuntimeManager. Its behavior:

  - When manager is wired AND the runtime is ACTIVE (resolve() non-None):
    → inject runtime_endpoint into adapter kwargs
    → log an observability event (debug)
    → adapter routes to the runtime service

  - When manager is wired but runtime is NOT active (resolve() None):
    → ModelNotActive is raised (the orchestration layer owns lifecycle;
      there is no silent fallback to in-process when the manager is wired)

  - When manager is NOT wired (no runtime subsystem):
    → runtime_endpoint=None is passed to adapter (in-process path)

This reflects the architectural requirement that the RuntimeManager is
the single authority for runtime operational state. When it is wired and
knows about a runtime for a model, that model must be ACTIVE to generate.
There is no silent fallback that would bypass the lifecycle contract.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from app.services.runtime import ModelNotActive, PeakVoxRuntime
from app.services.model_adapter import ModelAdapter
from app.services.runtime_manager import RuntimeManager
from app.services.runtime_registry import RuntimeRegistry
from app.services.runtime_types import RuntimeDescriptor
from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)
from app.services.runtime_events import RuntimeEventBus
from app.models.registry_types import ModelCapabilities, ModelDescriptor


def _good_descriptor(
    runtime_id: str = "kokoro-82m", model_id: str = "kokoro-base"
) -> RuntimeDescriptor:
    return RuntimeDescriptor.model_validate({
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": runtime_id, "name": runtime_id, "description": "",
            "provider": "kokoro", "version": "0.1.0", "edition": ["ce"], "labels": {},
        },
        "spec": {
            "runtime_type": "docker",
            "image": {"repository": "peakvox/kokoro-runtime", "tag": "0.1.0"},
            "service": {"protocol": "http", "port": 8000},
            "capabilities": ["tts"],
            "requirements": {"gpu": "none", "edition": ["ce"]},
            "model_binding": {"model_id": model_id, "is_default": True, "priority": 100},
        },
    })


class _RecordingDriver:
    """A driver that records calls and returns Active instances."""

    def __init__(self) -> None:
        self.instances: dict[str, RuntimeInstance] = {}

    async def install_runtime(self, runtime_id, descriptor):
        inst = RuntimeInstance(
            runtime_id=runtime_id, state=RuntimeState.INSTALLED,
            host="localhost", port=descriptor.spec.service.port,
            image_identity=ImageIdentity(
                repository=descriptor.spec.image.repository,
                tag=descriptor.spec.image.tag, digest=descriptor.spec.image.digest,
            ),
            started_at=None, last_health_at=None, health_state=HealthState.UNKNOWN,
        )
        self.instances[runtime_id] = inst
        return inst

    async def start_runtime(self, runtime_id):
        cur = self.instances.get(runtime_id) or _active_instance(runtime_id)
        inst = RuntimeInstance(
            runtime_id=cur.runtime_id, state=RuntimeState.ACTIVE,
            host=cur.host, port=cur.port, image_identity=cur.image_identity,
            started_at=cur.started_at, last_health_at=cur.last_health_at,
            health_state=HealthState.READY,
        )
        self.instances[runtime_id] = inst
        return inst

    async def update_runtime(self, runtime_id, descriptor):
        return self.instances.get(runtime_id) or _active_instance(runtime_id)

    async def remove_runtime(self, runtime_id):
        self.instances.pop(runtime_id, None)

    async def stop_runtime(self, runtime_id): pass

    async def restart_runtime(self, runtime_id):
        return await self.start_runtime(runtime_id)

    async def runtime_status(self, runtime_id):
        return self.instances.get(runtime_id) or _active_instance(runtime_id)

    async def runtime_logs(self, runtime_id, since=None):
        async def _empty():
            if False:
                yield ""
        return _empty()

    async def runtime_health(self, runtime_id):
        from app.services.runtime_types import HealthReport, Liveness, Readiness
        from datetime import datetime
        return HealthReport(
            runtime_id=runtime_id, liveness=Liveness.ALIVE,
            readiness=Readiness.READY, last_error=None,
            checked_at=datetime(2026, 6, 7, 0, 0, 0),
        )

    async def runtime_metrics(self, runtime_id):
        from app.services.runtime_types import Metrics
        return Metrics()


def _active_instance(runtime_id: str) -> RuntimeInstance:
    return RuntimeInstance(
        runtime_id=runtime_id, state=RuntimeState.ACTIVE,
        host="localhost", port=8000,
        image_identity=ImageIdentity(
            repository="peakvox/kokoro-runtime", tag="0.1.0", digest=None,
        ),
        started_at=__import__("datetime").datetime(2026, 6, 7),
        last_health_at=__import__("datetime").datetime(2026, 6, 7),
        health_state=HealthState.READY,
    )


class _TrackingAdapter(ModelAdapter):
    def __init__(self, descriptor):
        super().__init__(descriptor)
        self.captured_text: str = ""
        self.captured_output_path: object = None
        self.captured_kwargs: dict = {}
    async def install(self): ...
    async def load(self): ...
    def unload(self): ...
    async def health_check(self) -> bool: return True
    async def generate(self, *, text, output_path, **kwargs):
        self.captured_text = text
        self.captured_output_path = output_path
        self.captured_kwargs = kwargs
        return (1.5, [f"{self.model_id}:{text}"])
    async def clone_voice(self, *, db, voice, reference_audio_key): raise NotImplementedError
    async def build_variant(self, *, db, voice): raise NotImplementedError


@pytest.fixture
def runtime() -> PeakVoxRuntime:
    rt = PeakVoxRuntime()
    adapter = _TrackingAdapter(
        ModelDescriptor(
            id="kokoro-base", name="Kokoro Base", description="d",
            provider="kokoro", supported_tags=[],
            capabilities=ModelCapabilities(supports_tts=True),
        )
    )
    rt.register_adapter(adapter)
    return rt


def _wire_manager(rt: PeakVoxRuntime, *, install: bool, start: bool) -> RuntimeManager:
    """Attach a manager with the given install/start state."""
    desc = _good_descriptor()
    reg = RuntimeRegistry([desc])
    driver = _RecordingDriver()
    mgr = RuntimeManager(registry=reg, driver=driver, events=RuntimeEventBus())
    if install:
        asyncio.run(mgr.install("kokoro-82m"))
    if start:
        asyncio.run(mgr.start("kokoro-82m"))
    rt.attach_runtime_manager(mgr)
    return mgr


# ===== Bridge behavior: active runtime =====


def test_bridge_injects_endpoint_when_runtime_is_active(
    runtime: PeakVoxRuntime, caplog
) -> None:
    """When the manager is wired and the runtime is ACTIVE, the bridge
    injects runtime_endpoint into the adapter kwargs and logs an
    observability event."""
    _wire_manager(runtime, install=True, start=True)
    with caplog.at_level(logging.DEBUG, logger="app.services.runtime"):
        duration, _ = asyncio.run(
            runtime.generate(
                None, text="hi", model_id="kokoro-base",
                output_path=Path("/tmp/x.wav"),
            )
        )
    assert duration == 1.5
    # Bridge logs an observability event with the runtime id and endpoint.
    assert any(
        "kokoro-82m" in r.message
        for r in caplog.records
    ), f"Expected routing log with kokoro-82m; got: {[r.message for r in caplog.records]}"
    # Adapter received runtime_endpoint.
    adapter = runtime.get_adapter("kokoro-base")
    assert adapter.captured_kwargs.get("runtime_endpoint") == "http://localhost:8000"


def test_bridge_passes_endpoint_to_adapter_kwargs(runtime: PeakVoxRuntime) -> None:
    """When the manager is wired and the runtime is ACTIVE, the adapter
    receives runtime_endpoint in its kwargs."""
    _wire_manager(runtime, install=True, start=True)
    asyncio.run(
        runtime.generate(
            None, text="hi", model_id="kokoro-base",
            output_path=Path("/tmp/x.wav"),
        )
    )
    adapter = runtime.get_adapter("kokoro-base")
    assert "runtime_endpoint" in adapter.captured_kwargs
    assert adapter.captured_kwargs["runtime_endpoint"] == "http://localhost:8000"
    assert adapter.captured_text == "hi"
    assert adapter.captured_output_path == Path("/tmp/x.wav")


# ===== Bridge behavior: manager wired, runtime not active =====


def test_bridge_raises_model_not_active_when_runtime_not_started(
    runtime: PeakVoxRuntime,
) -> None:
    """When the manager is wired and knows about a runtime for this model
    but the runtime is NOT started, ModelNotActive is raised.

    There is no silent fallback to in-process when the orchestration
    layer is wired. The user must start the runtime through the UI."""
    _wire_manager(runtime, install=False, start=False)
    with pytest.raises(ModelNotActive) as excinfo:
        asyncio.run(
            runtime.generate(
                None, text="hi", model_id="kokoro-base",
                output_path=Path("/tmp/x.wav"),
            )
        )
    assert excinfo.value.model_id == "kokoro-base"


def test_bridge_raises_model_not_active_when_installed_but_not_started(
    runtime: PeakVoxRuntime,
) -> None:
    """Install without start → ModelNotActive. The runtime is installed
    (image pulled) but not running; inference must be blocked."""
    _wire_manager(runtime, install=True, start=False)
    with pytest.raises(ModelNotActive):
        asyncio.run(
            runtime.generate(
                None, text="hi", model_id="kokoro-base",
                output_path=Path("/tmp/x.wav"),
            )
        )


# ===== Bridge behavior: manager not wired =====


def test_bridge_passes_none_endpoint_when_manager_not_wired(
    runtime: PeakVoxRuntime, caplog
) -> None:
    """When no manager is attached, runtime_endpoint=None is injected
    into the adapter kwargs (in-process path)."""
    with caplog.at_level(logging.DEBUG, logger="app.services.runtime"):
        asyncio.run(
            runtime.generate(
                None, text="hi", model_id="kokoro-base",
                output_path=Path("/tmp/x.wav"),
            )
        )
    adapter = runtime.get_adapter("kokoro-base")
    assert adapter.captured_kwargs.get("runtime_endpoint") is None
    assert not any("routing" in r.message for r in caplog.records)
