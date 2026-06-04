"""The PeakVox Runtime — the single, model-agnostic entry point for generation.

Layering (ADR-0004, Runtime §2):

    User / API  →  PeakVoxRuntime  →  ModelAdapter  →  Model Provider  →  Inference

The runtime owns: adapter resolution, model resolution, ``Voice + Model → VoiceVariant``
resolution, and capability/tag validation. It interacts *only* with :class:`ModelAdapter`
instances — never a model implementation — and never branches on a model id/name; behavior is
driven by declared capabilities (ADR-0003). The OmniVoice adapters delegate actual inference to
the proven registry/provider path, so the runtime adds orchestration without reimplementing the
VRAM/load discipline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Voice, VoiceVariant
from app.models.registry_types import ModelDescriptor
from app.services.capabilities import missing_capabilities as _missing_caps
from app.services.model_adapter import ModelAdapter
from app.services.tag_validation import find_unsupported_tags
from app.services.voice_variant_repository import (
    get_voice_identity_by_public_id,
    resolve_variant,
)


class ModelNotRegistered(Exception):
    pass


class VoiceNotFound(Exception):
    pass


class VariantUnavailable(Exception):
    pass


class UnsupportedTags(Exception):
    def __init__(self, tags: list[str]) -> None:
        self.tags = tags
        super().__init__(f"Unsupported tags: {tags}")


class UnsupportedCapability(Exception):
    def __init__(self, missing: set[str]) -> None:
        self.missing = missing
        super().__init__(f"Missing capabilities: {sorted(missing)}")


@dataclass(frozen=True)
class Resolution:
    voice: Voice
    model: ModelDescriptor
    variant: VoiceVariant
    adapter: ModelAdapter


class PeakVoxRuntime:
    """Resolves and orchestrates generation across registered model adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, ModelAdapter] = {}

    # --- Adapter registry ---------------------------------------------------------

    def register_adapter(self, adapter: ModelAdapter) -> None:
        self._adapters[adapter.model_id] = adapter

    def get_adapter(self, model_id: str) -> ModelAdapter:
        try:
            return self._adapters[model_id]
        except KeyError:
            raise ModelNotRegistered(model_id)

    def list_adapters(self) -> list[ModelAdapter]:
        return list(self._adapters.values())

    def resolve_model(self, model_id: Optional[str]) -> ModelDescriptor:
        """Resolve a model id to its descriptor; ``None`` → the default adapter's model."""
        if model_id is not None:
            return self.get_adapter(model_id).descriptor
        for adapter in self._adapters.values():
            if adapter.descriptor.is_default:
                return adapter.descriptor
        if self._adapters:
            return next(iter(self._adapters.values())).descriptor
        raise ModelNotRegistered("no adapters registered")

    # --- Capability / tag validation (capability-driven, never name-driven) -------

    def validate_tags(self, model_id: str, text: str) -> list[str]:
        adapter = self.get_adapter(model_id)
        return find_unsupported_tags(text, adapter.get_supported_tags())

    def missing_capabilities(self, model_id: str, required: set[str]) -> set[str]:
        adapter = self.get_adapter(model_id)
        return _missing_caps(adapter.get_capabilities(), set(required))

    # --- Resolution ---------------------------------------------------------------

    async def resolve(
        self, db: AsyncSession, *, public_voice_id: str, model_id: Optional[str]
    ) -> Resolution:
        """Resolve ``Voice + Model → VoiceVariant`` for a stable public voice id."""
        descriptor = self.resolve_model(model_id)
        adapter = self.get_adapter(descriptor.id)
        voice = await get_voice_identity_by_public_id(db, public_voice_id)
        if voice is None:
            raise VoiceNotFound(public_voice_id)
        variant = await resolve_variant(db, voice_id=voice.id, model_id=descriptor.id)
        if variant is None:
            raise VariantUnavailable(
                f"No variant for voice '{public_voice_id}' on model '{descriptor.id}'"
            )
        return Resolution(voice=voice, model=descriptor, variant=variant, adapter=adapter)

    # --- Generation (single entry point) ------------------------------------------

    async def generate(
        self,
        db: AsyncSession,
        *,
        text: str,
        output_path: Path,
        model_id: Optional[str] = None,
        public_voice_id: Optional[str] = None,
        voice_profile_id: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        instruct: Optional[str] = None,
        params: Optional[dict] = None,
        job_id: Optional[str] = None,
        required_capabilities: Optional[set[str]] = None,
    ) -> tuple[float, list[str]]:
        descriptor = self.resolve_model(model_id)
        adapter = self.get_adapter(descriptor.id)

        # Capability-driven validation — no model-name branching.
        bad_tags = find_unsupported_tags(text, adapter.get_supported_tags())
        if bad_tags:
            raise UnsupportedTags(bad_tags)
        if required_capabilities:
            missing = _missing_caps(adapter.get_capabilities(), set(required_capabilities))
            if missing:
                raise UnsupportedCapability(missing)

        # Voice + Model → VoiceVariant resolution (optional; ad-hoc reference otherwise).
        if public_voice_id is not None:
            resolution = await self.resolve(
                db, public_voice_id=public_voice_id, model_id=descriptor.id
            )
            artifacts = resolution.variant.artifacts or {}
            variant_params = resolution.variant.params or {}
            ref_audio_path = ref_audio_path or artifacts.get("audio")
            ref_text = ref_text if ref_text is not None else variant_params.get("transcript")
            voice_profile_id = voice_profile_id or resolution.voice.id

        return await adapter.generate(
            text=text,
            output_path=output_path,
            voice_profile_id=voice_profile_id,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            language=language,
            instruct=instruct,
            params=params,
            job_id=job_id,
        )


# Process-wide runtime singleton (adapters registered at wiring time).
runtime = PeakVoxRuntime()
