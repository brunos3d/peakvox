"""TDD: RuntimeEventBus (2A.7).

Per ADR-0017 §3.6, the manager emits structured events for every
state transition. Events are frozen dataclasses with
``runtime_id``, ``timestamp``, and event-specific fields.

For Phase 2A, the bus is an in-process pub/sub with a synchronous
``publish`` and a list of subscribers. A future ADR adapts the
bus to the project's structured event channel
(``app.core.events``) if/when one exists; for now, the
RuntimeEventBus is self-contained.

These tests assert:
- The bus exposes ``publish`` and ``subscribe``.
- Subscribers receive published events in publish order.
- A subscriber that raises does not block other subscribers.
- The bus carries the canonical event types from ADR-0017 §3.6.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from app.services.runtime_events import (
    RuntimeEventBus,
    RuntimeHealthChanged,
    RuntimeInstallCompleted,
    RuntimeInstallFailed,
    RuntimeInstallRequested,
    RuntimeStartCompleted,
    RuntimeStartFailed,
    RuntimeStartRequested,
    RuntimeStopCompleted,
    RuntimeStopRequested,
)


def test_bus_publishes_to_subscribers() -> None:
    bus = RuntimeEventBus()
    received: List = []
    bus.subscribe(received.append)
    evt = RuntimeInstallRequested(runtime_id="kokoro-cpu")
    bus.publish(evt)
    assert received == [evt]


def test_multiple_subscribers_all_receive() -> None:
    bus = RuntimeEventBus()
    a: List = []
    b: List = []
    bus.subscribe(a.append)
    bus.subscribe(b.append)
    bus.publish(RuntimeStartRequested(runtime_id="kokoro-cpu"))
    assert a and b
    assert a == b


def test_subscribers_called_in_publish_order() -> None:
    bus = RuntimeEventBus()
    received: List[str] = []
    bus.subscribe(lambda e: received.append("a"))
    bus.subscribe(lambda e: received.append("b"))
    bus.subscribe(lambda e: received.append("c"))
    bus.publish(RuntimeInstallRequested(runtime_id="kokoro-cpu"))
    assert received == ["a", "b", "c"]


def test_subscriber_exception_does_not_block_others() -> None:
    bus = RuntimeEventBus()
    received: List = []

    def bad(e):
        raise RuntimeError("boom")

    bus.subscribe(bad)
    bus.subscribe(received.append)
    # The bus must continue to call the second subscriber even when
    # the first raises.
    bus.publish(RuntimeInstallRequested(runtime_id="kokoro-cpu"))
    assert len(received) == 1


def test_event_payloads_carry_runtime_id_and_timestamp() -> None:
    before = datetime.now(timezone.utc)
    evt = RuntimeStartRequested(runtime_id="kokoro-cpu")
    after = datetime.now(timezone.utc)
    assert evt.runtime_id == "kokoro-cpu"
    assert before <= evt.timestamp <= after


def test_canonical_event_types_exist() -> None:
    # The full ADR-0017 §3.6 event vocabulary; Phase 2A only uses
    # a subset (install + start + stop + health) but the types
    # exist for future use.
    assert RuntimeInstallRequested is not None
    assert RuntimeInstallCompleted is not None
    assert RuntimeInstallFailed is not None
    assert RuntimeStartRequested is not None
    assert RuntimeStartCompleted is not None
    assert RuntimeStartFailed is not None
    assert RuntimeStopRequested is not None
    assert RuntimeStopCompleted is not None
    assert RuntimeHealthChanged is not None


def test_failed_events_carry_error_string() -> None:
    evt = RuntimeInstallFailed(runtime_id="kokoro-cpu", error="registry 404")
    assert evt.runtime_id == "kokoro-cpu"
    assert evt.error == "registry 404"


def test_health_changed_carries_new_state() -> None:
    evt = RuntimeHealthChanged(runtime_id="kokoro-cpu", new_state="ready")
    assert evt.runtime_id == "kokoro-cpu"
    assert evt.new_state == "ready"
