"""TDD: 2D bridge activation in PeakVoxRuntime.generate (Milestone 17).

The 2A bridge block in ``runtime.py`` is a literal ``pass`` when
the resolution is non-None. In 2D the bridge is ACTIVATED:

  - When the manager is wired AND the resolution is non-None:
    the bridge records an observability event (a structured
    log + an in-process metric) confirming the runtime-service
    path is reachable. The adapter's 2C.2 dispatch handles
    the actual routing (KokoroAdapter dispatches on
    KOKORO_RUNTIME_URL).

  - When the manager is wired but the resolution is None:
    the bridge falls through to the in-process path (existing
    behavior).

  - When the manager is not wired: the in-process path is
    taken (existing behavior).

The activation does NOT change the adapter contract, does NOT
change the in-process path, and does NOT change the bridge's
position in the call chain. The activation is a
documentation + observability change at the verification
point between active-artifact resolution and the adapter
call.

Test surface (TDD):

  - The bridge records an observability event when the
    resolution is non-None.
  - The bridge does NOT record an observability event when
    the resolution is None.
  - The bridge does NOT change the adapter's kwargs.
  - The in-process path is preserved when the manager is not
    wired.
  - The in-process path is preserved when the manager is
    wired but the runtime is not installed.
  - The runtime-service path is the adapter's responsibility
    (KokoroAdapter's 2C.2 dispatch on KOKORO_RUNTIME_URL).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List

import pytest

from app.services.runtime import PeakVoxRuntime
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
        cur = self.instances.get(runtime_id) or _active(runtime_id)
        inst = RuntimeInstance(
            runtime_id=cur.runtime_id, state=RuntimeState.ACTIVE,
            host=cur.host, port=cur.port, image_identity=cur.image_identity,
            started_at=cur.started_at, last_health_at=cur.last_health_at,
            health_state=HealthState.READY,
        )
        self.instances[runtime_id] = inst
        return inst

    async def update_runtime(self, runtime_id, descriptor):
        return self.instances.get(runtime_id) or _active(runtime_id)

    async def remove_runtime(self, runtime_id):
        self.instances.pop(runtime_id, None)

    async def stop_runtime(self, runtime_id): pass

    async def restart_runtime(self, runtime_id):
        return await self.start_runtime(runtime_id)

    async def runtime_status(self, runtime_id):
        return self.instances.get(runtime_id) or _active(runtime_id)

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


def _active(runtime_id: str) -> RuntimeInstance:
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


# ===== 2D bridge activation =====


def test_bridge_records_observability_when_resolution_is_non_none(
    runtime: PeakVoxRuntime, caplog
) -> None:
    """When the manager is wired and the resolution is non-None
    (runtime is installed + started), the bridge records an
    observability event confirming the runtime-service path
    is reachable."""
    _wire_manager(runtime, install=True, start=True)
    with caplog.at_level(logging.DEBUG, logger="app.services.runtime"):
        duration, _ = asyncio.run(
            runtime.generate(
                None, text="hi", model_id="kokoro-base",
                output_path=Path("/tmp/x.wav"),
            )
        )
    # The bridge activation logs a debug message about the
    # runtime-service path. The message mentions "runtime-service"
    # and the runtime id.
    assert any(
        "runtime-service" in r.message and "kokoro-82m" in r.message
        for r in caplog.records
    ), (
        f"Expected runtime-service observability log; got: "
        f"{[r.message for r in caplog.records]}"
    )


def test_bridge_does_not_record_observability_when_resolution_is_none(
    runtime: PeakVoxRuntime, caplog
) -> None:
    """When the manager is wired but the resolution is None
    (runtime is not installed), the bridge does NOT record
    the observability event. The in-process path is taken."""
    _wire_manager(runtime, install=False, start=False)
    with caplog.at_level(logging.DEBUG, logger="app.services.runtime"):
        duration, _ = asyncio.run(
            runtime.generate(
                None, text="hi", model_id="kokoro-base",
                output_path=Path("/tmp/x.wav"),
            )
        )
    # No runtime-service observability log when the resolution
    # is None.
    assert not any(
        "runtime-service" in r.message and "kokoro-82m" in r.message
        for r in caplog.records
    ), "Bridge must not log runtime-service path when resolution is None"


def test_bridge_does_not_record_observability_when_manager_not_wired(
    runtime: PeakVoxRuntime, caplog
) -> None:
    """When the manager is not wired, the bridge does NOT
    record the observability event. The in-process path is
    taken (existing behavior)."""
    # No manager attached.
    with caplog.at_level(logging.DEBUG, logger="app.services.runtime"):
        duration, _ = asyncio.run(
            runtime.generate(
                None, text="hi", model_id="kokoro-base",
                output_path=Path("/tmp/x.wav"),
            )
        )
    assert not any("runtime-service" in r.message for r in caplog.records)


def test_bridge_does_not_perturb_adapter_kwargs(
    runtime: PeakVoxRuntime,
) -> None:
    """The bridge activation does NOT change the adapter's
    kwargs. The adapter receives the same kwargs whether the
    bridge is activated or not."""
    # Without manager.
    asyncio.run(
        runtime.generate(
            None, text="hi", model_id="kokoro-base",
            output_path=Path("/tmp/x.wav"),
        )
    )
    adapter_no_mgr = runtime.get_adapter("kokoro-base")
    text_no_mgr = adapter_no_mgr.captured_text
    path_no_mgr = adapter_no_mgr.captured_output_path
    kwargs_no_mgr = dict(adapter_no_mgr.captured_kwargs)

    # With manager + installed + started runtime.
    _wire_manager(runtime, install=True, start=True)
    asyncio.run(
        runtime.generate(
            None, text="hi", model_id="kokoro-base",
            output_path=Path("/tmp/x.wav"),
        )
    )
    text_with_mgr = adapter_no_mgr.captured_text
    path_with_mgr = adapter_no_mgr.captured_output_path
    kwargs_with_mgr = dict(adapter_no_mgr.captured_kwargs)

    # The text, output_path, and kwargs must be identical
    # (the bridge activation does not perturb them).
    assert text_no_mgr == text_with_mgr
    assert path_no_mgr == path_with_mgr
    assert kwargs_no_mgr == kwargs_with_mgr


def test_bridge_does_not_perturb_adapter_kwargs_when_resolution_is_none(
    runtime: PeakVoxRuntime,
) -> None:
    """The bridge activation does NOT change the adapter's
    kwargs even when the resolution is None. The in-process
    path is taken unchanged."""
    _wire_manager(runtime, install=False, start=False)
    adapter = runtime.get_adapter("kokoro-base")
    asyncio.run(
        runtime.generate(
            None, text="hi", model_id="kokoro-base",
            output_path=Path("/tmp/x.wav"),
        )
    )
    # The text and output_path are passed through unchanged.
    assert adapter.captured_text == "hi"
    assert adapter.captured_output_path == Path("/tmp/x.wav")
    # No endpoint kwarg is added (the bridge does not inject
    # a runtime endpoint into the adapter's kwargs).
    assert "endpoint" not in adapter.captured_kwargs
    assert "runtime_endpoint" not in adapter.captured_kwargs
    assert "runtime_descriptor" not in adapter.captured_kwargs
