"""ADR-0008 — Voice Variant Build Lifecycle status vocabulary + transitions."""

import pytest

from app.services.variant_lifecycle import (
    VARIANT_STATES,
    VariantStatus,
    can_generate,
    can_transition,
    map_legacy_status,
    validate_transition,
)


def test_five_canonical_states():
    assert VARIANT_STATES == {
        "pending",
        "building",
        "ready",
        "failed",
        "deprecated",
    }


def test_only_ready_can_generate():
    assert can_generate(VariantStatus.READY) is True
    for state in VARIANT_STATES - {"ready"}:
        assert can_generate(state) is False


@pytest.mark.parametrize(
    "src,dst",
    [
        ("pending", "building"),
        ("building", "ready"),
        ("building", "failed"),
        ("ready", "building"),       # rebuild
        ("ready", "deprecated"),
        ("deprecated", "building"),  # rebuild after deprecation
        ("failed", "building"),      # retry
    ],
)
def test_allowed_transitions(src, dst):
    assert can_transition(src, dst) is True


@pytest.mark.parametrize(
    "src,dst",
    [
        ("pending", "ready"),        # must build first
        ("ready", "failed"),         # ready never goes straight to failed
        ("deprecated", "ready"),     # must rebuild
        ("failed", "ready"),         # must rebuild
        ("ready", "pending"),
    ],
)
def test_disallowed_transitions(src, dst):
    assert can_transition(src, dst) is False
    with pytest.raises(ValueError):
        validate_transition(src, dst)


def test_legacy_adr0006_status_mapping():
    assert map_legacy_status("processing") == "building"
    assert map_legacy_status("stale") == "deprecated"
    assert map_legacy_status("ready") == "ready"
    assert map_legacy_status("failed") == "failed"
    # Unknown / already-current values pass through untouched.
    assert map_legacy_status("pending") == "pending"
    assert map_legacy_status("building") == "building"
