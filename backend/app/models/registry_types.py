"""Pydantic contracts describing a voice model in the registry.

This module is intentionally dependency-light (no torch / no provider imports) so it can
be imported anywhere — API schemas, the registry, migrations, and tests — without pulling
in the heavy ML runtime. Providers (which import torch/omnivoice) are wired in separately.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field

ModelStatus = Literal[
    "available", "loading", "loaded", "error", "disabled", "inactive", "deprecated"
]


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
    supports_speaker_embeddings: bool = False
    supports_custom_training: bool = False


class ModelRequirements(BaseModel):
    """Runtime needs — drives Cloud capacity planning / VRAM-aware scheduling."""

    min_vram_gb: Optional[float] = None
    gpu_required: bool = False
    runtime: Optional[str] = None  # e.g. "torch", free-form


class ModelLicense(BaseModel):
    """Licensing metadata — relevant to marketplace + commercial-use gating."""

    name: Optional[str] = None
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

    # Edition availability, derived from ``editions`` (ADR-0005/0006). Serialized for the API/UI
    # so the Models page can show per-edition availability without recomputing.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def available_in_ce(self) -> bool:
        return "community" in self.editions

    @computed_field  # type: ignore[prop-decorator]
    @property
    def available_in_cloud(self) -> bool:
        return "cloud" in self.editions

    @computed_field  # type: ignore[prop-decorator]
    @property
    def homepage_url(self) -> Optional[str]:
        return self.provider_metadata.get("homepage_url") or self.provider_metadata.get("homepage")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def repository_url(self) -> Optional[str]:
        return self.provider_metadata.get("repository_url")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def provider_url(self) -> Optional[str]:
        return self.provider_metadata.get("provider_url")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def license_name(self) -> Optional[str]:
        return self.license.name if self.license else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def license_url(self) -> Optional[str]:
        return self.license.url if self.license else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gpu_requirements(self) -> dict:
        return {
            "required": self.requirements.gpu_required,
            "source": self.provider_metadata.get("requirements_source", "unknown"),
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def memory_requirements(self) -> dict:
        return {
            "min_vram_gb": self.requirements.min_vram_gb,
            "source": self.provider_metadata.get("requirements_source", "unknown"),
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def runtime_requirements(self) -> dict:
        return {
            "runtime": self.requirements.runtime,
            "source": self.provider_metadata.get("requirements_source", "unknown"),
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def edition_availability(self) -> dict:
        return {
            "community": self.available_in_ce,
            "cloud": self.available_in_cloud,
            "basis": self.provider_metadata.get("edition_availability_basis", "declared metadata"),
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def install_status(self) -> str:
        if self.status == "disabled":
            return "not_installed"
        if self.status == "loading":
            return "downloading"
        if self.status == "error":
            return "failed"
        return "installed"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def activation_status(self) -> str:
        if self.status in {"available", "loaded", "loading"}:
            return "active"
        return "inactive"
