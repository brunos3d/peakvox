"""TDD: RuntimeRegistryLoader (2A.6).

Per ADR-0017 §2:

- Discovery model: file-based. The loader walks
  ``<registry_root>/<id>/<descriptor>`` and parses each descriptor.
- Descriptor loading: parse, validate, register. Malformed
  descriptors are logged and excluded; one bad descriptor does
  not block the rest.
- Indexes: id -> descriptor, model_id -> [id], capability -> [id].
- Lookup: get(id), list(), list_for_model(model_id),
  list_for_capability(capability).
- Path traversal (e.g. a descriptor with '..' in metadata.id) is
  rejected.

For Phase 2A, the descriptor is read from a dict-shaped format
(JSON). YAML support is added in sub-phase 2D when the actual
``runtime-registry/`` directory is published. The registry class
itself is format-agnostic: it operates on already-parsed
descriptors and on dict-shaped files on disk.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import pytest

from app.services.runtime_registry import RuntimeRegistry, RuntimeRegistryLoader
from app.services.runtime_types import RuntimeDescriptor


def _good_dict() -> dict:
    return {
        "api_version": "peakvox.io/v1",
        "kind": "Runtime",
        "metadata": {
            "id": "kokoro-cpu",
            "name": "Kokoro CPU",
            "description": "",
            "provider": "kokoro",
            "version": "1.4.2",
            "edition": ["ce"],
            "labels": {},
        },
        "spec": {
            "runtime_type": "docker",
            "image": {"repository": "peakvox/kokoro-runtime", "tag": "1.4.2"},
            "service": {"protocol": "http", "port": 8000},
            "capabilities": ["tts"],
            "requirements": {"gpu": "none", "edition": ["ce"]},
            "model_binding": {"model_id": "kokoro-base", "is_default": True, "priority": 100},
        },
    }


def test_registry_accepts_parsed_descriptors_directly(tmp_path: Path) -> None:
    desc = RuntimeDescriptor.model_validate(_good_dict())
    reg = RuntimeRegistry([desc])
    assert reg.get("kokoro-cpu") is desc
    assert reg.list() == [desc]


def test_registry_list_for_model_returns_matching_runtimes() -> None:
    d1 = RuntimeDescriptor.model_validate(_good_dict())
    d2_dict = _good_dict()
    d2_dict["metadata"]["id"] = "f5-tts-cpu"
    d2_dict["metadata"]["provider"] = "f5-tts"
    d2_dict["spec"]["model_binding"]["model_id"] = "f5-tts-base"
    d2 = RuntimeDescriptor.model_validate(d2_dict)
    reg = RuntimeRegistry([d1, d2])
    assert {r.metadata.id for r in reg.list_for_model("kokoro-base")} == {"kokoro-cpu"}
    assert {r.metadata.id for r in reg.list_for_model("f5-tts-base")} == {"f5-tts-cpu"}


def test_registry_list_for_capability_returns_matching_runtimes() -> None:
    d1 = RuntimeDescriptor.model_validate(_good_dict())
    d2_dict = _good_dict()
    d2_dict["metadata"]["id"] = "kokoro-cuda"
    d2_dict["spec"]["capabilities"] = ["tts", "multilingual"]
    d2 = RuntimeDescriptor.model_validate(d2_dict)
    reg = RuntimeRegistry([d1, d2])
    assert {r.metadata.id for r in reg.list_for_capability("multilingual")} == {"kokoro-cuda"}


def test_registry_get_returns_none_for_unknown_id() -> None:
    reg = RuntimeRegistry([])
    assert reg.get("missing") is None


def test_empty_registry_is_valid() -> None:
    reg = RuntimeRegistry([])
    assert reg.list() == []
    assert reg.list_for_model("any") == []
    assert reg.list_for_capability("any") == []


def test_loader_walks_directory_and_loads_json_descriptors(tmp_path: Path) -> None:
    # Layout: <root>/<id>/descriptor.json
    d1_dir = tmp_path / "kokoro-cpu"
    d1_dir.mkdir()
    (d1_dir / "descriptor.json").write_text(json.dumps(_good_dict()))

    d2_dict = _good_dict()
    d2_dict["metadata"]["id"] = "f5-tts-cpu"
    d2_dict["metadata"]["provider"] = "f5-tts"
    d2_dict["spec"]["model_binding"]["model_id"] = "f5-tts-base"
    d2_dir = tmp_path / "f5-tts-cpu"
    d2_dir.mkdir()
    (d2_dir / "descriptor.json").write_text(json.dumps(d2_dict))

    loader = RuntimeRegistryLoader()
    reg = loader.load_from_directory(tmp_path)
    assert {r.metadata.id for r in reg.list()} == {"kokoro-cpu", "f5-tts-cpu"}


def test_loader_skips_malformed_descriptors(tmp_path: Path, caplog) -> None:
    good_dir = tmp_path / "kokoro-cpu"
    good_dir.mkdir()
    (good_dir / "descriptor.json").write_text(json.dumps(_good_dict()))

    bad_dir = tmp_path / "broken"
    bad_dir.mkdir()
    (bad_dir / "descriptor.json").write_text("{ this is not valid json")

    loader = RuntimeRegistryLoader()
    with caplog.at_level(logging.WARNING, logger="app.services.runtime_registry"):
        reg = loader.load_from_directory(tmp_path)
    assert {r.metadata.id for r in reg.list()} == {"kokoro-cpu"}
    assert any("broken" in rec.message for rec in caplog.records)


def test_loader_skips_directories_with_no_descriptor(tmp_path: Path) -> None:
    good_dir = tmp_path / "kokoro-cpu"
    good_dir.mkdir()
    (good_dir / "descriptor.json").write_text(json.dumps(_good_dict()))

    empty_dir = tmp_path / "no-descriptor-here"
    empty_dir.mkdir()
    (empty_dir / "README.md").write_text("not a descriptor")

    loader = RuntimeRegistryLoader()
    reg = loader.load_from_directory(tmp_path)
    assert {r.metadata.id for r in reg.list()} == {"kokoro-cpu"}


def test_loader_rejects_path_traversal_id(tmp_path: Path) -> None:
    # The path-traversal guard is in the descriptor's id (the metadata.id
    # field), not in the directory name on disk. A descriptor with an
    # id containing '/' or '\' is rejected at parse time.
    bad_dir = tmp_path / "bad-id"
    bad_dir.mkdir()
    bad_dict = _good_dict()
    bad_dict["metadata"]["id"] = "../etc/passwd"
    (bad_dir / "descriptor.json").write_text(json.dumps(bad_dict))

    loader = RuntimeRegistryLoader()
    reg = loader.load_from_directory(tmp_path)
    assert reg.list() == []


def test_loader_rejects_descriptor_with_slash_in_id(tmp_path: Path) -> None:
    bad_dir = tmp_path / "bad-id-2"
    bad_dir.mkdir()
    bad_dict = _good_dict()
    bad_dict["metadata"]["id"] = "nested/inner"
    (bad_dir / "descriptor.json").write_text(json.dumps(bad_dict))

    loader = RuntimeRegistryLoader()
    reg = loader.load_from_directory(tmp_path)
    assert reg.list() == []


def test_loader_accepts_empty_directory() -> None:
    loader = RuntimeRegistryLoader()
    reg = loader.load_from_directory(Path("/tmp/empty-runtime-registry-2A6-xyz"))
    assert reg.list() == []


def test_loader_accepts_missing_directory() -> None:
    loader = RuntimeRegistryLoader()
    # Missing path is treated as empty (not an error at 2A; the
    # registry root is configurable and may be unset in 2A).
    reg = loader.load_from_directory(Path("/tmp/does-not-exist-2A6-xyz"))
    assert reg.list() == []
