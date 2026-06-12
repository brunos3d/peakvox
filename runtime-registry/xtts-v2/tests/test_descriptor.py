"""Descriptor schema validation for xtts-v2 (Task 30, ADR-0021).

The xtts-v2 descriptor must validate against the canonical RuntimeDescriptor
pydantic schema and bind to the xtts-v2 model in the catalog. Capabilities are
an honest subset of the model's declared capabilities — XTTS v2 is a
multilingual voice-cloning TTS, GPU-OPTIONAL (the key divergence from F5-TTS,
which is GPU-required).

Pure structural tests: they read the descriptor as text + JSON and assert the
contract. They do not require the runtime image to be built or the container
to run.
"""

from __future__ import annotations

import json
from pathlib import Path


def _xtts_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _descriptor_path() -> Path:
    return _xtts_dir() / "descriptor.json"


def _read_descriptor() -> dict:
    p = _descriptor_path()
    assert p.exists(), f"missing descriptor.json at {p}"
    return json.loads(p.read_text())


# --- Existence + minimum files for the R8 reference shape ------------------


def test_descriptor_exists_at_canonical_path() -> None:
    assert _descriptor_path().exists()


def test_xtts_dir_has_dockerfile() -> None:
    assert (_xtts_dir() / "Dockerfile").exists()


def test_xtts_dir_has_server_py() -> None:
    assert (_xtts_dir() / "server.py").exists()


def test_xtts_dir_has_requirements_txt() -> None:
    assert (_xtts_dir() / "requirements.txt").exists()


def test_xtts_dir_has_readme() -> None:
    assert (_xtts_dir() / "README.md").exists()


def test_xtts_dir_has_base_variant() -> None:
    assert (_xtts_dir() / "variants" / "base.json").exists()


# --- Descriptor schema basics ----------------------------------------------


def test_descriptor_api_version_is_peakvox_v1() -> None:
    assert _read_descriptor()["api_version"] == "peakvox.io/v1"


def test_descriptor_kind_is_runtime() -> None:
    assert _read_descriptor()["kind"] == "Runtime"


def test_descriptor_metadata_id_is_xtts_v2() -> None:
    assert _read_descriptor()["metadata"]["id"] == "xtts-v2"


def test_descriptor_provider_is_xtts() -> None:
    assert _read_descriptor()["metadata"]["provider"] == "xtts"


def test_descriptor_metadata_edition_includes_ce() -> None:
    assert "ce" in _read_descriptor()["metadata"]["edition"]


def test_descriptor_image_repository_matches_xtts() -> None:
    assert _read_descriptor()["spec"]["image"]["repository"] == "peakvox/xtts-runtime"


def test_descriptor_image_tag_present() -> None:
    assert _read_descriptor()["spec"]["image"]["tag"] == "0.1.0"


def test_descriptor_image_size_metadata_present() -> None:
    img = _read_descriptor()["spec"]["image"]
    assert img.get("image_size_mb") is not None
    assert img["image_size_mb"] > 0


# --- Runtime Service Contract ----------------------------------------------


def test_descriptor_service_port_is_8000() -> None:
    assert _read_descriptor()["spec"]["service"]["port"] == 8000


def test_descriptor_service_paths_match_contract() -> None:
    svc = _read_descriptor()["spec"]["service"]
    assert svc["health_path"] == "/health"
    assert svc["readiness_path"] == "/ready"
    assert svc["generate_path"] == "/v1/generate"
    assert svc["build_path"] == "/v1/variants/build"
    assert svc["metadata_path"] == "/v1/metadata"


# --- Model binding ----------------------------------------------------------


def test_descriptor_model_binding_targets_xtts_v2() -> None:
    assert _read_descriptor()["spec"]["model_binding"]["model_id"] == "xtts-v2"


def test_descriptor_model_binding_is_default() -> None:
    assert _read_descriptor()["spec"]["model_binding"]["is_default"] is True


# --- Capabilities — must not over-claim ------------------------------------


def test_descriptor_capabilities_are_vocabulary_subset() -> None:
    from app.services.runtime_types import RUNTIME_CAPABILITY_VOCABULARY
    declared = set(_read_descriptor()["spec"]["capabilities"])
    assert not (declared - RUNTIME_CAPABILITY_VOCABULARY)


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


def test_descriptor_declares_tts_cloning_multilingual_reference() -> None:
    caps = _read_descriptor()["spec"]["capabilities"]
    assert "tts" in caps
    assert "voice_cloning" in caps
    assert "multilingual" in caps
    assert "reference_audio" in caps


def test_descriptor_does_not_declare_unsupported_capabilities() -> None:
    """XTTS v2 dropped explicit emotion/style tokens, and the PeakVox contract
    does not wire streaming/voice-conversion/training. The descriptor must not
    claim them."""
    caps = _read_descriptor()["spec"]["capabilities"]
    for over in ("singing", "voice_design", "emotion_tags", "emotions",
                 "streaming", "voice_conversion", "custom_training",
                 "speaker_embeddings"):
        assert over not in caps


# --- Requirements — XTTS is GPU-OPTIONAL (the divergence from F5) -----------


def test_descriptor_requirements_gpu_is_optional() -> None:
    """The defining property: XTTS runs on CPU, so gpu is 'optional', NOT
    'required'. This is what makes the Docker driver honor the Use GPU setting
    as a clean GPU<->CPU switch (Phase K)."""
    assert _read_descriptor()["spec"]["requirements"]["gpu"] == "optional"


def test_descriptor_requirements_min_vram_is_modest() -> None:
    """XTTS needs ~4 GB VRAM on GPU — far less than F5's 12 GB."""
    vram = _read_descriptor()["spec"]["requirements"]["min_vram_gb"]
    assert vram is not None
    assert 0 < vram <= 8


def test_descriptor_requirements_edition_is_ce_cloud() -> None:
    ed = set(_read_descriptor()["spec"]["requirements"]["edition"])
    assert ed.issuperset({"ce", "cloud"})


# --- Lifecycle --------------------------------------------------------------


def test_descriptor_lifecycle_idle_timeout_is_ce_default() -> None:
    assert _read_descriptor()["spec"]["lifecycle"]["idle_timeout"] == "15m"


def test_descriptor_lifecycle_start_timeout_is_generous() -> None:
    """Model download + load (CPU especially) can take a while."""
    assert _read_descriptor()["spec"]["lifecycle"]["start_timeout_seconds"] >= 120


# --- Build metadata (R2) ----------------------------------------------------


def test_descriptor_build_metadata_present() -> None:
    build = _read_descriptor()["spec"].get("build")
    assert build is not None
    assert build["entrypoint"] == "server.py"
    assert build["dockerfile"] == "Dockerfile"
    assert build["build_context"] == "."


# --- Base variant (ADR-0018) ------------------------------------------------


def test_base_variant_validates_and_binds_to_runtime() -> None:
    from app.services.runtime_types import RuntimeVariantDescriptor
    raw = json.loads((_xtts_dir() / "variants" / "base.json").read_text())
    v = RuntimeVariantDescriptor.model_validate(raw)
    assert v.metadata.runtime_id == "xtts-v2"
    assert v.metadata.id == "base"
    assert v.spec.is_default is True
    assert v.spec.model_binding.model_id == "xtts-v2"
