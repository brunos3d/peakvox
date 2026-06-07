"""TDD: RuntimeDescriptor (2A.1) — the schema for runtime.yaml.

Phase 2A is infrastructure foundation work. RuntimeDescriptor is the
schema contract for runtime descriptors (ADR-0017 §1). No Docker
integration, no runtime activation, no service communication.

These tests assert:
- Required fields are enforced.
- api_version / kind have the canonical values for v1.
- metadata.id follows DNS-label rules.
- spec.capabilities is a subset of a bound model's ModelCapabilities
  (caller-driven; the descriptor carries the vocabulary, the loader
  wires the model).
- spec.requirements.edition is a subset of metadata.edition.
- spec.image.digest, when present, is a valid sha256 digest.
- model_dump round-trip preserves the descriptor.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.registry_types import ModelCapabilities
from app.services.runtime_types import (
    RUNTIME_CAPABILITY_VOCABULARY,
    RuntimeDescriptor,
)


def _good_dict() -> dict:
    return {
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": "kokoro-cpu",
            "name": "Kokoro CPU Runtime",
            "description": "CPU-capable Kokoro 82M TTS runtime.",
            "provider": "kokoro",
            "version": "1.4.2",
            "edition": ["ce", "cloud"],
            "labels": {"family": "tts", "license": "apache-2.0"},
        },
        "spec": {
            "runtime_type": "docker",
            "image": {
                "repository": "peakvox/kokoro-runtime",
                "tag": "1.4.2",
                "digest": "sha256:" + "a" * 64,
            },
            "service": {
                "protocol": "http",
                "port": 8000,
                "health_path": "/health",
                "readiness_path": "/ready",
                "generate_path": "/v1/generate",
                "build_path": "/v1/variants/build",
                "metadata_path": "/v1/metadata",
            },
            "capabilities": ["tts", "multilingual"],
            "requirements": {
                "gpu": "none",
                "cpu_cores": 1,
                "memory_gb": 2,
                "edition": ["ce", "cloud"],
            },
            "model_binding": {
                "model_id": "kokoro-base",
                "is_default": True,
                "priority": 100,
            },
            "lifecycle": {
                "install_policy": "pull-on-install",
                "health_interval_seconds": 10,
                "health_timeout_seconds": 3,
                "start_timeout_seconds": 60,
                "restart_policy": "on-failure",
            },
        },
    }


def test_runtime_descriptor_accepts_a_known_good_dict() -> None:
    desc = RuntimeDescriptor.model_validate(_good_dict())
    assert desc.metadata.id == "kokoro-cpu"
    assert desc.spec.image.repository == "peakvox/kokoro-runtime"
    assert desc.spec.service.port == 8000
    assert desc.spec.model_binding.model_id == "kokoro-base"
    assert desc.spec.lifecycle.health_interval_seconds == 10


def test_runtime_descriptor_rejects_wrong_api_version() -> None:
    data = _good_dict()
    data["api_version"] = "peakvox.io/v2"
    with pytest.raises(ValidationError) as excinfo:
        RuntimeDescriptor.model_validate(data)
    assert "api_version" in str(excinfo.value)


def test_runtime_descriptor_rejects_wrong_kind() -> None:
    data = _good_dict()
    data["kind"] = "NotRuntime"
    with pytest.raises(ValidationError) as excinfo:
        RuntimeDescriptor.model_validate(data)
    assert "kind" in str(excinfo.value)


def test_runtime_descriptor_rejects_missing_required_fields() -> None:
    data = _good_dict()
    del data["spec"]["image"]
    with pytest.raises(ValidationError):
        RuntimeDescriptor.model_validate(data)


def test_metadata_id_must_be_dns_label() -> None:
    data = _good_dict()
    data["metadata"]["id"] = "Not_Allowed_ID"
    with pytest.raises(ValidationError) as excinfo:
        RuntimeDescriptor.model_validate(data)
    assert "metadata.id" in str(excinfo.value).lower() or "id" in str(excinfo.value).lower()


def test_metadata_id_max_length_is_63() -> None:
    data = _good_dict()
    data["metadata"]["id"] = "a" * 64  # one over the limit
    with pytest.raises(ValidationError):
        RuntimeDescriptor.model_validate(data)


def test_requirements_edition_must_be_subset_of_metadata_edition() -> None:
    data = _good_dict()
    data["spec"]["requirements"]["edition"] = ["ce", "cloud", "edge"]
    with pytest.raises(ValidationError) as excinfo:
        RuntimeDescriptor.model_validate(data)
    assert "edition" in str(excinfo.value).lower()


def test_image_digest_must_be_sha256_when_present() -> None:
    data = _good_dict()
    data["spec"]["image"]["digest"] = "sha512:" + "b" * 128
    with pytest.raises(ValidationError):
        RuntimeDescriptor.model_validate(data)

    data["spec"]["image"]["digest"] = "sha256:" + "z" * 64
    with pytest.raises(ValidationError):
        RuntimeDescriptor.model_validate(data)


def test_image_digest_is_optional() -> None:
    data = _good_dict()
    del data["spec"]["image"]["digest"]
    desc = RuntimeDescriptor.model_validate(data)
    assert desc.spec.image.digest is None


def test_capabilities_subset_check_against_full_model_passes() -> None:
    desc = RuntimeDescriptor.model_validate(_good_dict())
    full = ModelCapabilities(
        supports_tts=True,
        supports_multilingual=True,
        supports_voice_cloning=True,
    )
    # Declared: ["tts", "multilingual"] — both supported by the model.
    desc.validate_capabilities_subset_of(full)  # no exception


def test_capabilities_subset_check_against_empty_model_raises() -> None:
    desc = RuntimeDescriptor.model_validate(_good_dict())
    # An empty ModelCapabilities has every boolean defaulting; supports_tts
    # defaults to True (per ModelCapabilities), but multilingual defaults to
    # False — so the descriptor's "multilingual" is unsupported.
    empty = ModelCapabilities()
    with pytest.raises(ValueError) as excinfo:
        desc.validate_capabilities_subset_of(empty)
    assert "multilingual" in str(excinfo.value)


def test_capabilities_subset_check_rejects_unsupported_capability() -> None:
    desc = RuntimeDescriptor.model_validate(_good_dict())
    # A model with supports_tts=False and supports_multilingual=True.
    # The descriptor's "tts" is unsupported.
    partial = ModelCapabilities(supports_tts=False, supports_multilingual=True)
    with pytest.raises(ValueError) as excinfo:
        desc.validate_capabilities_subset_of(partial)
    assert "tts" in str(excinfo.value)


def test_capability_vocabulary_is_well_defined() -> None:
    # Sanity: the vocabulary is non-empty and contains the canonical entries.
    assert "tts" in RUNTIME_CAPABILITY_VOCABULARY
    assert "voice_cloning" in RUNTIME_CAPABILITY_VOCABULARY
    assert "multilingual" in RUNTIME_CAPABILITY_VOCABULARY
    assert "singing" in RUNTIME_CAPABILITY_VOCABULARY
    assert "streaming" in RUNTIME_CAPABILITY_VOCABULARY


def test_unknown_capability_string_is_rejected() -> None:
    data = _good_dict()
    data["spec"]["capabilities"] = ["tts", "telepathy"]
    with pytest.raises(ValidationError) as excinfo:
        RuntimeDescriptor.model_validate(data)
    assert "telepathy" in str(excinfo.value) or "capabilities" in str(excinfo.value).lower()


def test_model_dump_round_trip_preserves_descriptor() -> None:
    original = RuntimeDescriptor.model_validate(_good_dict())
    dumped = original.model_dump()
    rehydrated = RuntimeDescriptor.model_validate(dumped)
    assert rehydrated == original
