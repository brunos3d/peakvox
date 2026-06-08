"""Runtime operational state (Phase 2A, 2A.2 — RuntimeInstance).

Per ADR-0017 §4.2:

    RuntimeInstance:
        runtime_id        str
        state             RuntimeState enum
        host              str
        port              int
        image_identity    ImageIdentity (frozen)
        started_at        datetime | None
        last_health_at    datetime | None
        health_state      HealthState enum

Phase 2A is infrastructure foundation work. This module is dependency-
light (no torch, no Docker SDK, no model frameworks). It is owned
exclusively by the Runtime Manager.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class RuntimeState(Enum):
    """Operational state of a runtime instance (ADR-0017 §4.2)."""

    INSTALLED = "installed"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    REMOVED = "removed"


class HealthState(Enum):
    """Health of a runtime instance (ADR-0017 §4.2 / §6.2).

    Distinct from ``Readiness`` in runtime_types.HealthReport:
    ``HealthState`` is the cached view held on ``RuntimeInstance``;
    ``Readiness`` is the value returned by the live probe.
    """

    READY = "ready"
    NOT_READY = "not_ready"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ImageIdentity:
    """Immutable image identity (repository + tag + optional digest).

    Pinned per ADR-0017 §1.4: ``(repository, tag, digest)`` is the
    immutable pin. Digest is optional; when present it overrides
    tag resolution at the substrate.
    """

    repository: str
    tag: str
    digest: Optional[str]


@dataclass(frozen=True)
class RuntimeInstance:
    """In-memory operational state for one runtime.

    Owned by the :class:`RuntimeManager`. Never persisted in 2A
    (persistence is OPEN_DECISIONS Decision 12). The class is frozen
    because instances are passed by reference across the
    manager/driver boundary; mutation is a state transition, not a
    field write — the manager replaces the cached instance.
    """

    runtime_id: str
    state: RuntimeState
    host: str
    port: int
    image_identity: ImageIdentity
    started_at: Optional[datetime]
    last_health_at: Optional[datetime]
    health_state: HealthState
    last_request_at: Optional[datetime] = None

    def with_last_request_at(self, when: datetime) -> "RuntimeInstance":
        """Return a new instance with ``last_request_at`` set to ``when``.

        The dataclass is frozen; mutation is a state transition.
        Used by the manager to record the most recent ``resolve()``
        call without mutating the cached instance in place.
        """
        from dataclasses import replace
        return replace(self, last_request_at=when)
