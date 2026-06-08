"""RuntimeEventBus (Phase 2A, 2A.7).

Per ADR-0017 §3.6, the manager emits structured events for every
state transition. Events are frozen dataclasses with
``runtime_id``, ``timestamp``, and event-specific fields.

For Phase 2A, the bus is an in-process pub/sub: a ``publish``
operation and a list of subscribers. A future ADR may adapt the
bus to a project-wide structured event channel
(``app.core.events``); the ``RuntimeManager`` does not depend on
any particular bus implementation, only on the ``publish`` /
``subscribe`` surface defined here.

Phase 2A is infrastructure foundation work. No runtime activation,
no Docker integration, no Runtime Service communication.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Protocol

_logger = logging.getLogger(__name__)


# ---- Event payloads (ADR-0017 §3.6) ---------------------------------------------

@dataclass(frozen=True)
class RuntimeEvent:
    """Base for all runtime events. Concrete events are below."""

    runtime_id: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class RuntimeInstallRequested(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeInstallCompleted(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeInstallFailed(RuntimeEvent):
    error: str = ""


@dataclass(frozen=True)
class RuntimeUpdateRequested(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeUpdateCompleted(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeUpdateFailed(RuntimeEvent):
    error: str = ""


@dataclass(frozen=True)
class RuntimeStartRequested(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeStartCompleted(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeStartFailed(RuntimeEvent):
    error: str = ""


@dataclass(frozen=True)
class RuntimeStopRequested(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeStopCompleted(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeRemoveRequested(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeRemoveCompleted(RuntimeEvent):
    pass


@dataclass(frozen=True)
class RuntimeHealthChanged(RuntimeEvent):
    new_state: str = ""  # "ready" | "not_ready" | "unknown"


@dataclass(frozen=True)
class RuntimeDiscovered(RuntimeEvent):
    descriptor_count: int = 0


@dataclass(frozen=True)
class RuntimeIdleTimeout(RuntimeEvent):
    """Emitted by the idle reaper (R7) when an Active runtime is
    auto-stopped after exceeding its ``idle_timeout``."""

    idle_seconds: float = 0.0


# ---- Bus -----------------------------------------------------------------------

class _Subscriber(Protocol):
    def __call__(self, event: RuntimeEvent) -> None: ...


class RuntimeEventBus:
    """In-process pub/sub for runtime events (ADR-0017 §3.6).

    Synchronous; subscribers are called in publish order. A subscriber
    that raises is logged and skipped — other subscribers still
    receive the event. The bus is read-only from the subscriber's
    perspective; subscribers cannot mutate the channel.
    """

    def __init__(self) -> None:
        self._subscribers: List[_Subscriber] = []

    def subscribe(self, subscriber: _Subscriber) -> None:
        self._subscribers.append(subscriber)

    def publish(self, event: RuntimeEvent) -> None:
        for sub in list(self._subscribers):
            try:
                sub(event)
            except Exception:  # subscriber-raised; do not break the channel
                _logger.exception(
                    "runtime event subscriber raised; event=%r", event
                )

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
