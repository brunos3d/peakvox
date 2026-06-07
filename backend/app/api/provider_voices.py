"""Legacy provider-voices endpoints — thin wrappers over VoiceResourceService.

All business logic has been migrated to ``VoiceResourceService`` and
``ImportResolver``.  These endpoints exist only for backward compatibility with
clients that still consume ``/api/provider-voices``.

New clients should use ``/api/voice-resources`` directly.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.provider_voice import ProviderVoiceResponse
from app.services.compatibility_resolver import CompatibilityResolver
from app.services.runtime import runtime
from app.services.voice_resource_service import VoiceResourceService

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_service() -> VoiceResourceService:
    return VoiceResourceService(
        provider_registry=runtime._provider_voice_registry,
        compatibility_resolver=CompatibilityResolver(runtime),
    )


def _legacy_to_response(v) -> ProviderVoiceResponse:
    """Map ``VoiceResourceResponse`` → ``ProviderVoiceResponse``.

    Preserves the exact field contract clients expect from the legacy endpoint.
    """
    return ProviderVoiceResponse(
        provider_voice_id=v.id,
        provider_id=v.provider_id or "",
        external_id=v.external_id or v.id,
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
    db: AsyncSession = Depends(get_db),
):
    # "all" is the frontend sentinel for "show all" — treat as None
    provider_id = provider if provider and provider != "all" else None
    lang = language if language and language != "all" else None
    gen = gender if gender and gender != "all" else None

    svc = _build_service()
    resources = await svc.list(
        db,
        resource_type="preset",
        resource_origin=provider_id,
        search=search or None,
        language=lang,
        gender=gen,
    )
    return [_legacy_to_response(r) for r in resources]


@router.get("/api/provider-voices/{provider_voice_id}", response_model=ProviderVoiceResponse)
async def get_provider_voice(
    provider_voice_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = _build_service()
    resource = await svc.get(db, provider_voice_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Provider voice not found")
    return _legacy_to_response(resource)
