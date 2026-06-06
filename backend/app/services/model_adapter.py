"""The ModelAdapter contract — the single seam between the Runtime and a model.

Everything above this line (Runtime, API, UI, marketplace) is model-agnostic; everything below
(provider/engine/weights) is model-specific. The Runtime interacts *only* with adapters, never
with a model implementation (ADR-0004, Runtime §6). Adding a model = writing an adapter.

The data methods (capabilities/languages/tags) are concrete and torch-free — they read the
declared :class:`ModelDescriptor`. The runtime/lifecycle methods are abstract; concrete
adapters import heavy runtimes lazily so this module stays import-safe without a GPU stack.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.services.realization import DEFAULT_REALIZATION

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.db import Voice, VoiceVariant


@dataclass(frozen=True)
class VariantBuildStrategy:
    """Declares that an adapter can build variants for voices of a given creation source.

    Used by :class:`CompatibilityResolver` — a voice is compatible with a model when
    an existing ready variant exists *or* the model's adapter declares a matching
    build strategy with ``can_build=True`` and all ``requires`` satisfied.
    """

    creation_source: str
    can_build: bool = True
    requires: list[str] = field(default_factory=list)
    description: str = ""


class ModelAdapter(ABC):
    """Translates between PeakVox concepts and one model engine."""

    def __init__(self, descriptor: ModelDescriptor) -> None:
        self.descriptor = descriptor

    # --- Identity + declared contract (concrete, torch-free) ----------------------

    @property
    def model_id(self) -> str:
        return self.descriptor.id

    def get_capabilities(self) -> ModelCapabilities:
        return self.descriptor.capabilities

    def get_supported_languages(self) -> list[str]:
        return list(self.descriptor.supported_languages)

    def get_supported_tags(self) -> list[str]:
        return list(self.descriptor.supported_tags)

    @property
    def supported_realization_types(self) -> list[str]:
        """Realization types this adapter can build (ADR-0008). The Runtime preflight-matches
        a variant's desired realization against this list before dispatching a build; it never
        interprets build strategy itself. Defaults to ``reference_sample``; providers with a
        different format (embeddings, checkpoints, LoRAs, …) override."""
        return [DEFAULT_REALIZATION]

    def get_build_strategies(self) -> list[VariantBuildStrategy]:
        """Declare which creation sources this adapter can build variants for.

        Used by :class:`CompatibilityResolver` to determine voice-model compatibility
        without checking the database. Each strategy asserts that when a voice has the
        given ``creation_source``, this adapter can produce a variant for it (assuming
        the listed prerequisites are met).

        Override on concrete adapters. Default = empty (no build-from-scratch support).
        """
        return []

    # --- Lifecycle ----------------------------------------------------------------

    @abstractmethod
    async def install(self) -> None:
        """Fetch weights/manifest into the model cache (idempotent)."""

    @abstractmethod
    async def load(self) -> None:
        """Bring weights resident (GPU/CPU), honoring the VRAM contract."""

    @abstractmethod
    def unload(self) -> None:
        """Release device memory. Safe to call when not loaded."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Readiness/liveness for the runtime and (future) cloud workers."""

    # --- Inference + voice realization --------------------------------------------

    @abstractmethod
    async def generate(
        self,
        *,
        text: str,
        output_path: Path,
        voice_profile_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        instruct: Optional[str] = None,
        params: Optional[dict] = None,
        job_id: Optional[str] = None,
    ) -> tuple[float, list[str]]:
        """Run inference, write audio to ``output_path``, return ``(duration_seconds, logs)``."""

    @abstractmethod
    async def clone_voice(
        self, *, db: "AsyncSession", voice: "Voice", reference_audio_key: str
    ) -> "VoiceVariant":
        """Build this model's VoiceVariant for ``voice`` from reference audio."""

    @abstractmethod
    async def build_variant(self, *, db: "AsyncSession", voice: "Voice") -> "VoiceVariant":
        """Produce (or rebuild) this model's VoiceVariant for ``voice`` from its canonical sources."""
