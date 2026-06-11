"""Tests for RuntimeVariant community import validation (Task 27 Phase D/G/H).

Validation is pure and network-free: given a runtime descriptor and a *declared*
candidate checkpoint, decide compatibility. Compatibility is declared-and-checked
(ADR-0003), a variant may not exceed its runtime (ADR-0017 §1.5), and imported
variants are always ``community`` trust (Phase H).
"""

from __future__ import annotations

import pytest

from app.services.runtime_types import RuntimeDescriptor
from app.services.runtime_variant_import import (
    VariantImportCandidate,
    derive_variant_id,
    parse_hf_reference,
    validate_variant_import,
)


def _runtime() -> RuntimeDescriptor:
    return RuntimeDescriptor.model_validate(
        {
            "api_version": "peakvox.io/v1",
            "kind": "Runtime",
            "metadata": {
                "id": "f5-tts-base",
                "name": "F5-TTS Runtime",
                "provider": "f5-tts",
                "version": "0.1.0",
                "edition": ["ce", "cloud"],
                "labels": {"model_family": "f5-tts"},
            },
            "spec": {
                "runtime_type": "docker",
                "image": {"repository": "peakvox/f5-tts-runtime", "tag": "0.1.0"},
                "service": {"protocol": "http", "port": 8000},
                "capabilities": ["tts", "voice_cloning", "multilingual", "reference_audio"],
                "requirements": {"gpu": "required", "edition": ["ce", "cloud"]},
                "model_binding": {"model_id": "f5-tts-base", "is_default": True},
            },
        }
    )


# ---- HF reference parsing -----------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://huggingface.co/firstpixel/F5-TTS-pt-br", "firstpixel/F5-TTS-pt-br"),
        ("huggingface.co/firstpixel/F5-TTS-pt-br", "firstpixel/F5-TTS-pt-br"),
        ("https://huggingface.co/models/firstpixel/F5-TTS-pt-br", "firstpixel/F5-TTS-pt-br"),
        ("https://huggingface.co/firstpixel/F5-TTS-pt-br/tree/main", "firstpixel/F5-TTS-pt-br"),
        ("firstpixel/F5-TTS-pt-br", "firstpixel/F5-TTS-pt-br"),
    ],
)
def test_parse_hf_reference_accepts_known_forms(raw: str, expected: str) -> None:
    assert parse_hf_reference(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "not a url", "https://example.com/foo/bar", "https://huggingface.co/onlyone"],
)
def test_parse_hf_reference_rejects_bad_input(raw: str) -> None:
    assert parse_hf_reference(raw) is None


def test_derive_variant_id_sanitizes_to_dns_label() -> None:
    assert derive_variant_id("firstpixel/F5-TTS-pt-br") == "f5-tts-pt-br"
    assert derive_variant_id("owner/My_Weird.Model") == "my-weird-model"


# ---- validation gates ---------------------------------------------------------


def test_compatible_candidate_passes_and_is_community_trust() -> None:
    result = validate_variant_import(
        _runtime(),
        VariantImportCandidate(
            source_ref="firstpixel/F5-TTS-pt-br",
            declared_provider="f5-tts",
            declared_capabilities=["tts", "voice_cloning", "multilingual"],
        ),
    )
    assert result.compatible is True
    assert result.trust == "community"
    assert result.proposed_variant_id == "f5-tts-pt-br"
    assert result.reasons == []


def test_rejects_provider_mismatch() -> None:
    result = validate_variant_import(
        _runtime(),
        VariantImportCandidate(
            source_ref="someone/xtts-checkpoint",
            declared_provider="xtts",
            declared_capabilities=["tts"],
        ),
    )
    assert result.compatible is False
    assert any("provider" in r for r in result.reasons)


def test_rejects_capabilities_exceeding_runtime() -> None:
    result = validate_variant_import(
        _runtime(),
        VariantImportCandidate(
            source_ref="someone/f5-singer",
            declared_provider="f5-tts",
            declared_capabilities=["tts", "singing"],  # runtime has no singing
        ),
    )
    assert result.compatible is False
    assert any("singing" in r for r in result.reasons)


def test_rejects_unknown_capability_vocabulary() -> None:
    result = validate_variant_import(
        _runtime(),
        VariantImportCandidate(
            source_ref="someone/telepathic",
            declared_provider="f5-tts",
            declared_capabilities=["tts", "telepathy"],
        ),
    )
    assert result.compatible is False
    assert any("vocabulary" in r for r in result.reasons)


def test_missing_provider_warns_but_does_not_block() -> None:
    result = validate_variant_import(
        _runtime(),
        VariantImportCandidate(
            source_ref="anon/mystery",
            declared_capabilities=["tts"],
        ),
    )
    assert result.compatible is True
    assert any("cannot be verified" in w for w in result.warnings)


def test_family_match_accepted_when_provider_absent() -> None:
    result = validate_variant_import(
        _runtime(),
        VariantImportCandidate(
            source_ref="firstpixel/F5-TTS-pt-br",
            declared_model_family="f5-tts",
            declared_capabilities=["tts"],
        ),
    )
    assert result.compatible is True


def test_unknown_format_warns() -> None:
    result = validate_variant_import(
        _runtime(),
        VariantImportCandidate(
            source_ref="firstpixel/F5-TTS-pt-br",
            declared_provider="f5-tts",
            declared_capabilities=["tts"],
            declared_format="exotic",
        ),
    )
    assert result.compatible is True
    assert any("format" in w for w in result.warnings)
