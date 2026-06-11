"""TDD: RuntimeVariant descriptor + registry/loader support (ADR-0018, Phase 0).

A RuntimeVariant is an INFRASTRUCTURE descriptor concept (ADR-0018), parallel
to RuntimeDescriptor — it binds a checkpoint to a Runtime. It is NOT a domain
entity and must never be confused with the domain ``VoiceVariant``
(Voice × Model; ADR-0001/0004/0008/0009).

These tests pin the Phase 0 guarantees:
  - the schema validates good variants and rejects malformed ones,
  - the loader reads ``<runtime>/variants/*.json`` additively,
  - a registry with NO ``variants/`` folder behaves identically to before
    (single-``base`` runtime; zero explicit variants),
  - one bad variant file is skipped-and-logged and never blocks the runtime.

Nothing here wires variants into resolution or lifecycle — that is migration
Phase 1+. The primitive exists to be wired later.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services.runtime_registry import RuntimeRegistry, RuntimeRegistryLoader
from app.services.runtime_types import (
    RuntimeDescriptor,
    RuntimeVariantDescriptor,
)


# ---- fixtures -----------------------------------------------------------------


def _runtime_dict(runtime_id: str = "f5-tts", model_id: str = "f5-tts-base") -> dict:
    return {
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": runtime_id,
            "name": "F5-TTS Runtime",
            "description": "",
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
            "model_binding": {"model_id": model_id, "is_default": True, "priority": 100},
        },
    }


def _variant_dict(
    *,
    variant_id: str = "pt-br",
    runtime_id: str = "f5-tts",
    model_id: str = "f5-tts-pt-br",
    is_default: bool = False,
) -> dict:
    return {
        "api_version": "peakvox.io/v1",
        "kind": "RuntimeVariant",
        "metadata": {
            "id": variant_id,
            "name": f"F5-TTS {variant_id}",
            "runtime_id": runtime_id,
            "description": "",
            "labels": {},
        },
        "spec": {
            "model_binding": {"model_id": model_id, "is_default": is_default, "priority": 100},
            "checkpoint": {
                "source_type": "hf",
                "source_ref": "firstpixel/F5-TTS-pt-br",
                "format": "safetensors",
            },
            "is_default": is_default,
            "capabilities": ["tts", "voice_cloning", "multilingual"],
        },
    }


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


# ---- schema -------------------------------------------------------------------


def test_variant_descriptor_validates_good_payload() -> None:
    v = RuntimeVariantDescriptor.model_validate(_variant_dict())
    assert v.kind == "RuntimeVariant"
    assert v.metadata.id == "pt-br"
    assert v.metadata.runtime_id == "f5-tts"
    assert v.spec.model_binding.model_id == "f5-tts-pt-br"
    assert v.spec.checkpoint.source_type == "hf"
    assert v.spec.checkpoint.source_ref == "firstpixel/F5-TTS-pt-br"


def test_variant_descriptor_rejects_wrong_kind() -> None:
    bad = _variant_dict()
    bad["kind"] = "Runtime"
    with pytest.raises(ValidationError):
        RuntimeVariantDescriptor.model_validate(bad)


def test_variant_descriptor_requires_runtime_id() -> None:
    bad = _variant_dict()
    del bad["metadata"]["runtime_id"]
    with pytest.raises(ValidationError):
        RuntimeVariantDescriptor.model_validate(bad)


def test_variant_descriptor_rejects_unknown_capability() -> None:
    bad = _variant_dict()
    bad["spec"]["capabilities"] = ["tts", "telepathy"]
    with pytest.raises(ValidationError):
        RuntimeVariantDescriptor.model_validate(bad)


def test_variant_descriptor_rejects_bad_checkpoint_digest() -> None:
    bad = _variant_dict()
    bad["spec"]["checkpoint"]["digest"] = "not-a-sha"
    with pytest.raises(ValidationError):
        RuntimeVariantDescriptor.model_validate(bad)


def test_variant_descriptor_rejects_unknown_edition() -> None:
    bad = _variant_dict()
    bad["spec"]["edition"] = ["enterprise"]
    with pytest.raises(ValidationError):
        RuntimeVariantDescriptor.model_validate(bad)


# ---- registry index -----------------------------------------------------------


def test_registry_indexes_variants_by_runtime() -> None:
    desc = RuntimeDescriptor.model_validate(_runtime_dict())
    base = RuntimeVariantDescriptor.model_validate(
        _variant_dict(variant_id="base", model_id="f5-tts-base", is_default=True)
    )
    ptbr = RuntimeVariantDescriptor.model_validate(_variant_dict())
    reg = RuntimeRegistry([desc], [base, ptbr])

    got = {v.metadata.id for v in reg.list_variants_for_runtime("f5-tts")}
    assert got == {"base", "pt-br"}
    assert reg.get_variant("f5-tts", "pt-br") is ptbr
    assert reg.get_variant("f5-tts", "missing") is None


def test_registry_rejects_duplicate_variant_id_for_runtime() -> None:
    v1 = RuntimeVariantDescriptor.model_validate(_variant_dict())
    v2 = RuntimeVariantDescriptor.model_validate(_variant_dict())
    with pytest.raises(ValueError):
        RuntimeRegistry([], [v1, v2])


def test_registry_without_variants_has_empty_variant_list() -> None:
    desc = RuntimeDescriptor.model_validate(_runtime_dict())
    reg = RuntimeRegistry([desc])
    assert reg.list_variants_for_runtime("f5-tts") == []


# ---- loader -------------------------------------------------------------------


def test_loader_reads_variants_subdirectory(tmp_path: Path) -> None:
    rt = tmp_path / "f5-tts"
    _write(rt / "descriptor.json", _runtime_dict())
    _write(rt / "variants" / "base.json",
           _variant_dict(variant_id="base", model_id="f5-tts-base", is_default=True))
    _write(rt / "variants" / "pt-br.json", _variant_dict())

    reg = RuntimeRegistryLoader().load_from_directory(tmp_path)

    assert reg.get("f5-tts") is not None
    got = {v.metadata.id for v in reg.list_variants_for_runtime("f5-tts")}
    assert got == {"base", "pt-br"}


def test_loader_runtime_without_variants_dir_is_unchanged(tmp_path: Path) -> None:
    rt = tmp_path / "f5-tts"
    _write(rt / "descriptor.json", _runtime_dict())

    reg = RuntimeRegistryLoader().load_from_directory(tmp_path)

    assert reg.get("f5-tts") is not None
    assert reg.list_variants_for_runtime("f5-tts") == []


def test_loader_skips_bad_variant_but_keeps_runtime_and_good_variants(
    tmp_path: Path, caplog
) -> None:
    rt = tmp_path / "f5-tts"
    _write(rt / "descriptor.json", _runtime_dict())
    _write(rt / "variants" / "good.json",
           _variant_dict(variant_id="good", model_id="f5-tts-base"))
    # malformed JSON
    (rt / "variants" / "broken.json").write_text("{ not json")
    # wrong kind
    bad_kind = _variant_dict(variant_id="badkind")
    bad_kind["kind"] = "Runtime"
    _write(rt / "variants" / "badkind.json", bad_kind)

    reg = RuntimeRegistryLoader().load_from_directory(tmp_path)

    # runtime survives; only the good variant is registered
    assert reg.get("f5-tts") is not None
    got = {v.metadata.id for v in reg.list_variants_for_runtime("f5-tts")}
    assert got == {"good"}


def test_loader_skips_variant_with_mismatched_runtime_id(tmp_path: Path) -> None:
    rt = tmp_path / "f5-tts"
    _write(rt / "descriptor.json", _runtime_dict())
    # variant claims to belong to a different runtime than the directory it lives in
    _write(rt / "variants" / "stray.json",
           _variant_dict(variant_id="stray", runtime_id="omnivoice"))

    reg = RuntimeRegistryLoader().load_from_directory(tmp_path)

    assert reg.list_variants_for_runtime("f5-tts") == []
    assert reg.list_variants_for_runtime("omnivoice") == []
