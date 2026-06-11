"""Tests for RuntimeVariant resolution wiring (ADR-0018 Phase 1; Task 27 C).

The registry can now *select* the RuntimeVariant for a (runtime, model):
  - explicit model-bound variant wins,
  - else the default / ``base`` variant,
  - else ``None`` — the implicit-base case (runtime ships no variants/), which
    keeps every existing single-``base`` runtime byte-identical.

The ``trust`` provenance field defaults to ``verified`` so first-party variants
are curated-by-default and pre-existing descriptors stay valid.
"""

from __future__ import annotations

from app.services.runtime_registry import RuntimeRegistry
from app.services.runtime_types import RuntimeDescriptor, RuntimeVariantDescriptor


def _runtime(runtime_id: str = "f5-tts-base", model_id: str = "f5-tts-base") -> RuntimeDescriptor:
    return RuntimeDescriptor.model_validate(
        {
            "api_version": "peakvox.io/v1",
            "kind": "Runtime",
            "metadata": {
                "id": runtime_id,
                "name": "F5-TTS",
                "provider": "f5-tts",
                "version": "0.1.0",
                "edition": ["ce", "cloud"],
                "labels": {"model_family": "f5-tts"},
            },
            "spec": {
                "runtime_type": "docker",
                "image": {"repository": "peakvox/f5-tts-runtime", "tag": "0.1.0"},
                "service": {"protocol": "http", "port": 8000},
                "capabilities": ["tts", "voice_cloning", "multilingual"],
                "requirements": {"gpu": "required", "edition": ["ce", "cloud"]},
                "model_binding": {"model_id": model_id, "is_default": True},
            },
        }
    )


def _variant(
    *,
    variant_id: str,
    runtime_id: str = "f5-tts-base",
    model_id: str,
    is_default: bool = False,
    trust: str = "verified",
) -> RuntimeVariantDescriptor:
    return RuntimeVariantDescriptor.model_validate(
        {
            "api_version": "peakvox.io/v1",
            "kind": "RuntimeVariant",
            "metadata": {
                "id": variant_id,
                "name": f"F5-TTS {variant_id}",
                "runtime_id": runtime_id,
                "trust": trust,
            },
            "spec": {
                "model_binding": {"model_id": model_id, "is_default": is_default},
                "checkpoint": {"source_type": "hf", "source_ref": f"owner/{variant_id}"},
                "is_default": is_default,
                "capabilities": ["tts"],
            },
        }
    )


def test_select_variant_returns_none_for_runtime_without_variants() -> None:
    reg = RuntimeRegistry([_runtime()])
    # Implicit-base: no explicit variant; resolution stays byte-identical.
    assert reg.select_variant("f5-tts-base", "f5-tts-base") is None


def test_select_variant_prefers_model_bound_match() -> None:
    base = _variant(variant_id="base", model_id="f5-tts-base", is_default=True)
    ptbr = _variant(variant_id="pt-br", model_id="f5-tts-pt-br")
    reg = RuntimeRegistry([_runtime()], [base, ptbr])
    chosen = reg.select_variant("f5-tts-base", "f5-tts-pt-br")
    assert chosen is not None
    assert chosen.metadata.id == "pt-br"


def test_select_variant_falls_back_to_default() -> None:
    base = _variant(variant_id="base", model_id="f5-tts-base", is_default=True)
    ptbr = _variant(variant_id="pt-br", model_id="f5-tts-pt-br")
    reg = RuntimeRegistry([_runtime()], [base, ptbr])
    # A model with no model-bound variant falls back to the default variant.
    chosen = reg.select_variant("f5-tts-base", "some-other-model")
    assert chosen is not None
    assert chosen.metadata.id == "base"


def test_variant_trust_defaults_to_verified() -> None:
    base = _variant(variant_id="base", model_id="f5-tts-base", is_default=True)
    assert base.metadata.trust == "verified"


def test_variant_trust_can_be_community() -> None:
    imported = _variant(
        variant_id="pt-br", model_id="f5-tts-pt-br", trust="community"
    )
    assert imported.metadata.trust == "community"
