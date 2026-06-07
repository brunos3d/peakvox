"""TDD: RuntimeInstance (2A.2) — frozen operational state for a runtime.

Phase 2A is infrastructure foundation work. RuntimeInstance is the
in-memory state of a runtime (state, host, port, image identity,
health). It is owned by the Runtime Manager; the manager is the
only writer.

These tests assert:
- Field types are enforced.
- image_identity is a frozen nested object.
- State enum values are exhaustive.
- Two RuntimeInstances with the same fields compare equal.
"""

from __future__ import annotations

import pytest

from app.services.runtime_instance import (
    HealthState,
    ImageIdentity,
    RuntimeInstance,
    RuntimeState,
)


def test_runtime_instance_carries_canonical_fields() -> None:
    inst = RuntimeInstance(
        runtime_id="kokoro-cpu",
        state=RuntimeState.ACTIVE,
        host="peakvox-kokoro",
        port=8000,
        image_identity=ImageIdentity(
            repository="peakvox/kokoro-runtime",
            tag="1.4.2",
            digest="sha256:" + "a" * 64,
        ),
        started_at=None,
        last_health_at=None,
        health_state=HealthState.READY,
    )
    assert inst.runtime_id == "kokoro-cpu"
    assert inst.state is RuntimeState.ACTIVE
    assert inst.host == "peakvox-kokoro"
    assert inst.port == 8000
    assert inst.image_identity.digest.startswith("sha256:")


def test_image_identity_is_frozen() -> None:
    identity = ImageIdentity(
        repository="peakvox/f5-runtime",
        tag="1.4.2",
        digest="sha256:" + "b" * 64,
    )
    with pytest.raises(Exception):
        identity.repository = "evil/mutated"  # type: ignore[misc]


def test_runtime_instance_is_frozen() -> None:
    inst = RuntimeInstance(
        runtime_id="x",
        state=RuntimeState.INSTALLED,
        host="h",
        port=8000,
        image_identity=ImageIdentity(repository="r", tag="t", digest=None),
        started_at=None,
        last_health_at=None,
        health_state=HealthState.UNKNOWN,
    )
    with pytest.raises(Exception):
        inst.state = RuntimeState.ACTIVE  # type: ignore[misc]


def test_two_instances_with_same_fields_compare_equal() -> None:
    identity = ImageIdentity(repository="r", tag="t", digest=None)
    a = RuntimeInstance(
        runtime_id="x", state=RuntimeState.ACTIVE, host="h", port=8000,
        image_identity=identity, started_at=None, last_health_at=None,
        health_state=HealthState.READY,
    )
    b = RuntimeInstance(
        runtime_id="x", state=RuntimeState.ACTIVE, host="h", port=8000,
        image_identity=identity, started_at=None, last_health_at=None,
        health_state=HealthState.READY,
    )
    assert a == b


def test_state_enum_covers_seven_values() -> None:
    # Per ADR-0017 §4.2 RuntimeInstance.state.
    assert {s.name for s in RuntimeState} == {
        "INSTALLED", "STARTING", "ACTIVE", "STOPPING", "STOPPED", "FAILED", "REMOVED",
    }


def test_health_state_enum_covers_three_values() -> None:
    # Per ADR-0017 §4.2 HealthReport fields.
    assert {s.name for s in HealthState} == {"READY", "NOT_READY", "UNKNOWN"}


def test_image_identity_digest_is_optional() -> None:
    identity = ImageIdentity(repository="r", tag="t", digest=None)
    assert identity.digest is None
