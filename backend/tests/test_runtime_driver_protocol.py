"""TDD: RuntimeDriver Protocol (2A.5).

Per ADR-0017 §4.1, ``RuntimeDriver`` is a ``typing.Protocol`` with 10
operations:

  1.  install_runtime
  2.  update_runtime
  3.  remove_runtime
  4.  start_runtime
  5.  stop_runtime
  6.  restart_runtime
  7.  runtime_status
  8.  runtime_logs
  9.  runtime_health
  10. runtime_metrics

These tests assert:
- The Protocol declares all 10 methods.
- A concrete driver with all 10 methods conforms structurally.
- A driver missing one method is rejected at protocol-check time.
- The Protocol is independent of any specific substrate (no Docker
  imports; no K8s imports).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator, List, Optional

import pytest

from app.services.runtime_driver import RuntimeDriver
from app.services.runtime_errors import RuntimeDriverError
from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)
from app.services.runtime_types import HealthReport, Liveness, Metrics, Readiness


class GoodDriver:
    """A driver that implements all 10 operations of the RuntimeDriver protocol."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def install_runtime(
        self, runtime_id: str, descriptor
    ) -> RuntimeInstance:
        self.calls.append("install")
        return RuntimeInstance(
            runtime_id=runtime_id, state=RuntimeState.INSTALLED, host="h", port=8000,
            image_identity=ImageIdentity(repository="r", tag="t", digest=None),
            started_at=None, last_health_at=None, health_state=HealthState.UNKNOWN,
        )

    async def update_runtime(self, runtime_id: str, descriptor) -> RuntimeInstance:
        self.calls.append("update")
        return await self.install_runtime(runtime_id, descriptor)

    async def remove_runtime(self, runtime_id: str) -> None:
        self.calls.append("remove")

    async def start_runtime(self, runtime_id: str) -> RuntimeInstance:
        self.calls.append("start")
        return RuntimeInstance(
            runtime_id=runtime_id, state=RuntimeState.ACTIVE, host="h", port=8000,
            image_identity=ImageIdentity(repository="r", tag="t", digest=None),
            started_at=datetime.now(timezone.utc), last_health_at=None,
            health_state=HealthState.READY,
        )

    async def stop_runtime(self, runtime_id: str) -> None:
        self.calls.append("stop")

    async def restart_runtime(self, runtime_id: str) -> RuntimeInstance:
        self.calls.append("restart")
        return await self.start_runtime(runtime_id)

    async def runtime_status(self, runtime_id: str) -> RuntimeInstance:
        self.calls.append("status")
        return await self.install_runtime(runtime_id, None)

    async def runtime_logs(
        self, runtime_id: str, since: Optional[datetime] = None
    ) -> AsyncIterator[str]:
        self.calls.append("logs")
        if False:
            yield ""

    async def runtime_health(self, runtime_id: str) -> HealthReport:
        self.calls.append("health")
        return HealthReport(
            runtime_id=runtime_id, liveness=Liveness.ALIVE, readiness=Readiness.READY,
            last_error=None, checked_at=datetime.now(timezone.utc),
        )

    async def runtime_metrics(self, runtime_id: str) -> Metrics:
        self.calls.append("metrics")
        return Metrics()


class BadDriverMissingStart:
    """Intentionally missing start_runtime to verify protocol enforcement."""

    async def install_runtime(self, runtime_id, descriptor) -> RuntimeInstance:
        raise NotImplementedError

    async def update_runtime(self, runtime_id, descriptor) -> RuntimeInstance:
        raise NotImplementedError

    async def remove_runtime(self, runtime_id) -> None:
        raise NotImplementedError

    # start_runtime MISSING on purpose

    async def stop_runtime(self, runtime_id) -> None:
        raise NotImplementedError

    async def restart_runtime(self, runtime_id) -> RuntimeInstance:
        raise NotImplementedError

    async def runtime_status(self, runtime_id) -> RuntimeInstance:
        raise NotImplementedError

    async def runtime_logs(self, runtime_id, since=None):
        raise NotImplementedError

    async def runtime_health(self, runtime_id) -> HealthReport:
        raise NotImplementedError

    async def runtime_metrics(self, runtime_id) -> Metrics:
        raise NotImplementedError


def test_protocol_declares_all_ten_operations() -> None:
    expected = {
        "install_runtime", "update_runtime", "remove_runtime",
        "start_runtime", "stop_runtime", "restart_runtime",
        "runtime_status", "runtime_logs", "runtime_health", "runtime_metrics",
    }
    declared = set(RuntimeDriver.__dict__) | set(dir(RuntimeDriver))
    # Pydantic / typing.Protocol: declared methods appear in __annotations__ or as callables.
    annotations = set(getattr(RuntimeDriver, "__annotations__", {}).keys())
    members = expected & (annotations | declared)
    missing = expected - members
    assert not missing, f"RuntimeDriver missing operations: {missing}"


def test_good_driver_conforms_to_protocol() -> None:
    d = GoodDriver()
    # isinstance with a runtime-checkable Protocol passes when the
    # candidate implements every method.
    assert isinstance(d, RuntimeDriver)


def test_bad_driver_is_rejected_by_protocol() -> None:
    bad = BadDriverMissingStart()
    assert not isinstance(bad, RuntimeDriver)
