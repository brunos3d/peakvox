"""RuntimeVariant import — validation foundation (ADR-0018 Phase 6; Task 27 D/G/H).

A *community model import* lets a user attach a third-party checkpoint (e.g. a
Hugging Face repo such as ``firstpixel/F5-TTS-pt-br``) to an **existing**
runtime as a new :class:`RuntimeVariantDescriptor` — with **no new Docker image,
no new runtime folder, no rebuild**. The full flow is::

    Add Variant → paste HF URL → VALIDATE → download → register → use

This module implements only the **VALIDATE** gate, and only the part that needs
no network: given a target runtime descriptor and a *declared* candidate, decide
whether the checkpoint is compatible with the runtime. Download + register are a
later phase; keeping validation pure and side-effect-free makes it unit-testable
and safe to ship now.

Design rules carried from the architecture:

* **Compatibility is declared and checked, never inferred from a repo name**
  (ADR-0003 applied to checkpoints). A repo *called* ``F5-TTS-pt-br`` proves
  nothing; the candidate must *declare* its provider/family/capabilities and we
  check those. What cannot be declared is surfaced as a *warning*, not a silent
  pass.
* **A variant may not exceed its runtime's capabilities** — mirrors
  ``RuntimeDescriptor.validate_capabilities_subset_of`` (ADR-0017 §1.5).
* **Imported variants are ``community`` trust** (Task 27 Phase H): compatibility
  is checked but never provider-validated by PeakVox.
* **No model internals leak** (ADR-0004 §6): this module deals in providers,
  families, and capability labels — never embedding/checkpoint formats on a
  public surface (the format stays internal to the descriptor).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional
from urllib.parse import urlparse

from app.services.runtime_types import (
    RUNTIME_CAPABILITY_VOCABULARY,
    RuntimeDescriptor,
)

# Recognized checkpoint container formats. Unknown formats are a warning, not a
# hard reject — the runtime service is the final authority on what it can load.
KNOWN_CHECKPOINT_FORMATS: frozenset[str] = frozenset(
    {"safetensors", "pytorch", "bin", "ckpt", "gguf", "onnx"}
)

_HF_REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
_DNS_LABEL_SANITIZE_RE = re.compile(r"[^a-z0-9-]+")


def parse_hf_reference(raw: str) -> Optional[str]:
    """Parse a Hugging Face reference into a canonical ``owner/name`` repo id.

    Accepts ``https://huggingface.co/owner/name`` (optionally with a trailing
    path/anchor), ``huggingface.co/owner/name``, or a bare ``owner/name`` repo
    id. Returns ``None`` for anything that is not a recognizable HF repo
    reference. Never hits the network.
    """
    if not raw or not raw.strip():
        return None
    text = raw.strip()

    if "huggingface.co" in text:
        if "://" not in text:
            text = "https://" + text
        parsed = urlparse(text)
        if parsed.netloc.lower() not in {"huggingface.co", "www.huggingface.co"}:
            return None
        parts = [p for p in parsed.path.split("/") if p]
        # Strip the optional "models" segment HF sometimes includes.
        if parts and parts[0] == "models":
            parts = parts[1:]
        if len(parts) < 2:
            return None
        repo = f"{parts[0]}/{parts[1]}"
    else:
        repo = text

    return repo if _HF_REPO_RE.match(repo) else None


def derive_variant_id(repo_id: str) -> str:
    """Derive a DNS-label variant id from an HF repo id (best-effort).

    ``firstpixel/F5-TTS-pt-br`` → ``f5-tts-pt-br``. The result is a valid
    ``metadata.id`` (lowercase alphanumeric + ``-``, trimmed). Collisions with
    an existing variant id are the caller's concern (the registry rejects
    duplicates).
    """
    name = repo_id.split("/", 1)[-1].lower()
    slug = _DNS_LABEL_SANITIZE_RE.sub("-", name).strip("-")
    return slug or "imported"


@dataclass(frozen=True)
class VariantImportCandidate:
    """A *declared* checkpoint a user wants to attach to a runtime.

    Everything except ``source_ref`` is what the user (or, later, an automated
    Hugging Face metadata probe) *declares*. We validate the declaration; we do
    not trust the repo name. ``declared_provider``/``declared_model_family`` are
    optional because not every repo exposes them — a missing declaration becomes
    a warning ("cannot verify"), never a silent compatibility pass.
    """

    source_ref: str
    source_type: Literal["hf", "url", "local"] = "hf"
    declared_provider: Optional[str] = None
    declared_model_family: Optional[str] = None
    declared_capabilities: List[str] = field(default_factory=list)
    declared_format: str = "safetensors"
    requested_variant_id: Optional[str] = None


@dataclass(frozen=True)
class VariantImportValidation:
    """The result of validating a candidate against a runtime.

    ``compatible`` is the go/no-go. ``reasons`` are hard blockers (non-empty ⇔
    incompatible). ``warnings`` are things the user should know but that do not
    block (e.g. provider not declared → unverified). ``proposed_variant_id`` and
    ``trust`` describe the descriptor that *would* be written on accept.
    """

    compatible: bool
    runtime_id: str
    proposed_variant_id: str
    trust: Literal["verified", "community"]
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_variant_import(
    runtime: RuntimeDescriptor,
    candidate: VariantImportCandidate,
) -> VariantImportValidation:
    """Validate a community checkpoint against a target runtime (no network).

    Gates (all *declared-and-checked*, never inferred from the repo name):

    1. **Capability vocabulary** — declared capabilities must be in the closed
       runtime vocabulary (ADR-0003). Unknown → reject.
    2. **Capability ceiling** — declared capabilities must be a subset of the
       runtime's own capabilities; a variant cannot exceed its runtime
       (ADR-0017 §1.5). Exceeds → reject.
    3. **Provider/family match** — if declared, must match the runtime's
       ``provider`` or ``model_family`` label; mismatch → reject. If *not*
       declared → warning (compatibility unverified), not a reject.
    4. **Format** — unknown container format → warning (the runtime service is
       the final authority on loadability).

    Imported variants are always ``community`` trust.
    """
    runtime_id = runtime.metadata.id
    reasons: List[str] = []
    warnings: List[str] = []

    # Gate 1 — vocabulary.
    unknown_caps = [
        c for c in candidate.declared_capabilities
        if c not in RUNTIME_CAPABILITY_VOCABULARY
    ]
    if unknown_caps:
        reasons.append(
            f"declares capabilities outside the closed vocabulary: {sorted(unknown_caps)}"
        )

    # Gate 2 — capability ceiling (only the known ones; unknown already flagged).
    runtime_caps = set(runtime.spec.capabilities)
    exceeding = [
        c for c in candidate.declared_capabilities
        if c in RUNTIME_CAPABILITY_VOCABULARY and c not in runtime_caps
    ]
    if exceeding:
        reasons.append(
            f"declares capabilities the runtime {runtime_id!r} does not provide: "
            f"{sorted(exceeding)} (a variant cannot exceed its runtime)"
        )

    # Gate 3 — provider / family match.
    runtime_provider = runtime.metadata.provider.lower()
    runtime_family = str(runtime.metadata.labels.get("model_family", "")).lower()
    declared_provider = (candidate.declared_provider or "").lower()
    declared_family = (candidate.declared_model_family or "").lower()

    if declared_provider:
        if declared_provider != runtime_provider and declared_provider != runtime_family:
            reasons.append(
                f"declared provider {candidate.declared_provider!r} does not match "
                f"runtime provider {runtime.metadata.provider!r}"
            )
    elif declared_family:
        if runtime_family and declared_family != runtime_family:
            reasons.append(
                f"declared model family {candidate.declared_model_family!r} does not "
                f"match runtime family {runtime_family!r}"
            )
    else:
        warnings.append(
            "no provider/model-family declared — compatibility with this runtime "
            "cannot be verified; import as community/unverified at your own risk"
        )

    # Gate 4 — format.
    if candidate.declared_format.lower() not in KNOWN_CHECKPOINT_FORMATS:
        warnings.append(
            f"unrecognized checkpoint format {candidate.declared_format!r}; the "
            f"runtime service will decide whether it can be loaded"
        )

    if not candidate.declared_capabilities:
        warnings.append(
            "no capabilities declared — the variant will advertise none until "
            "they are declared and verified"
        )

    proposed_id = candidate.requested_variant_id or derive_variant_id(candidate.source_ref)

    return VariantImportValidation(
        compatible=not reasons,
        runtime_id=runtime_id,
        proposed_variant_id=proposed_id,
        trust="community",
        reasons=reasons,
        warnings=warnings,
    )
