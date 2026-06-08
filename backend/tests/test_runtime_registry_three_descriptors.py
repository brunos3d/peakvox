"""TDD: T12.3 — RuntimeRegistryLoader discovers all 3 descriptors.

The RuntimeRegistryLoader walks ``<registry_root>/<id>/descriptor.json``
and parses each descriptor. After TASK 12, the registry must
discover three entries:

  - kokoro-82m       (R8 reference)
  - omnivoice-base   (T12.1)
  - f5-tts-base      (T12.2)

These tests verify:
  - The loader picks up all three entries.
  - Each entry validates against the RuntimeDescriptor schema.
  - Each entry binds to a model in BUILTIN_MODELS.
  - The capabilities of each entry are a subset of its bound
    model's declared capabilities (ADR-0017 §1.5).
  - list_for_model routes correctly.

API-level coverage (3 runtimes visible via /api/runtimes and
3 models with runtimes via /api/models/with-runtimes) is
covered by the live terminal validation in T12.3's terminal
validation step, and by the updated
test_api_models_with_runtimes.py / test_api_runtimes.py test
suite which now uses the on-disk registry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_REGISTRY_ROOT = REPO_ROOT / "runtime-registry"

EXPECTED_RUNTIMES = {
    "kokoro-82m":     "kokoro-base",
    "omnivoice-base": "omnivoice-base",
    "f5-tts-base":    "f5-tts-base",
}


def _read_descriptor(runtime_id: str) -> dict:
    path = RUNTIME_REGISTRY_ROOT / runtime_id / "descriptor.json"
    assert path.exists(), f"missing descriptor at {path}"
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_runtime_registry_root_contains_three_entries() -> None:
    """The runtime-registry/ directory contains exactly three
    runtime entries after TASK 12."""
    entries = sorted(
        d.name for d in RUNTIME_REGISTRY_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith("__")
        and not d.name.startswith(".")
    )
    assert entries == sorted(EXPECTED_RUNTIMES.keys()), (
        f"expected {sorted(EXPECTED_RUNTIMES.keys())}, got {entries}"
    )


def test_loader_picks_up_all_three_descriptors() -> None:
    """The RuntimeRegistryLoader parses all three descriptors
    without error and the registry has length 3."""
    from app.services.runtime_registry import RuntimeRegistryLoader
    registry = RuntimeRegistryLoader().load_from_directory(RUNTIME_REGISTRY_ROOT)
    assert len(registry) == 3


@pytest.mark.parametrize("runtime_id,expected_model_id", list(EXPECTED_RUNTIMES.items()))
def test_each_descriptor_validates_against_schema(
    runtime_id: str, expected_model_id: str
) -> None:
    """Each descriptor file parses cleanly against RuntimeDescriptor."""
    from app.services.runtime_types import RuntimeDescriptor
    raw = _read_descriptor(runtime_id)
    desc = RuntimeDescriptor.model_validate(raw)
    assert desc.metadata.id == runtime_id
    assert desc.spec.model_binding.model_id == expected_model_id


@pytest.mark.parametrize("runtime_id,expected_model_id", list(EXPECTED_RUNTIMES.items()))
def test_each_descriptor_binds_to_a_catalog_model(
    runtime_id: str, expected_model_id: str
) -> None:
    """The bound model exists in BUILTIN_MODELS."""
    from app.services.model_catalog import BUILTIN_MODELS
    model_ids = {m.id for m in BUILTIN_MODELS}
    assert expected_model_id in model_ids, (
        f"runtime {runtime_id!r} binds to model {expected_model_id!r} "
        f"which is not in BUILTIN_MODELS"
    )


@pytest.mark.parametrize("runtime_id,expected_model_id", list(EXPECTED_RUNTIMES.items()))
def test_each_descriptor_capabilities_subset_of_bound_model(
    runtime_id: str, expected_model_id: str
) -> None:
    """Each runtime's capabilities are a subset of the bound
    model's declared capabilities (ADR-0017 §1.5)."""
    from app.services.model_catalog import BUILTIN_MODELS
    from app.services.runtime_types import RuntimeDescriptor
    raw = _read_descriptor(runtime_id)
    desc = RuntimeDescriptor.model_validate(raw)
    model = next(m for m in BUILTIN_MODELS if m.id == expected_model_id)
    desc.validate_capabilities_subset_of(model.capabilities)


@pytest.mark.parametrize("runtime_id,expected_model_id", list(EXPECTED_RUNTIMES.items()))
def test_each_descriptor_routes_to_its_model(
    runtime_id: str, expected_model_id: str
) -> None:
    """list_for_model returns the right descriptor for each
    model id."""
    from app.services.runtime_registry import RuntimeRegistryLoader
    registry = RuntimeRegistryLoader().load_from_directory(RUNTIME_REGISTRY_ROOT)
    by_model = registry.list_for_model(expected_model_id)
    assert len(by_model) == 1
    assert by_model[0].metadata.id == runtime_id


# ---------------------------------------------------------------------------
# Capability vocabulary (each descriptor must not over-claim)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("runtime_id", list(EXPECTED_RUNTIMES.keys()))
def test_each_descriptor_capabilities_in_vocabulary(runtime_id: str) -> None:
    """Every declared capability is in the closed vocabulary."""
    from app.services.runtime_types import RUNTIME_CAPABILITY_VOCABULARY
    raw = _read_descriptor(runtime_id)
    declared = set(raw["spec"]["capabilities"])
    unknown = declared - RUNTIME_CAPABILITY_VOCABULARY
    assert not unknown, f"unknown capabilities: {sorted(unknown)}"


# ---------------------------------------------------------------------------
# Runtime Service Contract — all 5 endpoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("runtime_id", list(EXPECTED_RUNTIMES.keys()))
def test_each_descriptor_exposes_full_5_endpoint_contract(runtime_id: str) -> None:
    """Every runtime declares the 5-endpoint Runtime Service
    Contract (ADR-0017 §6)."""
    raw = _read_descriptor(runtime_id)
    svc = raw["spec"]["service"]
    assert svc["health_path"] == "/health"
    assert svc["readiness_path"] == "/ready"
    assert svc["generate_path"] == "/v1/generate"
    assert svc["build_path"] == "/v1/variants/build"
    assert svc["metadata_path"] == "/v1/metadata"


@pytest.mark.parametrize("runtime_id", list(EXPECTED_RUNTIMES.keys()))
def test_each_descriptor_service_port_is_8000(runtime_id: str) -> None:
    raw = _read_descriptor(runtime_id)
    assert raw["spec"]["service"]["port"] == 8000
