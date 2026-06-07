"""RuntimeDriver Protocol (Phase 2A, 2A.5).

Per ADR-0017 §4.1, ``RuntimeDriver`` is a ``typing.Protocol`` with 10
operations. The Protocol is structural (``runtime_checkable``) so
concrete drivers do not need to inherit; they only need to expose
the methods with the right signatures.

The Protocol is dependency-light: it does not import Docker, K8s,
Podman, or any substrate-specific library. The first concrete
driver (``DockerRuntimeDriver``) is introduced in sub-phase 2B.

Phase 2A is infrastructure foundation work.
"""

from __future__ import annotations

from datetime import datetime
from typing import AsyncIterator, Optional, Protocol, runtime_checkable

from app.services.runtime_errors import RuntimeDriverError  # noqa: F401  (re-exported)
from app.services.runtime_instance import RuntimeInstance
from app.services.runtime_types import HealthReport, Metrics  # noqa: F401  (re-exported)
from app.services.runtime_types import RuntimeDescriptor  # noqa: F401  (re-exported)


__all__ = [
    "RuntimeDriver",
    "RuntimeDriverError",
    "RuntimeInstance",
    "RuntimeDescriptor",
    "HealthReport",
    "Metrics",
]


@runtime_checkable
class RuntimeDriver(Protocol):
    """The substrate-neutral driver contract (ADR-0017 §4.2).

    Ten operations; the manager depends only on this interface.
    """

    async def install_runtime(
        self, runtime_id: str, descriptor: RuntimeDescriptor
    ) -> RuntimeInstance: ...

    async def update_runtime(
        self, runtime_id: str, descriptor: RuntimeDescriptor
    ) -> RuntimeInstance: ...

    async def remove_runtime(self, runtime_id: str) -> None: ...

    async def start_runtime(self, runtime_id: str) -> RuntimeInstance: ...

    async def stop_runtime(self, runtime_id: str) -> None: ...

    async def restart_runtime(self, runtime_id: str) -> RuntimeInstance: ...

    async def runtime_status(self, runtime_id: str) -> RuntimeInstance: ...

    async def runtime_logs(
        self, runtime_id: str, since: Optional[datetime] = None
    ) -> AsyncIterator[str]: ...

    async def runtime_health(self, runtime_id: str) -> HealthReport: ...

    async def runtime_metrics(self, runtime_id: str) -> Metrics: ...
