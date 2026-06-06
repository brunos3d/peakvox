import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

from app.schemas.provider_voice import ProviderVoiceResponse
from app.services.runtime import runtime

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(v) -> ProviderVoiceResponse:
    return ProviderVoiceResponse(
        provider_voice_id=v.provider_voice_id,
        provider_id=v.provider_id,
        external_id=v.external_id,
        name=v.name,
        description=v.description,
        language=v.language,
        gender=v.gender,
        is_default=v.is_default,
    )


@router.get("/api/provider-voices", response_model=list[ProviderVoiceResponse])
async def list_provider_voices(
    provider: Optional[str] = None,
    language: Optional[str] = None,
    gender: Optional[str] = None,
    search: Optional[str] = None,
):
    # "all" is the frontend sentinel for "show all" — treat as None
    provider_id = provider if provider and provider != "all" else None
    lang = language if language and language != "all" else None
    gen = gender if gender and gender != "all" else None
    voices = runtime._provider_voice_registry.search(
        query=search or "",
        provider_id=provider_id,
        language=lang,
        gender=gen,
    )
    return [_to_response(v) for v in voices]


@router.get("/api/provider-voices/{provider_voice_id}", response_model=ProviderVoiceResponse)
async def get_provider_voice(provider_voice_id: str):
    voice = runtime._provider_voice_registry.get(provider_voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Provider voice not found")
    return _to_response(voice)
