"""Voice onboarding: turn a legacy VoiceProfile into a Voice + OmniVoice VoiceVariant.

``split_profile_row`` is a pure mapping reused by the backfill migration and by runtime
dual-write on voice create/update, so both paths stay identical (ADR-0001 / Migration §2).
"""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_MODEL_ID = "omnivoice-base"


def split_profile_row(profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(voice_dict, variant_dict)`` derived from a voice_profiles row.

    The Voice reuses the profile's UUID as its ``id`` (so existing storage prefixes
    ``/data/voices/{id}/`` keep working) and carries ``public_voice_id`` unchanged.
    """
    voice = {
        "id": profile["id"],
        "public_voice_id": profile["public_voice_id"],
        "owner_id": profile.get("owner_id"),
        "creator_id": None,
        "name": profile["name"],
        "description": profile.get("description"),
        "language": profile.get("language"),
        "language_code": profile.get("language_code"),
        "preview_audio": profile.get("audio_filename"),  # the reference doubles as preview initially
        "meta": profile.get("meta"),
        "characteristics": profile.get("characteristics"),
        "royalty_config": None,
        "is_public": bool(profile.get("is_public", False)),
        "is_community_voice": bool(profile.get("is_community_voice", False)),
        "is_preset_voice": bool(profile.get("is_preset_voice", False)),
        "is_favorite": bool(profile.get("is_favorite", False)),
        "status": profile.get("status", "ready"),
        "usage_count": int(profile.get("usage_count", 0) or 0),
    }
    defaults = profile.get("generation_defaults") or {}
    variant = {
        "voice_id": profile["id"],
        "model_id": DEFAULT_MODEL_ID,
        "model_version": None,
        "artifact_type": "reference_sample",
        "artifacts": {"audio": profile.get("audio_filename")},
        "params": {
            "transcript": profile.get("transcript"),
            "voice_design": defaults.get("voice_design"),
            "generation_defaults": defaults,
        },
        "source": "cloned",
        "status": "ready",
    }
    return voice, variant


def _profile_to_dict(profile) -> dict[str, Any]:
    """Read the fields ``split_profile_row`` needs from a ``VoiceProfile`` ORM object."""
    return {
        "id": profile.id,
        "public_voice_id": profile.public_voice_id,
        "owner_id": profile.owner_id,
        "name": profile.name,
        "description": profile.description,
        "language": profile.language,
        "language_code": profile.language_code,
        "transcript": profile.transcript,
        "audio_filename": profile.audio_filename,
        "meta": profile.meta,
        "characteristics": profile.characteristics,
        "generation_defaults": profile.generation_defaults,
        "is_public": profile.is_public,
        "is_community_voice": profile.is_community_voice,
        "is_preset_voice": profile.is_preset_voice,
        "is_favorite": profile.is_favorite,
        "status": profile.status,
        "usage_count": profile.usage_count,
    }


async def mirror_profile_to_split(db: AsyncSession, profile) -> None:
    """Upsert the ``Voice`` + ``omnivoice-base`` ``VoiceVariant`` mirroring a ``VoiceProfile``.

    Keeps the split tables consistent with voice_profiles on every create/update so generation
    can resolve by variant immediately. Reuses ``split_profile_row`` (DRY) — the same mapping
    the backfill migration uses. Commits.
    """
    from app.models.db import Voice, VoiceVariant

    voice_data, variant_data = split_profile_row(_profile_to_dict(profile))

    voice = await db.get(Voice, voice_data["id"])
    if voice is None:
        db.add(Voice(**voice_data))
    else:
        for key, value in voice_data.items():
            if key != "id":
                setattr(voice, key, value)

    existing = (
        await db.execute(
            select(VoiceVariant).where(
                VoiceVariant.voice_id == variant_data["voice_id"],
                VoiceVariant.model_id == variant_data["model_id"],
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(VoiceVariant(**variant_data))
    else:
        existing.artifacts = variant_data["artifacts"]
        existing.params = variant_data["params"]
        existing.status = variant_data["status"]

    await db.commit()


async def delete_voice_split(db: AsyncSession, voice_id: str) -> None:
    """Remove the split ``Voice`` + its variants for a deleted profile. Commits."""
    from app.models.db import Voice, VoiceVariant

    await db.execute(delete(VoiceVariant).where(VoiceVariant.voice_id == voice_id))
    voice = await db.get(Voice, voice_id)
    if voice is not None:
        await db.delete(voice)
    await db.commit()
