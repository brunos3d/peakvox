"""RuntimeRegistry + RuntimeRegistryLoader (Phase 2A, 2A.6).

Per ADR-0017 §2:

- Discovery model: file-based. The loader walks
  ``<registry_root>/<id>/<descriptor>`` and parses each
  descriptor.
- Descriptor loading: parse, validate, register. Malformed
  descriptors are logged and excluded; one bad descriptor does
  not block the rest.
- Indexes: id -> descriptor, model_id -> [id], capability -> [id].
- Lookup: get(id), list(), list_for_model(model_id),
  list_for_capability(capability).
- Path traversal (e.g. a descriptor with '..' in metadata.id) is
  rejected.

For Phase 2A, the on-disk format is JSON (``.json``). YAML is the
canonical format per ADR-0017 §1.1; YAML support is added in
sub-phase 2D when the actual ``runtime-registry/`` directory is
published. The ``RuntimeRegistry`` itself is format-agnostic: it
operates on already-parsed descriptors and on dict-shaped files.

Phase 2A is infrastructure foundation work. No runtime activation,
no Docker integration, no Runtime Service communication.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

from pydantic import ValidationError

from app.services.runtime_types import RuntimeDescriptor

_logger = logging.getLogger(__name__)


class RuntimeRegistry:
    """In-memory index of runtime descriptors (ADR-0017 §2.3).

    Built once at startup (or on hot-reload, future). The registry
    is read-only at runtime; descriptors are file-managed.
    """

    def __init__(self, descriptors: Iterable[RuntimeDescriptor]) -> None:
        self._by_id: dict[str, RuntimeDescriptor] = {}
        self._by_model_id: dict[str, List[str]] = {}
        self._by_capability: dict[str, List[str]] = {}
        for desc in descriptors:
            self._register(desc)

    def _register(self, desc: RuntimeDescriptor) -> None:
        rid = desc.metadata.id
        if rid in self._by_id:
            raise ValueError(f"duplicate runtime id in registry: {rid!r}")
        self._by_id[rid] = desc
        self._by_model_id.setdefault(desc.spec.model_binding.model_id, []).append(rid)
        for cap in desc.spec.capabilities:
            self._by_capability.setdefault(cap, []).append(rid)

    def get(self, runtime_id: str) -> Optional[RuntimeDescriptor]:
        return self._by_id.get(runtime_id)

    def list(self) -> List[RuntimeDescriptor]:
        return list(self._by_id.values())

    def list_for_model(self, model_id: str) -> List[RuntimeDescriptor]:
        return [
            self._by_id[rid] for rid in self._by_model_id.get(model_id, [])
            if rid in self._by_id
        ]

    def list_for_capability(self, capability: str) -> List[RuntimeDescriptor]:
        return [
            self._by_id[rid] for rid in self._by_capability.get(capability, [])
            if rid in self._by_id
        ]

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, runtime_id: object) -> bool:
        return runtime_id in self._by_id


class RuntimeRegistryLoader:
    """File-based descriptor loader (ADR-0017 §2.2).

    Walks a registry root and parses descriptors. For Phase 2A the
    on-disk format is JSON. YAML support is added in sub-phase 2D
    when the actual ``runtime-registry/`` directory is published;
    the loader is format-agnostic — it can be re-targeted by
    adding a YAML parser in 2D.
    """

    _DESCRIPTOR_FILENAME = "descriptor.json"

    def __init__(self, *, descriptor_filename: str = _DESCRIPTOR_FILENAME) -> None:
        self._descriptor_filename = descriptor_filename

    def load_from_directory(self, root: Path) -> RuntimeRegistry:
        if not root.exists():
            _logger.info("runtime registry root %s does not exist; empty registry", root)
            return RuntimeRegistry([])

        descriptors: List[RuntimeDescriptor] = []
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            descriptor_path = child / self._descriptor_filename
            if not descriptor_path.exists():
                # Directory without a descriptor — skip silently.
                continue
            try:
                desc = self._load_one(child, descriptor_path)
            except Exception:
                _logger.warning(
                    "skipping runtime registry entry %s: failed to parse descriptor",
                    child,
                    exc_info=True,
                )
                continue
            if desc is not None:
                descriptors.append(desc)

        return RuntimeRegistry(descriptors)

    def _load_one(
        self, child_dir: Path, descriptor_path: Path
    ) -> Optional[RuntimeDescriptor]:
        try:
            raw = json.loads(descriptor_path.read_text())
        except (OSError, ValueError) as exc:
            _logger.warning(
                "could not read %s: %s", descriptor_path, exc
            )
            return None

        # Path-traversal guard: reject ids that escape the directory.
        metadata = raw.get("metadata") if isinstance(raw, dict) else None
        if not isinstance(metadata, dict):
            _logger.warning(
                "descriptor at %s is missing 'metadata' object; skipping",
                descriptor_path,
            )
            return None
        runtime_id = metadata.get("id")
        if not isinstance(runtime_id, str) or "/" in runtime_id or "\\" in runtime_id:
            _logger.warning(
                "descriptor at %s has invalid id %r; skipping",
                descriptor_path, runtime_id,
            )
            return None

        try:
            return RuntimeDescriptor.model_validate(raw)
        except ValidationError as exc:
            _logger.warning(
                "descriptor at %s failed validation: %s", descriptor_path, exc
            )
            return None
