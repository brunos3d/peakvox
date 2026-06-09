"""OmniVoice-family ModelAdapters — the first real adapters proving the multi-model runtime.

``OmniVoiceAdapter`` (Base) and ``OmniVoiceSingingAdapter`` (Singing + Emotion) share
one engine and one variant shape (reference-audio cloning) but advertise different capabilities
and tags via their descriptors. Both implement the same :class:`ModelAdapter` contract, so the
Runtime treats them identically — the difference is *declared data*, not branching code.

Data + variant methods are torch-free. Lifecycle/inference delegate to the proven registry /
``omnivoice_service`` path (lazy imports keep this module import-safe without a GPU stack).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Voice, VoiceVariant
from app.services.model_adapter import ModelAdapter, VariantBuildStrategy

logger = logging.getLogger(__name__)


class OmniVoiceFamilyAdapter(ModelAdapter):
    """Shared behavior for OmniVoice-family models."""

    # --- Lifecycle (delegates to the proven registry/service path) ----------------

    async def install(self) -> None:
        # Built-ins ship with the platform; weights are fetched on first load by the service.
        # (Community models use the HF installer; nothing to do here.)
        return None

    async def load(self) -> None:
        from app.services.model_registry import model_registry

        await model_registry.ensure_loaded(self.model_id)

    def unload(self) -> None:
        from app.services.omnivoice_service import omnivoice_service

        omnivoice_service.offload()

    async def health_check(self) -> bool:
        from app.services.omnivoice_service import omnivoice_service

        return bool(omnivoice_service.is_loaded)

    @staticmethod
    def get_build_strategies() -> list[VariantBuildStrategy]:
        return [
            VariantBuildStrategy(
                creation_source="SOURCE_ASSET",
                can_build=True,
                requires=["source_asset"],
                description="OmniVoice clones a voice from reference audio.",
            ),
        ]

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
        runtime_endpoint: Optional[str] = None,
    ) -> tuple[float, list[str]]:
        # Delegate to the registry: reuses the single-flight lock, ensure_loaded (with
        # cross-model offload), and the provider's proven inference path.
        from app.services.model_registry import model_registry

        resolved_voice_id = voice_id or voice_profile_id
        return await model_registry.generate(
            self.model_id,
            text=text,
            output_path=output_path,
            voice_profile_id=resolved_voice_id,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            language=language,
            instruct=instruct,
            params=params or {},
            job_id=job_id,
        )

    # --- Voice realization (torch-free: reference-audio reuse) ---------------------

    async def _upsert_variant(
        self, db: AsyncSession, *, voice: Voice, audio_key: Optional[str],
        transcript: Optional[str], source: str, status: Optional[str] = None,
    ) -> VoiceVariant:
        existing = (
            await db.execute(
                select(VoiceVariant).where(
                    VoiceVariant.voice_id == voice.id,
                    VoiceVariant.model_id == self.model_id,
                )
            )
        ).scalar_one_or_none()
        artifacts = {"audio": audio_key}
        params = {"transcript": transcript, "generation_defaults": {}}
        if existing is None:
            existing = VoiceVariant(
                voice_id=voice.id,
                model_id=self.model_id,
                artifact_type="reference_sample",
                artifacts=artifacts,
                params=params,
                source=source,
            )
            if status:
                existing.status = status
            db.add(existing)
        else:
            existing.artifacts = artifacts
            existing.params = params
            existing.source = source
            if status:
                existing.status = status
        await db.commit()
        await db.refresh(existing)
        return existing

    async def clone_voice(
        self, *, db: AsyncSession, voice: Voice, reference_audio_key: str
    ) -> VoiceVariant:
        """Create this model's variant from an explicit reference clip."""
        return await self._upsert_variant(
            db, voice=voice, audio_key=reference_audio_key, transcript=None, source="cloned", status="ready"
        )

    async def build_variant(self, *, db: AsyncSession, voice: Voice) -> VoiceVariant:
        """(Re)build this model's variant from the voice's canonical sources.

        OmniVoice-family models clone from reference audio, so a variant reuses the voice's
        existing reference (and transcript) — no new artifacts, no new ``public_voice_id``.
        """
        canonical = (
            await db.execute(select(VoiceVariant).where(VoiceVariant.voice_id == voice.id))
        ).scalars().first()
        audio_key = (canonical.artifacts or {}).get("audio") if canonical else voice.preview_audio
        transcript = (canonical.params or {}).get("transcript") if canonical else None
        return await self._upsert_variant(
            db, voice=voice, audio_key=audio_key, transcript=transcript, source="regenerated"
        )


class OmniVoiceAdapter(OmniVoiceFamilyAdapter):
    """OmniVoice Base — TTS, cloning, emotion tags, voice design."""


class OmniVoiceSingingAdapter(OmniVoiceFamilyAdapter):
    """OmniVoice Singing + Emotion — adds sung delivery + the rich emotion tag set."""
