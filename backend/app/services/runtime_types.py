"""Runtime types (Phase 2A, 2A.1 + 2A.3).

This module contains the descriptor schema (``RuntimeDescriptor``) and
the observability types (``HealthReport``, ``Metrics``) that every
Runtime Service speaks. The descriptor is the contract that
``runtime.yaml`` must satisfy (ADR-0017 §1).

Phase 2A is infrastructure foundation work. This module is dependency-
light (no torch, no Docker SDK, no model frameworks, no YAML parser).
YAML serialization is the registry loader's concern (2A.6); this
module deals in dicts.

Vocabulary
----------

``RUNTIME_CAPABILITY_VOCABULARY`` is the closed set of capability
labels a runtime may declare. Each label maps 1:1 to a boolean field
on ``ModelCapabilities`` (ADR-0003). A runtime's ``spec.capabilities``
must be a subset of the *bound* model's declared capabilities; the
subset check is invoked by the loader (``validate_capabilities_subset_of``).
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import FrozenSet, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.registry_types import ModelCapabilities


# ---- idle-timeout vocabulary (R7) ---------------------------------------------

RUNTIME_IDLE_TIMEOUT_VOCABULARY: FrozenSet[str] = frozenset({
    "never",     # Cloud default; the autoscaler owns lifecycle
    "15m",       # Community Edition default
    "30m",
    "1h",
    "6h",
})


def parse_idle_timeout_to_seconds(value: str) -> Optional[int]:
    """Convert a vocabulary entry to seconds; ``never`` → ``None``.

    Used by the manager's reaper. Returns ``None`` for ``"never"``
    (sentinel: "do not reap"). Raises ``ValueError`` for unknown
    vocabulary entries.
    """
    if value == "never":
        return None
    if value == "15m":
        return 15 * 60
    if value == "30m":
        return 30 * 60
    if value == "1h":
        return 60 * 60
    if value == "6h":
        return 6 * 60 * 60
    raise ValueError(
        f"unknown idle_timeout vocabulary entry: {value!r} "
        f"(expected one of {sorted(RUNTIME_IDLE_TIMEOUT_VOCABULARY)})"
    )


RUNTIME_CAPABILITY_VOCABULARY: FrozenSet[str] = frozenset({
    # Maps 1:1 to ModelCapabilities fields (ADR-0003).
    "tts",                       # supports_tts
    "voice_cloning",             # supports_voice_cloning
    "multilingual",              # supports_multilingual
    "voice_conversion",          # supports_voice_conversion
    "emotion_tags",              # supports_emotion_tags
    "voice_design",              # supports_voice_design
    "reference_audio",           # supports_reference_audio
    "batch_generation",          # supports_batch_generation
    "speaker_embeddings",        # supports_speaker_embeddings
    "custom_training",           # supports_custom_training
    "singing",                   # supports_singing
    "streaming",                 # supports_streaming
    "emotions",                  # supports_emotions (legacy ADR-0003 §2)
})


# ---- observability types (2A.3) -------------------------------------------------

class Liveness(Enum):
    """Liveness probe result (ADR-0017 §6.1)."""

    ALIVE = "alive"
    DEAD = "dead"


class Readiness(Enum):
    """Readiness probe result (ADR-0017 §6.2).

    Readiness must indicate the runtime can actually serve inference
    (model loaded, weights resident, device claimed, no transient
    error). The manager refuses to route to a not-ready instance.
    """

    READY = "ready"
    NOT_READY = "not_ready"
    UNKNOWN = "unknown"


class HealthReport(BaseModel):
    """Liveness + readiness snapshot (ADR-0017 §4.2)."""

    runtime_id: str
    liveness: Liveness
    readiness: Readiness
    last_error: Optional[str]
    checked_at: datetime

    model_config = {"frozen": True}


class Metrics(BaseModel):
    """Runtime metrics placeholder (ADR-0017 §4.2).

    Forward-safe: the first version of any driver may return
    ``Metrics()`` with no counters. Future drivers populate this
    without a schema change.
    """

    model_config = {"frozen": True, "extra": "allow"}


# ---- descriptor schema (2A.1) ---------------------------------------------------

_DNS_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9\-.]*[a-z0-9]$")
_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class RuntimeImage(BaseModel):
    """spec.image: OCI image identity (ADR-0017 §1.1).

    Always present, always used by ``RuntimeManager``. The
    ``Repository`` + ``tag`` + optional ``digest`` form the
    immutable image identity. The ``digest`` is set by the
    registry loader / build script when the image is built
    locally; in production paths, the digest is the pin.
    """

    repository: str = Field(..., min_length=1)
    tag: str = Field(..., min_length=1)
    digest: Optional[str] = None
    image_size_mb: Optional[float] = Field(default=None, gt=0)

    @field_validator("digest")
    @classmethod
    def _validate_digest(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not _SHA256_DIGEST_RE.match(v):
            raise ValueError(
                "spec.image.digest, when present, must match 'sha256:[0-9a-f]{64}'"
            )
        return v


class RuntimeBuild(BaseModel):
    """spec.build: local-build metadata (R2 — CE-only).

    Optional. When present, the descriptor carries the source
    required to build the OCI image it describes (CE flow). When
    absent, the image is presumed to be prebuilt in a registry
    (Cloud flow).

    ``RuntimeManager`` **never reads this block**; the manager is
    image-agnostic. The build script / registry loader is the
    only consumer.
    """

    entrypoint: str = Field(..., min_length=1)
    build_context: str = Field(..., min_length=1)
    dockerfile: str = "Dockerfile"

    @field_validator("entrypoint")
    @classmethod
    def _validate_entrypoint_is_relative(cls, v: str) -> str:
        if v.startswith("/") or v.startswith("\\"):
            raise ValueError(
                "spec.build.entrypoint must be a path relative to the build context"
            )
        return v

    @field_validator("build_context")
    @classmethod
    def _validate_build_context_is_relative(cls, v: str) -> str:
        if v.startswith("/") or v.startswith("\\"):
            raise ValueError(
                "spec.build.build_context must be a path relative to the descriptor's directory"
            )
        return v


class RuntimeService(BaseModel):
    """spec.service: Runtime Service Contract endpoint set (ADR-0017 §1.1 / §6)."""

    protocol: Literal["http", "grpc"] = "http"
    port: int = Field(..., ge=1, le=65535)
    health_path: str = "/health"
    readiness_path: str = "/ready"
    generate_path: str = "/v1/generate"
    build_path: str = "/v1/variants/build"
    metadata_path: str = "/v1/metadata"


class RuntimeRequirements(BaseModel):
    """spec.requirements: host-side requirements (ADR-0017 §1.1 / §1.6)."""

    gpu: Literal["required", "optional", "none"] = "optional"
    min_vram_gb: Optional[int] = Field(default=None, ge=0)
    cpu_cores: Optional[int] = Field(default=None, ge=0)
    memory_gb: Optional[int] = Field(default=None, ge=0)
    edition: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_edition_nonempty(self) -> "RuntimeRequirements":
        if not self.edition:
            raise ValueError("spec.requirements.edition must be non-empty")
        for ed in self.edition:
            if ed not in {"ce", "cloud"}:
                raise ValueError(
                    f"spec.requirements.edition contains unknown edition '{ed}'"
                )
        return self


class RuntimeModelBinding(BaseModel):
    """spec.model_binding: maps this runtime to a logical Model (ADR-0017 §1.1)."""

    model_id: str = Field(..., min_length=1)
    is_default: bool = False
    priority: int = Field(default=100, ge=0)


class RuntimeLifecycle(BaseModel):
    """spec.lifecycle: install/update/health/idle policy (ADR-0017 §1.1, R7).

    ``idle_timeout`` is the new field (R7) — the manager
    auto-stops the runtime container after this many seconds of
    inactivity since the last ``resolve()``. The default is
    ``"15m"`` (CE); Cloud operators may set ``"never"`` and let
    the autoscaler own lifecycle.
    """

    install_policy: Literal["pull-on-start", "pull-on-install", "lazy"] = "pull-on-start"
    health_interval_seconds: int = Field(default=10, gt=0)
    health_timeout_seconds: int = Field(default=3, gt=0)
    start_timeout_seconds: int = Field(default=60, gt=0)
    restart_policy: Literal["on-failure", "always", "never"] = "on-failure"
    idle_timeout: str = Field(default="15m")

    @field_validator("idle_timeout")
    @classmethod
    def _validate_idle_timeout_vocabulary(cls, v: str) -> str:
        if v not in RUNTIME_IDLE_TIMEOUT_VOCABULARY:
            raise ValueError(
                f"spec.lifecycle.idle_timeout must be one of "
                f"{sorted(RUNTIME_IDLE_TIMEOUT_VOCABULARY)}; got {v!r}"
            )
        return v


class RuntimeMetadata(BaseModel):
    """metadata: identity + human-readable info (ADR-0017 §1.1)."""

    id: str = Field(..., min_length=1, max_length=63)
    name: str = Field(..., min_length=1)
    description: str = ""
    provider: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    edition: List[str] = Field(..., min_length=1)
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _validate_id_is_dns_label(cls, v: str) -> str:
        if len(v) > 63:
            raise ValueError("metadata.id must be ≤ 63 characters")
        if not _DNS_LABEL_RE.match(v):
            raise ValueError(
                "metadata.id must be a DNS-label (lowercase alphanumeric, '-', '.', "
                "starting and ending with alphanumeric)"
            )
        return v

    @field_validator("edition")
    @classmethod
    def _validate_edition_known(cls, v: List[str]) -> List[str]:
        for ed in v:
            if ed not in {"ce", "cloud"}:
                raise ValueError(f"metadata.edition contains unknown edition '{ed}'")
        return v


class RuntimeDescriptor(BaseModel):
    """The runtime.yaml contract (ADR-0017 §1).

    Validated against a closed schema. Capability subset checks
    against a bound model are performed by the caller via
    :meth:`validate_capabilities_subset_of` (the descriptor does not
    know which model it is bound to at load time).
    """

    api_version: Literal["peakvox.io/v1"] = "peakvox.io/v1"
    kind: Literal["Runtime"] = "Runtime"
    metadata: RuntimeMetadata
    spec: "RuntimeDescriptorSpec"

    @field_validator("api_version")
    @classmethod
    def _check_api_version(cls, v: str) -> str:
        # Literal already enforces this; the explicit check exists so the
        # error message is meaningful and the constraint is visible.
        if v != "peakvox.io/v1":
            raise ValueError(f"unsupported api_version: {v!r}")
        return v

    @model_validator(mode="after")
    def _check_requirements_edition_subset(self) -> "RuntimeDescriptor":
        req_ed = set(self.spec.requirements.edition)
        meta_ed = set(self.metadata.edition)
        if not req_ed.issubset(meta_ed):
            missing = sorted(req_ed - meta_ed)
            raise ValueError(
                f"spec.requirements.edition ({sorted(req_ed)}) must be a subset of "
                f"metadata.edition ({sorted(meta_ed)}); missing: {missing}"
            )
        return self

    def validate_capabilities_subset_of(self, model_caps: ModelCapabilities) -> None:
        """Raise ValueError if any declared capability is unsupported by the model.

        The mapping is explicit (no implicit defaults) — every declared
        capability must have an explicit ``True`` on the bound
        :class:`ModelCapabilities`. Per ADR-0017 §1.5: the runtime
        cannot exceed the model.
        """
        mapping: dict[str, bool] = {
            "tts": model_caps.supports_tts,
            "voice_cloning": model_caps.supports_voice_cloning,
            "multilingual": model_caps.supports_multilingual,
            "voice_conversion": model_caps.supports_voice_conversion,
            "emotion_tags": model_caps.supports_emotion_tags,
            "voice_design": model_caps.supports_voice_design,
            "reference_audio": model_caps.supports_reference_audio,
            "batch_generation": model_caps.supports_batch_generation,
            "speaker_embeddings": model_caps.supports_speaker_embeddings,
            "custom_training": model_caps.supports_custom_training,
            "singing": model_caps.supports_singing,
            "streaming": model_caps.supports_streaming,
            "emotions": model_caps.supports_emotions,
        }
        unsupported = sorted(
            cap for cap in self.spec.capabilities if not mapping.get(cap, False)
        )
        if unsupported:
            raise ValueError(
                f"Runtime {self.metadata.id!r} declares capabilities not supported by "
                f"bound model {self.spec.model_binding.model_id!r}: {unsupported}"
            )


class RuntimeDescriptorSpec(BaseModel):
    """spec: behavior (image, build, service, capabilities, requirements, ...).

    R2 added ``build`` (optional; CE-only). The manager never reads
    it; the registry loader / build script does.
    """

    runtime_type: Literal["docker"] = "docker"  # first version
    image: RuntimeImage
    build: Optional[RuntimeBuild] = None
    service: RuntimeService
    capabilities: List[str] = Field(default_factory=list)
    requirements: RuntimeRequirements
    model_binding: RuntimeModelBinding
    lifecycle: RuntimeLifecycle = Field(default_factory=RuntimeLifecycle)

    @field_validator("capabilities")
    @classmethod
    def _validate_capabilities_vocabulary(cls, v: List[str]) -> List[str]:
        unknown = [c for c in v if c not in RUNTIME_CAPABILITY_VOCABULARY]
        if unknown:
            raise ValueError(
                f"spec.capabilities contains unknown entries (not in the closed "
                f"vocabulary): {unknown}"
            )
        return v


# Forward reference resolution — RuntimeDescriptor references RuntimeDescriptorSpec.
RuntimeDescriptor.model_rebuild()
