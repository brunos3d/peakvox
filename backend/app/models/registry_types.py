"""Pydantic contracts describing a voice model in the registry.

This module is intentionally dependency-light (no torch / no provider imports) so it can
be imported anywhere — API schemas, the registry, migrations, and tests — without pulling
in the heavy ML runtime. Providers (which import torch/omnivoice) are wired in separately.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

ModelStatus = Literal["available", "loading", "loaded", "error", "disabled"]


class ModelCapabilities(BaseModel):
    """The feature surface a model advertises (ADR-0003, the Model Capability Contract).

    Declared, never inferred. The Runtime, API, UI, and Marketplace all read this one contract;
    no code branches on model id/name. New capabilities are additive and default to ``False``
    (forward-compatible); unknown fields from a newer model are ignored by older readers.
    """

    # Contract version — bumped when capabilities are added (additive only).
    capability_version: int = 1

    # Legacy v1 subset (kept for back-compat).
    supports_tts: bool = True
    supports_voice_cloning: bool = False
    supports_emotions: bool = False
    supports_singing: bool = False
    supports_streaming: bool = False
    supports_api: bool = True

    # ADR-0003 superset (additive; safe default = unsupported).
    supports_voice_conversion: bool = False
    supports_emotion_tags: bool = False
    supports_voice_design: bool = False
    supports_multilingual: bool = False
    supports_reference_audio: bool = False
    supports_batch_generation: bool = False


class ModelRequirements(BaseModel):
    """Runtime needs — drives Cloud capacity planning / VRAM-aware scheduling."""

    min_vram_gb: Optional[float] = None
    gpu_required: bool = False
    runtime: Optional[str] = None  # e.g. "torch", free-form


class ModelLicense(BaseModel):
    """Licensing metadata — relevant to marketplace + commercial-use gating."""

    code: Optional[str] = None        # e.g. "apache-2.0"
    weights_license: Optional[str] = None
    commercial_use: Optional[bool] = None
    url: Optional[str] = None


class ModelDescriptor(BaseModel):
    """Everything the platform needs to know about a model, independent of how it loads.

    The ``provider`` names a registered :class:`ModelProvider` implementation that knows how
    to load and run this model. ``repo_id``/``model_path`` are the load coordinates.
    """

    id: str
    name: str
    description: str
    version: str = "1.0.0"
    provider: str
    repo_id: Optional[str] = None
    model_path: Optional[str] = None
    supported_languages: list[str] = Field(default_factory=list)
    supported_tags: list[str] = Field(default_factory=list)
    supported_voice_design: list[str] = Field(default_factory=list)
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    requirements: ModelRequirements = Field(default_factory=ModelRequirements)
    license: Optional[ModelLicense] = None
    provider_metadata: dict = Field(default_factory=dict)
    status: ModelStatus = "available"
    is_default: bool = False
    is_builtin: bool = True
    editions: list[str] = Field(default_factory=lambda: ["community"])
