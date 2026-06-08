"""TDD: R8 — Kokoro is the reference runtime shape.

The ``runtime-registry/kokoro-82m/descriptor.json`` is the
canonical reference shape. Every future runtime (F5-TTS, XTTS,
OpenVoice, Fish, OmniVoice) is a copy of this shape with
targeted edits.

This test asserts that the Kokoro descriptor:

  1. Parses cleanly against the closed schema.
  2. Carries the R2 ``spec.build`` block (CE-only).
  3. Declares the R7 ``spec.lifecycle.idle_timeout`` (CE default).
  4. Binds to the ``kokoro-base`` model with is_default = true.
  5. Includes the 5-endpoint Runtime Service Contract in
     ``spec.service``.
  6. Image is the source of truth: ``peakvox/kokoro-runtime:0.1.0``.
  7. Edition includes ``ce``.

The test is the canonical R8 reference test; new runtimes
mirror this shape, and their tests are structurally similar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services.runtime_types import RuntimeDescriptor


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _kokoro_descriptor_path() -> Path:
    """The canonical location of the Kokoro reference descriptor.

    The path is the runtime-registry/ directory at the repo root
    (sibling of backend/), per ADR-0017 §2.1 + R1.
    """
    return Path(__file__).resolve().parents[2] / "runtime-registry" / "kokoro-82m" / "descriptor.json"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_kokoro_descriptor_exists_at_canonical_path() -> None:
    """The Kokoro descriptor is published at the canonical location."""
    p = _kokoro_descriptor_path()
    assert p.exists(), f"missing reference descriptor at {p}"


def test_kokoro_descriptor_loads_as_valid_json() -> None:
    """The descriptor is valid JSON and parses against the schema."""
    p = _kokoro_descriptor_path()
    with p.open() as f:
        payload = json.load(f)
    d = RuntimeDescriptor.model_validate(payload)
    assert d.metadata.id == "kokoro-82m"


# ---------------------------------------------------------------------------
# R8 reference invariants
# ---------------------------------------------------------------------------


def test_kokoro_descriptor_is_default_for_kokoro_base_model() -> None:
    """The Kokoro runtime is the default for the kokoro-base model
    (is_default = true; priority 100)."""
    p = _kokoro_descriptor_path()
    payload = json.loads(p.read_text())
    d = RuntimeDescriptor.model_validate(payload)
    assert d.spec.model_binding.model_id == "kokoro-base"
    assert d.spec.model_binding.is_default is True
    assert d.spec.model_binding.priority == 100


def test_kokoro_descriptor_includes_ce_edition() -> None:
    """The Kokoro runtime declares ce in metadata.edition."""
    p = _kokoro_descriptor_path()
    payload = json.loads(p.read_text())
    d = RuntimeDescriptor.model_validate(payload)
    assert "ce" in d.metadata.edition


def test_kokoro_descriptor_image_is_canonical() -> None:
    """The image identity is peakvox/kokoro-runtime:0.1.0 (no digest
    pre-set; the build script populates digest after docker build)."""
    p = _kokoro_descriptor_path()
    payload = json.loads(p.read_text())
    d = RuntimeDescriptor.model_validate(payload)
    assert d.spec.image.repository == "peakvox/kokoro-runtime"
    assert d.spec.image.tag == "0.1.0"
    assert d.spec.image.digest is None  # set by build script


# ---------------------------------------------------------------------------
# R2 — spec.build
# ---------------------------------------------------------------------------


def test_kokoro_descriptor_has_spec_build_block() -> None:
    """The Kokoro descriptor carries the R2 spec.build block
    (CE-only; the manager never reads it)."""
    p = _kokoro_descriptor_path()
    payload = json.loads(p.read_text())
    d = RuntimeDescriptor.model_validate(payload)
    assert d.spec.build is not None
    assert d.spec.build.entrypoint == "server.py"
    assert d.spec.build.build_context == "."
    assert d.spec.build.dockerfile == "Dockerfile"


# ---------------------------------------------------------------------------
# R7 — spec.lifecycle.idle_timeout
# ---------------------------------------------------------------------------


def test_kokoro_descriptor_has_idle_timeout_15m() -> None:
    """The Kokoro descriptor declares idle_timeout = '15m' (CE default)."""
    p = _kokoro_descriptor_path()
    payload = json.loads(p.read_text())
    d = RuntimeDescriptor.model_validate(payload)
    assert d.spec.lifecycle.idle_timeout == "15m"


# ---------------------------------------------------------------------------
# Runtime Service Contract
# ---------------------------------------------------------------------------


def test_kokoro_descriptor_declares_5_endpoint_contract() -> None:
    """The Kokoro descriptor carries the 5-endpoint Runtime Service
    Contract in spec.service."""
    p = _kokoro_descriptor_path()
    payload = json.loads(p.read_text())
    d = RuntimeDescriptor.model_validate(payload)
    assert d.spec.service.protocol == "http"
    assert d.spec.service.port == 8000
    assert d.spec.service.health_path == "/health"
    assert d.spec.service.readiness_path == "/ready"
    assert d.spec.service.generate_path == "/v1/generate"
    assert d.spec.service.build_path == "/v1/variants/build"
    assert d.spec.service.metadata_path == "/v1/metadata"


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


def test_kokoro_descriptor_capabilities_subset_of_vocabulary() -> None:
    """The Kokoro descriptor's capabilities are in the closed vocabulary."""
    p = _kokoro_descriptor_path()
    payload = json.loads(p.read_text())
    d = RuntimeDescriptor.model_validate(payload)
    assert "tts" in d.spec.capabilities


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_kokoro_descriptor_round_trips_through_model_dump() -> None:
    """The descriptor round-trips through model_dump + model_validate
    without loss. This is the R8 reference for future runtimes."""
    p = _kokoro_descriptor_path()
    payload = json.loads(p.read_text())
    d1 = RuntimeDescriptor.model_validate(payload)
    dumped = d1.model_dump()
    d2 = RuntimeDescriptor.model_validate(dumped)

    assert d1.metadata.id == d2.metadata.id
    assert d1.spec.image.repository == d2.spec.image.repository
    assert d1.spec.image.tag == d2.spec.image.tag
    assert d1.spec.build is not None
    assert d2.spec.build is not None
    assert d1.spec.build.entrypoint == d2.spec.build.entrypoint
    assert d1.spec.build.build_context == d2.spec.build.build_context
    assert d1.spec.build.dockerfile == d2.spec.build.dockerfile
    assert d1.spec.lifecycle.idle_timeout == d2.spec.lifecycle.idle_timeout
    assert d1.spec.service.port == d2.spec.service.port
    assert d1.spec.model_binding.model_id == d2.spec.model_binding.model_id
