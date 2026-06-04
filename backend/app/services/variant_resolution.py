"""Resolve generation inputs from a Voice + Model, via its VoiceVariant.

This is the wire-level realization of the ``Voice + Model -> VoiceVariant`` contract: callers
pass a stable public_voice_id + model id; this returns the concrete inputs the provider needs.
Lazy/auto build of a missing variant is wired in a later phase; for now a missing variant is an
explicit error the caller maps to 409 (API §3).
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.voice_variant_repository import (
    get_voice_identity_by_public_id, resolve_variant,
)


class VariantUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class GenerationInputs:
    voice_id: str
    variant_id: str
    ref_audio_key: str | None
    ref_text: str | None
    generation_defaults: dict


async def resolve_generation_inputs(
    db: AsyncSession, *, public_voice_id: str, model_id: str
) -> GenerationInputs:
    voice = await get_voice_identity_by_public_id(db, public_voice_id)
    if voice is None:
        raise VariantUnavailableError(f"Unknown voice '{public_voice_id}'")

    variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
    if variant is None:
        raise VariantUnavailableError(
            f"No variant for voice '{public_voice_id}' on model '{model_id}' (build required)"
        )

    artifacts = variant.artifacts or {}
    params = variant.params or {}
    return GenerationInputs(
        voice_id=voice.id,
        variant_id=variant.id,
        ref_audio_key=artifacts.get("audio"),
        ref_text=params.get("transcript"),
        generation_defaults=params.get("generation_defaults") or {},
    )
