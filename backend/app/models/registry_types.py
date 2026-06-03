"""Pydantic contracts describing a voice model in the registry.

This module is intentionally dependency-light (no torch / no provider imports) so it can
be imported anywhere — API schemas, the registry, migrations, and tests — without pulling
in the heavy ML runtime. Providers (which import torch/omnivoice) are wired in separately.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

ModelStatus = Literal["available", "loading", "loaded", "error", "disabled"]


class ModelCapabilities(BaseModel):
    """The feature surface a model advertises. Drives capability-gated UI and validation."""

    supports_tts: bool = True
    supports_voice_cloning: bool = False
    supports_emotions: bool = False
    supports_singing: bool = False
    supports_streaming: bool = False
    supports_api: bool = True


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
    status: ModelStatus = "available"
    is_default: bool = False
    is_builtin: bool = True
    editions: list[str] = Field(default_factory=lambda: ["community"])
