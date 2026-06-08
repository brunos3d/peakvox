"""TDD: T12.2 — Descriptor schema validation for f5-tts-base.

The f5-tts-base descriptor must validate against the canonical
RuntimeDescriptor pydantic schema and bind to the f5-tts-base
model in the catalog. Capabilities are an honest subset of the
model's declared capabilities — F5-TTS is a flow-matching
voice-cloning TTS, GPU-only.

These are pure structural tests: they read the descriptor as
text + JSON and assert the contract. They do not require the
runtime image to be built or the container to run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _f5_tts_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _descriptor_path() -> Path:
    return _f5_tts_dir() / "descriptor.json"


def _read_descriptor() -> dict:
    p = _descriptor_path()
    assert p.exists(), f"missing descriptor.json at {p}"
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# Existence + minimum files for the R8 reference shape
# ---------------------------------------------------------------------------


def test_descriptor_exists_at_canonical_path() -> None:
    assert _descriptor_path().exists()


def test_f5_tts_dir_has_dockerfile() -> None:
    assert (_f5_tts_dir() / "Dockerfile").exists()


def test_f5_tts_dir_has_server_py() -> None:
    assert (_f5_tts_dir() / "server.py").exists()


def test_f5_tts_dir_has_requirements_txt() -> None:
    assert (_f5_tts_dir() / "requirements.txt").exists()


def test_f5_tts_dir_has_readme() -> None:
    assert (_f5_tts_dir() / "README.md").exists()


# ---------------------------------------------------------------------------
# Descriptor schema basics
# ---------------------------------------------------------------------------


def test_descriptor_api_version_is_peakvox_v1() -> None:
    d = _read_descriptor()
    assert d["api_version"] == "peakvox.io/v1"


def test_descriptor_kind_is_runtime() -> None:
    d = _read_descriptor()
    assert d["kind"] == "Runtime"


def test_descriptor_metadata_id_is_f5_tts_base() -> None:
    d = _read_descriptor()
    assert d["metadata"]["id"] == "f5-tts-base"


def test_descriptor_metadata_edition_includes_ce() -> None:
    d = _read_descriptor()
    assert "ce" in d["metadata"]["edition"]


def test_descriptor_image_repository_matches_f5_tts() -> None:
    d = _read_descriptor()
    assert d["spec"]["image"]["repository"] == "peakvox/f5-tts-runtime"


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


def test_descriptor_model_binding_targets_f5_tts_base() -> None:
    d = _read_descriptor()
    assert d["spec"]["model_binding"]["model_id"] == "f5-tts-base"


def test_descriptor_model_binding_is_default() -> None:
    d = _read_descriptor()
    assert d["spec"]["model_binding"]["is_default"] is True


# ---------------------------------------------------------------------------
# Capabilities — must not over-claim
# ---------------------------------------------------------------------------


def test_descriptor_capabilities_are_vocabulary_subset() -> None:
    from app.services.runtime_types import RUNTIME_CAPABILITY_VOCABULARY
    d = _read_descriptor()
    declared = set(d["spec"]["capabilities"])
    unknown = declared - RUNTIME_CAPABILITY_VOCABULARY
    assert not unknown, f"unknown capabilities: {sorted(unknown)}"


def test_descriptor_capabilities_are_subset_of_bound_model() -> None:
    from app.services.runtime_types import RuntimeDescriptor
    from app.services.model_catalog import BUILTIN_MODELS
    d = _read_descriptor()
    desc = RuntimeDescriptor.model_validate(d)
    model = next((m for m in BUILTIN_MODELS if m.id == desc.spec.model_binding.model_id), None)
    assert model is not None, (
        f"no model in BUILTIN_MODELS with id {desc.spec.model_binding.model_id!r}"
    )
    desc.validate_capabilities_subset_of(model.capabilities)


def test_descriptor_declares_tts_voice_cloning_reference_audio() -> None:
    """F5-TTS is a flow-matching voice-cloning TTS — all three
    must be present."""
    d = _read_descriptor()
    assert "tts" in d["spec"]["capabilities"]
    assert "voice_cloning" in d["spec"]["capabilities"]
    assert "reference_audio" in d["spec"]["capabilities"]


def test_descriptor_does_not_declare_unsupported_capabilities() -> None:
    """F5-TTS does not support singing, voice design, emotion
    tags, or streaming (per the catalog). The descriptor must
    not claim them."""
    d = _read_descriptor()
    assert "singing" not in d["spec"]["capabilities"]
    assert "voice_design" not in d["spec"]["capabilities"]
    assert "emotion_tags" not in d["spec"]["capabilities"]
    assert "streaming" not in d["spec"]["capabilities"]


# ---------------------------------------------------------------------------
# Requirements — F5-TTS is GPU-only
# ---------------------------------------------------------------------------


def test_descriptor_requirements_gpu_is_required() -> None:
    d = _read_descriptor()
    assert d["spec"]["requirements"]["gpu"] == "required"


def test_descriptor_requirements_min_vram_is_at_least_8gb() -> None:
    """F5-TTS in BF16 needs ~12 GB VRAM; the descriptor must
    declare at least 8 GB (the documented minimum)."""
    d = _read_descriptor()
    assert d["spec"]["requirements"]["min_vram_gb"] is not None
    assert d["spec"]["requirements"]["min_vram_gb"] >= 8


def test_descriptor_requirements_edition_is_ce_cloud() -> None:
    d = _read_descriptor()
    ed = set(d["spec"]["requirements"]["edition"])
    assert ed.issuperset({"ce", "cloud"})


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_descriptor_lifecycle_idle_timeout_is_ce_default() -> None:
    """R7: CE default is 15m."""
    d = _read_descriptor()
    assert d["spec"]["lifecycle"]["idle_timeout"] == "15m"


def test_descriptor_lifecycle_start_timeout_is_generous() -> None:
    """GPU model load + weights download can take >60s; the
    descriptor must allow a generous start_timeout."""
    d = _read_descriptor()
    assert d["spec"]["lifecycle"]["start_timeout_seconds"] >= 120


# ---------------------------------------------------------------------------
# Build metadata (R2)
# ---------------------------------------------------------------------------


def test_descriptor_build_metadata_present() -> None:
    d = _read_descriptor()
    build = d["spec"].get("build")
    assert build is not None
    assert build["entrypoint"] == "server.py"
    assert build["dockerfile"] == "Dockerfile"
    assert build["build_context"] == "."
