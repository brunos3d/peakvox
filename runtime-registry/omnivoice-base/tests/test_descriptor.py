"""TDD: T12.1 — Descriptor schema validation.

The omnivoice-base descriptor must validate against the
canonical RuntimeDescriptor pydantic schema, bind to the
omnivoice-base model in the catalog, and declare a capability
subset that matches the model's declared capabilities.

These are pure structural tests: they read the descriptor as
text + JSON and assert the contract. They do not require the
runtime image to be built or the container to run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _omnivoice_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _descriptor_path() -> Path:
    return _omnivoice_dir() / "descriptor.json"


def _read_descriptor() -> dict:
    p = _descriptor_path()
    assert p.exists(), f"missing descriptor.json at {p}"
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# Existence + minimum files for the R8 reference shape
# ---------------------------------------------------------------------------


def test_descriptor_exists_at_canonical_path() -> None:
    assert _descriptor_path().exists()


def test_omnivoice_dir_has_dockerfile() -> None:
    """The Dockerfile is part of the R8 reference shape (build)."""
    assert (_omnivoice_dir() / "Dockerfile").exists()


def test_omnivoice_dir_has_server_py() -> None:
    """The server.py is part of the R8 reference shape (entrypoint)."""
    assert (_omnivoice_dir() / "server.py").exists()


def test_omnivoice_dir_has_requirements_txt() -> None:
    assert (_omnivoice_dir() / "requirements.txt").exists()


def test_omnivoice_dir_has_readme() -> None:
    assert (_omnivoice_dir() / "README.md").exists()


# ---------------------------------------------------------------------------
# Descriptor schema basics
# ---------------------------------------------------------------------------


def test_descriptor_api_version_is_peakvox_v1() -> None:
    d = _read_descriptor()
    assert d["api_version"] == "peakvox.io/v1"


def test_descriptor_kind_is_runtime() -> None:
    d = _read_descriptor()
    assert d["kind"] == "Runtime"


def test_descriptor_metadata_id_is_omnivoice_base() -> None:
    d = _read_descriptor()
    assert d["metadata"]["id"] == "omnivoice-base"


def test_descriptor_metadata_edition_includes_ce() -> None:
    d = _read_descriptor()
    assert "ce" in d["metadata"]["edition"]


def test_descriptor_image_repository_matches_omnivoice() -> None:
    d = _read_descriptor()
    assert d["spec"]["image"]["repository"] == "peakvox/omnivoice-runtime"


def test_descriptor_image_tag_present() -> None:
    d = _read_descriptor()
    assert d["spec"]["image"]["tag"] == "0.1.0"


# ---------------------------------------------------------------------------
# Runtime Service Contract
# ---------------------------------------------------------------------------


def test_descriptor_service_port_is_8000() -> None:
    d = _read_descriptor()
    assert d["spec"]["service"]["port"] == 8000


def test_descriptor_service_paths_match_contract() -> None:
    d = _read_descriptor()
    svc = d["spec"]["service"]
    assert svc["health_path"] == "/health"
    assert svc["readiness_path"] == "/ready"
    assert svc["generate_path"] == "/v1/generate"
    assert svc["build_path"] == "/v1/variants/build"
    assert svc["metadata_path"] == "/v1/metadata"


# ---------------------------------------------------------------------------
# Model binding
# ---------------------------------------------------------------------------


def test_descriptor_model_binding_targets_omnivoice_base() -> None:
    d = _read_descriptor()
    assert d["spec"]["model_binding"]["model_id"] == "omnivoice-base"


def test_descriptor_model_binding_is_default() -> None:
    d = _read_descriptor()
    assert d["spec"]["model_binding"]["is_default"] is True


# ---------------------------------------------------------------------------
# Capabilities — must not over-claim
# ---------------------------------------------------------------------------


def test_descriptor_capabilities_are_vocabulary_subset() -> None:
    """Every declared capability must be in the closed vocabulary."""
    from app.services.runtime_types import RUNTIME_CAPABILITY_VOCABULARY
    d = _read_descriptor()
    declared = set(d["spec"]["capabilities"])
    unknown = declared - RUNTIME_CAPABILITY_VOCABULARY
    assert not unknown, f"unknown capabilities: {sorted(unknown)}"


def test_descriptor_capabilities_are_subset_of_bound_model() -> None:
    """The runtime's capabilities must be a subset of the bound
    model's declared capabilities (ADR-0017 §1.5)."""
    from app.services.runtime_types import RuntimeDescriptor
    from app.services.model_catalog import BUILTIN_MODELS
    d = _read_descriptor()
    desc = RuntimeDescriptor.model_validate(d)
    model = next((m for m in BUILTIN_MODELS if m.id == desc.spec.model_binding.model_id), None)
    assert model is not None, (
        f"no model in BUILTIN_MODELS with id {desc.spec.model_binding.model_id!r}"
    )
    desc.validate_capabilities_subset_of(model.capabilities)


def test_descriptor_declares_tts_and_voice_cloning() -> None:
    """OmniVoice is a voice-cloning TTS — both must be present."""
    d = _read_descriptor()
    assert "tts" in d["spec"]["capabilities"]
    assert "voice_cloning" in d["spec"]["capabilities"]


def test_descriptor_does_not_declare_unsupported_capabilities() -> None:
    """OmniVoice base does not support singing or streaming
    (per the BUILTIN_MODELS catalog). The descriptor must not
    claim them."""
    d = _read_descriptor()
    assert "singing" not in d["spec"]["capabilities"]
    assert "streaming" not in d["spec"]["capabilities"]


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------


def test_descriptor_requirements_edition_is_ce_cloud() -> None:
    d = _read_descriptor()
    ed = set(d["spec"]["requirements"]["edition"])
    assert ed.issuperset({"ce"})


def test_descriptor_requirements_gpu_is_optional() -> None:
    """OmniVoice is CPU-capable (slow) but GPU-recommended."""
    d = _read_descriptor()
    assert d["spec"]["requirements"]["gpu"] == "optional"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_descriptor_lifecycle_idle_timeout_is_ce_default() -> None:
    """R7: CE default is 15m."""
    d = _read_descriptor()
    assert d["spec"]["lifecycle"]["idle_timeout"] == "15m"


# ---------------------------------------------------------------------------
# Build metadata (R2)
# ---------------------------------------------------------------------------


def test_descriptor_build_metadata_present() -> None:
    """R2: CE-only build metadata is present."""
    d = _read_descriptor()
    build = d["spec"].get("build")
    assert build is not None
    assert build["entrypoint"] == "server.py"
    assert build["dockerfile"] == "Dockerfile"
    assert build["build_context"] == "."
