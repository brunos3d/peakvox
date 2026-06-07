"""TDD: HealthReport and Metrics (2A.3) — runtime observability types.

Phase 2A is infrastructure foundation work. HealthReport carries
liveness + readiness from a runtime probe (ADR-0017 §6.1, §6.2).
Metrics is a forward-safe placeholder; the first driver may
return empty.

These tests assert:
- Liveness and readiness enums are exhaustive.
- last_error is optional and string-shaped.
- checked_at is required and datetime-shaped.
- Metrics accepts an empty payload (Phase 2 first driver may
  return empty).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.runtime_types import HealthReport, Liveness, Metrics, Readiness


def test_health_report_required_fields() -> None:
    now = datetime.now(timezone.utc)
    rep = HealthReport(
        runtime_id="kokoro-cpu",
        liveness=Liveness.ALIVE,
        readiness=Readiness.READY,
        last_error=None,
        checked_at=now,
    )
    assert rep.runtime_id == "kokoro-cpu"
    assert rep.liveness is Liveness.ALIVE
    assert rep.readiness is Readiness.READY
    assert rep.last_error is None
    assert rep.checked_at == now


def test_health_report_last_error_is_optional_string() -> None:
    rep = HealthReport(
        runtime_id="x",
        liveness=Liveness.ALIVE,
        readiness=Readiness.NOT_READY,
        last_error="weights_loading",
        checked_at=datetime.now(timezone.utc),
    )
    assert rep.last_error == "weights_loading"


def test_liveness_enum_has_two_values() -> None:
    assert {s.name for s in Liveness} == {"ALIVE", "DEAD"}


def test_readiness_enum_has_three_values() -> None:
    assert {s.name for s in Readiness} == {"READY", "NOT_READY", "UNKNOWN"}


def test_metrics_accepts_empty_payload() -> None:
    # Forward-safe: a first-version driver may return Metrics() with no
    # counters. The type exists; the body is empty by design.
    m = Metrics()
    assert m is not None


def test_health_report_is_frozen() -> None:
    rep = HealthReport(
        runtime_id="x",
        liveness=Liveness.ALIVE,
        readiness=Readiness.READY,
        last_error=None,
        checked_at=datetime.now(timezone.utc),
    )
    with pytest.raises(Exception):
        rep.readiness = Readiness.NOT_READY  # type: ignore[misc]
