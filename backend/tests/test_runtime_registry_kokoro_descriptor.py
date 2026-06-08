"""TDD: runtime-registry/ directory + Kokoro descriptor (2D.5).

The runtime-registry/ directory at the repo root holds runtime
descriptors (one per runtime). The on-disk format for 2D is
JSON (``descriptor.json``); YAML is the canonical format per
ADR-0017 §1.1 and lands in a later phase. The loader is
format-agnostic — it can be re-targeted by adding a YAML parser.

Layout::

    runtime-registry/
        kokoro-82m/
            descriptor.json
        (future descriptors)

The Kokoro descriptor binds to the existing model id
``kokoro-base`` (per ``backend/app/services/model_catalog.py``
line 210). The descriptor's capabilities are a subset of
``ModelCapabilities`` (ADR-0017 §1.5).

These tests verify:
- The descriptor file exists.
- It parses cleanly.
- It validates against the ``RuntimeDescriptor`` schema.
- It binds to ``kokoro-base`` (model id from the catalog).
- Its ``metadata.edition`` includes ``ce``.
- Its capabilities are a subset of the bound model's
  ``ModelCapabilities`` (no implicit capabilities).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# Resolve the runtime-registry/ directory at the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_REGISTRY_ROOT = REPO_ROOT / "runtime-registry"
KOKORO_DESCRIPTOR_PATH = (
    RUNTIME_REGISTRY_ROOT / "kokoro-82m" / "descriptor.json"
)


def test_runtime_registry_root_exists() -> None:
    """The runtime-registry/ directory exists at the repo root."""
    assert RUNTIME_REGISTRY_ROOT.exists(), (
        f"runtime-registry/ directory missing at {RUNTIME_REGISTRY_ROOT}"
    )
    assert RUNTIME_REGISTRY_ROOT.is_dir()


def test_kokoro_descriptor_file_exists() -> None:
    """The Kokoro descriptor file is published."""
    assert KOKORO_DESCRIPTOR_PATH.exists(), (
        f"Kokoro descriptor missing at {KOKORO_DESCRIPTOR_PATH}"
    )
    assert KOKORO_DESCRIPTOR_PATH.is_file()


def test_kokoro_descriptor_parses_as_valid_json() -> None:
    """The descriptor file is well-formed JSON."""
    raw = KOKORO_DESCRIPTOR_PATH.read_text()
    payload = json.loads(raw)
    assert isinstance(payload, dict)


def test_kokoro_descriptor_validates_against_runtime_descriptor_schema() -> None:
    """The descriptor validates against the RuntimeDescriptor Pydantic schema."""
    from app.services.runtime_types import RuntimeDescriptor

    raw = KOKORO_DESCRIPTOR_PATH.read_text()
    payload = json.loads(raw)
    desc = RuntimeDescriptor.model_validate(payload)
    assert desc.metadata.id == "kokoro-82m"
    assert desc.kind == "Runtime"
    assert desc.api_version == "peakvox.io/v1"


def test_kokoro_descriptor_binds_to_kokoro_base_model() -> None:
    """The descriptor's model_binding.model_id is 'kokoro-base'."""
    from app.services.runtime_types import RuntimeDescriptor

    raw = KOKORO_DESCRIPTOR_PATH.read_text()
    desc = RuntimeDescriptor.model_validate(json.loads(raw))
    assert desc.spec.model_binding.model_id == "kokoro-base"
    assert desc.spec.model_binding.is_default is True


def test_kokoro_descriptor_edition_includes_ce() -> None:
    """The descriptor's metadata.edition includes 'ce'."""
    from app.services.runtime_types import RuntimeDescriptor

    raw = KOKORO_DESCRIPTOR_PATH.read_text()
    desc = RuntimeDescriptor.model_validate(json.loads(raw))
    assert "ce" in desc.metadata.edition


def test_kokoro_descriptor_capabilities_subset_of_model_caps() -> None:
    """The descriptor's capabilities are a subset of the bound
    model's ModelCapabilities (no implicit capabilities)."""
    from app.models.registry_types import ModelCapabilities
    from app.services.runtime_types import RuntimeDescriptor

    raw = KOKORO_DESCRIPTOR_PATH.read_text()
    desc = RuntimeDescriptor.model_validate(json.loads(raw))

    # The bound model's capabilities (Kokoro TTS only).
    model_caps = ModelCapabilities(
        supports_tts=True,
        supports_streaming=True,
    )
    # Should not raise.
    desc.validate_capabilities_subset_of(model_caps)


def test_kokoro_descriptor_capabilities_subset_rejects_unsupported() -> None:
    """If a capability is not supported by the model, the
    validation raises ValueError. Guards against accidental
    capability inflation in the descriptor."""
    from app.models.registry_types import ModelCapabilities
    from app.services.runtime_types import RuntimeDescriptor

    raw = KOKORO_DESCRIPTOR_PATH.read_text()
    desc = RuntimeDescriptor.model_validate(json.loads(raw))

    # A model with TTS disabled rejects any TTS-declaring descriptor.
    model_caps = ModelCapabilities(supports_tts=False)
    if "tts" in desc.spec.capabilities:
        with pytest.raises(ValueError, match="not supported by"):
            desc.validate_capabilities_subset_of(model_caps)


def test_kokoro_descriptor_loader_picks_it_up() -> None:
    """The RuntimeRegistryLoader picks up the descriptor from
    the runtime-registry/ directory."""
    from app.services.runtime_registry import RuntimeRegistryLoader

    loader = RuntimeRegistryLoader()
    registry = loader.load_from_directory(RUNTIME_REGISTRY_ROOT)
    assert "kokoro-82m" in registry
    desc = registry.get("kokoro-82m")
    assert desc is not None
    assert desc.spec.model_binding.model_id == "kokoro-base"
    # The model_id index should be populated.
    rts_for_kokoro = registry.list_for_model("kokoro-base")
    assert any(d.metadata.id == "kokoro-82m" for d in rts_for_kokoro)
