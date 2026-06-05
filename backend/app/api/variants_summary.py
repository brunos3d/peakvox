import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db import Voice, VoiceVariant, Model

logger = logging.getLogger(__name__)

router = APIRouter(tags=["variants"])


@router.get("/variants/summary")
async def get_variant_summary(db: AsyncSession = Depends(get_db)):
    """Return variant status across all voices for the Variant Dashboard.

    CE-only utility. Returns a list of voices, each with an array of per-model
    variant statuses. No pagination (CE scale assumption).
    """
    voices = (await db.execute(select(Voice))).scalars().all()
    models = (await db.execute(select(Model))).scalars().all()
    model_map = {m.id: m.name for m in models}

    variants = (
        await db.execute(select(VoiceVariant))
    ).scalars().all()

    voice_map: dict[str, list[dict]] = {}
    for v in variants:
        voice_map.setdefault(v.voice_id, []).append({
            "model_id": v.model_id,
            "model_name": model_map.get(v.model_id, v.model_id),
            "status": v.status,
            "active_artifact_id": v.active_artifact_id,
            "error_message": v.error_message,
        })

    result = []
    for voice in voices:
        result.append({
            "voice_id": voice.id,
            "voice_name": voice.name,
            "models": voice_map.get(voice.id, []),
        })

    return result
