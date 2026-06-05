import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db import Voice, Model, VoiceVariant
from app.services.runtime import (
    runtime,
    ModelNotRegistered,
    ModelNotAvailableInEdition,
    VariantBuildFailed,
    VariantBuilding,
)
from app.services.voice_variant_repository import get_voice_identity_by_public_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Variants"])


@router.post("/variants/backfill")
async def backfill_missing_variants(
    model_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Build missing variants for all voices × all installed models.

    Skips voice+model pairs that already have a variant. Returns a summary
    of what was built, skipped, and any errors.
    """
    # Collect all voices, models, and existing variants in bulk.
    voices = (await db.execute(select(Voice))).scalars().all()
    all_models = (await db.execute(select(Model))).scalars().all()
    if model_filter:
        all_models = [
            m for m in all_models
            if model_filter.lower() in m.id.lower() or model_filter.lower() in m.name.lower()
        ]
    existing = (await db.execute(select(VoiceVariant))).scalars().all()
    exists: set[tuple[str, str]] = {(v.voice_id, v.model_id) for v in existing}

    built: list[dict] = []
    skipped: list[dict] = []
    errors: list[dict] = []

    for voice in voices:
        for model in all_models:
            key = (voice.id, model.id)
            if key in exists:
                skipped.append({
                    "voice_id": voice.id,
                    "voice_name": voice.name,
                    "model_id": model.id,
                    "model_name": model.name,
                })
                continue

            try:
                resolved = await get_voice_identity_by_public_id(db, voice.public_voice_id)
                if resolved is None:
                    errors.append({
                        "voice_id": voice.id,
                        "voice_name": voice.name,
                        "model_id": model.id,
                        "model_name": model.name,
                        "error": "Voice not found by public ID",
                    })
                    continue

                variant = await runtime.ensure_variant(db, voice=resolved, model_id=model.id)
                built.append({
                    "voice_id": voice.id,
                    "voice_name": voice.name,
                    "model_id": model.id,
                    "model_name": model.name,
                    "status": variant.status,
                })
            except ModelNotRegistered as e:
                errors.append({
                    "voice_id": voice.id,
                    "voice_name": voice.name,
                    "model_id": model.id,
                    "model_name": model.name,
                    "error": str(e),
                })
            except VariantBuildFailed as e:
                errors.append({
                    "voice_id": voice.id,
                    "voice_name": voice.name,
                    "model_id": model.id,
                    "model_name": model.name,
                    "error": str(e.error) if e.error else "Build failed",
                })
            except VariantBuilding:
                skipped.append({
                    "voice_id": voice.id,
                    "voice_name": voice.name,
                    "model_id": model.id,
                    "model_name": model.name,
                    "note": "already building",
                })
            except ModelNotAvailableInEdition as e:
                errors.append({
                    "voice_id": voice.id,
                    "voice_name": voice.name,
                    "model_id": model.id,
                    "model_name": model.name,
                    "error": str(e),
                })
            except Exception as e:
                logger.exception("Unexpected error building variant %s/%s", voice.id, model.id)
                errors.append({
                    "voice_id": voice.id,
                    "voice_name": voice.name,
                    "model_id": model.id,
                    "model_name": model.name,
                    "error": str(e),
                })

    return {
        "built": built,
        "skipped": skipped,
        "errors": errors,
        "total_built": len(built),
        "total_skipped": len(skipped),
        "total_errors": len(errors),
    }
