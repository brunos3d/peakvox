"""Voice Variant Build Lifecycle — the status vocabulary and transitions (ADR-0008).

A VoiceVariant is a first-class *buildable* runtime asset, not passive metadata. Its
``status`` column moves through five states; the Runtime owns the transitions and dispatches
builds to adapters. This module is the single source of truth for the vocabulary and the legal
state machine — pure logic, no I/O, so both the Runtime and the migration runner can share it.

ADR-0008 supersedes ADR-0006's lifecycle status values: ``processing → building`` and
``stale → deprecated``; ``ready``/``failed`` are unchanged; ``pending`` is new.
"""

from __future__ import annotations


class VariantStatus:
    """The five canonical variant lifecycle states (ADR-0008)."""

    PENDING = "pending"      # record exists; no artifact built yet
    BUILDING = "building"    # build in progress (async job)
    READY = "ready"          # artifact exists and is usable for inference
    FAILED = "failed"        # build failed; artifact partial or absent
    DEPRECATED = "deprecated"  # artifact exists but should not be used; rebuild/remove


VARIANT_STATES: frozenset[str] = frozenset(
    {
        VariantStatus.PENDING,
        VariantStatus.BUILDING,
        VariantStatus.READY,
        VariantStatus.FAILED,
        VariantStatus.DEPRECATED,
    }
)

# Only a `ready` variant can serve inference (ADR-0008 §Voice Variant States).
_GENERABLE: frozenset[str] = frozenset({VariantStatus.READY})

# Legal transitions (ADR-0008 §Transition rules). The build pipeline is the only path to
# `ready`; `ready` is never reached directly from `pending`/`failed`/`deprecated`.
_TRANSITIONS: dict[str, frozenset[str]] = {
    VariantStatus.PENDING: frozenset({VariantStatus.BUILDING}),
    VariantStatus.BUILDING: frozenset({VariantStatus.READY, VariantStatus.FAILED}),
    VariantStatus.READY: frozenset({VariantStatus.BUILDING, VariantStatus.DEPRECATED}),
    VariantStatus.FAILED: frozenset({VariantStatus.BUILDING}),
    VariantStatus.DEPRECATED: frozenset({VariantStatus.BUILDING}),
}

# ADR-0006 → ADR-0008 status remap. Values already in the new vocabulary pass through.
_LEGACY_MAP: dict[str, str] = {
    "processing": VariantStatus.BUILDING,
    "stale": VariantStatus.DEPRECATED,
}


def can_generate(status: str) -> bool:
    """True only when the variant is ``ready`` (the sole inference-eligible state)."""
    return status in _GENERABLE


def can_transition(src: str, dst: str) -> bool:
    """True if ``src → dst`` is a legal lifecycle transition."""
    return dst in _TRANSITIONS.get(src, frozenset())


def validate_transition(src: str, dst: str) -> None:
    """Raise ``ValueError`` if ``src → dst`` is not a legal transition."""
    if not can_transition(src, dst):
        raise ValueError(f"Illegal variant transition: {src!r} → {dst!r}")


def map_legacy_status(status: str) -> str:
    """Map an ADR-0006-era status value onto the ADR-0008 vocabulary (idempotent)."""
    return _LEGACY_MAP.get(status, status)
