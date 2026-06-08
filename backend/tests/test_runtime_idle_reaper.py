"""TDD: Phase 3 idle reaper (R7).

The ``RuntimeManager.run_idle_reaper`` method auto-stops any
``Active`` runtime that has been idle longer than its
descriptor's ``spec.lifecycle.idle_timeout``.

Vocabulary
----------

``spec.lifecycle.idle_timeout`` is a closed set:

  - "never"  — autoscaler owns lifecycle (Cloud default)
  - "15m"    — Community Edition default
  - "30m"    — half-hour idle
  - "1h"     — hour idle
  - "6h"     — six hours idle

When the reaper stops a runtime, it emits a
``RuntimeIdleTimeout`` event with the elapsed seconds.

The reaper is the background task started by
``runtime_wiring.start_idle_reaper`` at backend boot. It
wakes up every 60 seconds and calls
``manager.run_idle_reaper()`` once.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.runtime_events import RuntimeEventBus, RuntimeIdleTimeout
from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)
from app.services.runtime_manager import RuntimeManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_descriptor(id_: str = "kokoro-82m", idle_timeout: str = "15m") -> dict:
    return {
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": id_,
            "name": f"{id_} runtime",
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
            "lifecycle": {"idle_timeout": idle_timeout},
        },
    }


def _make_instance(
    runtime_id: str = "kokoro-82m",
    state: RuntimeState = RuntimeState.ACTIVE,
    last_request_at: datetime | None = None,
) -> RuntimeInstance:
    return RuntimeInstance(
        runtime_id=runtime_id,
        state=state,
        host="localhost",
        port=8000,
        image_identity=ImageIdentity(
            repository="peakvox/kokoro-runtime", tag="0.1.0", digest=None
        ),
        started_at=datetime.now(timezone.utc),
        last_health_at=datetime.now(timezone.utc),
        last_request_at=last_request_at,
        health_state=HealthState.READY,
    )


class _MockDriver:
    """A no-op RuntimeDriver. The reaper only calls ``stop_runtime``."""

    def __init__(self) -> None:
        self.stop_calls: list[str] = []

    async def stop_runtime(self, runtime_id: str) -> None:
        self.stop_calls.append(runtime_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_idle_reaper_stops_idle_runtime(tmp_path: Path) -> None:
    """A runtime idle for longer than the timeout is auto-stopped."""
    import json
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    (d / "descriptor.json").write_text(json.dumps(_make_descriptor(idle_timeout="15m")))

    from app.services.runtime_registry import RuntimeRegistryLoader
    registry = RuntimeRegistryLoader().load_from_directory(tmp_path)
    driver = _MockDriver()
    bus = RuntimeEventBus()
    manager = RuntimeManager(registry=registry, driver=driver, events=bus)

    # Inject an Active instance whose last_request_at is 30 minutes ago.
    old = datetime.now(timezone.utc) - timedelta(minutes=30)
    manager._instance_cache["kokoro-82m"] = _make_instance(
        last_request_at=old,
    )

    events_received: list = []
    bus.subscribe(lambda e: events_received.append(e))

    reaped = await manager.run_idle_reaper()
    assert reaped == 1
    assert driver.stop_calls == ["kokoro-82m"]
    assert any(isinstance(e, RuntimeIdleTimeout) for e in events_received)


@pytest.mark.asyncio
async def test_run_idle_reaper_skips_active_runtime_with_no_last_request(
    tmp_path: Path,
) -> None:
    """An Active instance with ``last_request_at = None`` is not reaped.

    The runtime may have been started manually outside the manager
    (e.g. by an operator via docker CLI). Without a recorded
    last_request_at, the reaper has no signal to stop it.
    """
    import json
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    (d / "descriptor.json").write_text(json.dumps(_make_descriptor(idle_timeout="15m")))

    from app.services.runtime_registry import RuntimeRegistryLoader
    registry = RuntimeRegistryLoader().load_from_directory(tmp_path)
    driver = _MockDriver()
    bus = RuntimeEventBus()
    manager = RuntimeManager(registry=registry, driver=driver, events=bus)

    manager._instance_cache["kokoro-82m"] = _make_instance(
        last_request_at=None,
    )

    reaped = await manager.run_idle_reaper()
    assert reaped == 0
    assert driver.stop_calls == []


@pytest.mark.asyncio
async def test_run_idle_reaper_does_not_stop_non_idle_runtime(
    tmp_path: Path,
) -> None:
    """An Active runtime whose last_request_at is recent is not reaped."""
    import json
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    (d / "descriptor.json").write_text(json.dumps(_make_descriptor(idle_timeout="15m")))

    from app.services.runtime_registry import RuntimeRegistryLoader
    registry = RuntimeRegistryLoader().load_from_directory(tmp_path)
    driver = _MockDriver()
    bus = RuntimeEventBus()
    manager = RuntimeManager(registry=registry, driver=driver, events=bus)

    recent = datetime.now(timezone.utc) - timedelta(minutes=5)
    manager._instance_cache["kokoro-82m"] = _make_instance(
        last_request_at=recent,
    )

    reaped = await manager.run_idle_reaper()
    assert reaped == 0
    assert driver.stop_calls == []


@pytest.mark.asyncio
async def test_run_idle_reaper_respects_never_timeout(tmp_path: Path) -> None:
    """A runtime with ``idle_timeout = "never"`` is never reaped,
    even if last_request_at is ancient (Cloud autoscaler owns lifecycle)."""
    import json
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    (d / "descriptor.json").write_text(json.dumps(_make_descriptor(idle_timeout="never")))

    from app.services.runtime_registry import RuntimeRegistryLoader
    registry = RuntimeRegistryLoader().load_from_directory(tmp_path)
    driver = _MockDriver()
    bus = RuntimeEventBus()
    manager = RuntimeManager(registry=registry, driver=driver, events=bus)

    ancient = datetime.now(timezone.utc) - timedelta(days=365)
    manager._instance_cache["kokoro-82m"] = _make_instance(
        last_request_at=ancient,
    )

    reaped = await manager.run_idle_reaper()
    assert reaped == 0
    assert driver.stop_calls == []


@pytest.mark.asyncio
async def test_run_idle_reaper_skips_non_active_states(tmp_path: Path) -> None:
    """A non-Active instance (Installed, Stopped, Failed) is not reaped,
    even if last_request_at is ancient."""
    import json
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    (d / "descriptor.json").write_text(json.dumps(_make_descriptor(idle_timeout="15m")))

    from app.services.runtime_registry import RuntimeRegistryLoader
    registry = RuntimeRegistryLoader().load_from_directory(tmp_path)
    driver = _MockDriver()
    bus = RuntimeEventBus()
    manager = RuntimeManager(registry=registry, driver=driver, events=bus)

    ancient = datetime.now(timezone.utc) - timedelta(days=1)
    for state in (RuntimeState.INSTALLED, RuntimeState.STOPPED, RuntimeState.FAILED):
        manager._instance_cache["kokoro-82m"] = _make_instance(
            state=state, last_request_at=ancient,
        )
        reaped = await manager.run_idle_reaper()
        assert reaped == 0
        assert driver.stop_calls == []


@pytest.mark.asyncio
async def test_idle_timeout_event_carries_elapsed_seconds(tmp_path: Path) -> None:
    """The RuntimeIdleTimeout event reports the elapsed seconds."""
    import json
    d = tmp_path / "kokoro-82m"
    d.mkdir()
    (d / "descriptor.json").write_text(json.dumps(_make_descriptor(idle_timeout="15m")))

    from app.services.runtime_registry import RuntimeRegistryLoader
    registry = RuntimeRegistryLoader().load_from_directory(tmp_path)
    driver = _MockDriver()
    bus = RuntimeEventBus()
    manager = RuntimeManager(registry=registry, driver=driver, events=bus)

    old = datetime.now(timezone.utc) - timedelta(minutes=20)
    manager._instance_cache["kokoro-82m"] = _make_instance(
        last_request_at=old,
    )

    received: list[RuntimeIdleTimeout] = []
    bus.subscribe(lambda e: received.append(e) if isinstance(e, RuntimeIdleTimeout) else None)

    await manager.run_idle_reaper()
    assert len(received) == 1
    event = received[0]
    assert event.runtime_id == "kokoro-82m"
    # ~20 minutes = ~1200 seconds (allow ±5s for test latency).
    assert 1195 <= event.idle_seconds <= 1205
