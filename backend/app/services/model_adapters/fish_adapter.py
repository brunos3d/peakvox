"""FishAudioAdapter — the first non-OmniVoice provider (Phase 3.8 architecture validation).

Fish Audio differs from OmniVoice in architecture, voice representation, embedding format, and
inference pipeline. It integrates **purely through the :class:`ModelAdapter` contract** — the
Runtime needs no changes to support it, which is the whole point of the validation.

Fish-specific realization details (embedding format, etc.) live entirely inside the variant and
this adapter; they are never exposed on the public API (ADR-0004). Inference is not wired yet
(the model ships ``status="disabled"`` until weights/runtime are verified), so ``generate``/
``load`` raise a clear error if invoked; resolution and variant building are fully functional.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Voice, VoiceVariant
from app.services.model_adapter import ModelAdapter


class FishAudioAdapter(ModelAdapter):
    """Adapter for Fish Audio S2 (CE-only). Distinct engine, same contract."""

    # Fish realizes a voice as a precomputed speaker embedding, not a reference clip (ADR-0008).
    @property
    def supported_realization_types(self) -> list[str]:
        return ["embedding"]

    async def install(self) -> None:
        # Community models are fetched via the HF installer; nothing platform-side to do.
        return None

    async def load(self) -> None:
        raise NotImplementedError(
            "Fish Audio inference is not wired yet (model is disabled pending weights/licensing)."
        )

    def unload(self) -> None:
        return None

    async def health_check(self) -> bool:
        # Not runnable until the Fish runtime is wired; healthy=False keeps it out of readiness.
        return False

    async def generate(
        self,
        *,
        text: str,
        output_path: Path,
        voice_profile_id: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        instruct: Optional[str] = None,
        params: Optional[dict] = None,
        job_id: Optional[str] = None,
    ) -> tuple[float, list[str]]:
        raise NotImplementedError(
            "Fish Audio inference is not wired yet (model is disabled pending weights/licensing)."
        )

    # --- Voice realization (Fish-specific format, encapsulated) --------------------

    async def _upsert_variant(
        self, db: AsyncSession, *, voice: Voice, audio_key: Optional[str], source: str
    ) -> VoiceVariant:
        existing = (
            await db.execute(
                select(VoiceVariant).where(
                    VoiceVariant.voice_id == voice.id,
                    VoiceVariant.model_id == self.model_id,
                )
            )
        ).scalar_one_or_none()
        # Fish realizes a voice as a speaker EMBEDDING (a different format than OmniVoice's
        # reference sample) — the difference is contained entirely within the variant.
        artifacts = {"source_audio": audio_key, "embedding": None}
        params = {"format": "fish-speaker-embedding", "computed": False}
        if existing is None:
            existing = VoiceVariant(
                voice_id=voice.id,
                model_id=self.model_id,
                artifact_type="embedding",
                artifacts=artifacts,
                params=params,
                source=source,
                status="ready",
            )
            db.add(existing)
        else:
            existing.artifact_type = "embedding"
            existing.artifacts = artifacts
            existing.params = params
            existing.source = source
            existing.status = "ready"
        await db.commit()
        await db.refresh(existing)
        return existing

    async def clone_voice(
        self, *, db: AsyncSession, voice: Voice, reference_audio_key: str
    ) -> VoiceVariant:
        return await self._upsert_variant(db, voice=voice, audio_key=reference_audio_key, source="cloned")

    async def build_variant(self, *, db: AsyncSession, voice: Voice) -> VoiceVariant:
        """Build the Fish variant from the voice's canonical reference (embedding computed later)."""
        canonical = (
            await db.execute(select(VoiceVariant).where(VoiceVariant.voice_id == voice.id))
        ).scalars().first()
        audio_key = (canonical.artifacts or {}).get("audio") if canonical else voice.preview_audio
        return await self._upsert_variant(db, voice=voice, audio_key=audio_key, source="regenerated")
