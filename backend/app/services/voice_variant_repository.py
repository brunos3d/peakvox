"""Lookups for the split voice model: identity (voices) + realization (voice_variants)."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Voice, VoiceVariant


async def get_voice_identity_by_public_id(db: AsyncSession, public_voice_id: str) -> Optional[Voice]:
    res = await db.execute(select(Voice).where(Voice.public_voice_id == public_voice_id))
    return res.scalar_one_or_none()


async def resolve_variant(db: AsyncSession, *, voice_id: str, model_id: str) -> Optional[VoiceVariant]:
    """Return the (voice_id, model_id) variant, or None if it does not exist yet.

    A None result means the variant must be built by the onboarding pipeline before generation
    (lazy build / stale rebuild — wired in a later phase). For omnivoice-base on a backfilled
    voice, the variant always exists.
    """
    res = await db.execute(
        select(VoiceVariant).where(
            VoiceVariant.voice_id == voice_id, VoiceVariant.model_id == model_id
        )
    )
    return res.scalar_one_or_none()
