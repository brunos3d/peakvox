import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.voice_resource import VoiceResourceResponse
from app.schemas.voice import VoiceProfileResponse
from app.services.compatibility_resolver import CompatibilityResolver
from app.services.import_resolver import ImportAlreadyExistsError
from app.services.runtime import runtime
from app.services.voice_resource_service import VoiceResourceService

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_service() -> VoiceResourceService:
    return VoiceResourceService(
        provider_registry=runtime._provider_voice_registry,
        compatibility_resolver=CompatibilityResolver(runtime),
    )


@router.get(
    "/api/voice-resources",
    response_model=list[VoiceResourceResponse],
)
async def list_voice_resources(
    resource_type: Optional[str] = None,
    resource_origin: Optional[str] = None,
    search: Optional[str] = None,
    language: Optional[str] = None,
    gender: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    svc = _build_service()
    return await svc.list(
        db,
        resource_type=resource_type,
        resource_origin=resource_origin,
        search=search,
        language=language,
        gender=gender,
    )


@router.get(
    "/api/voice-resources/{resource_id}",
    response_model=VoiceResourceResponse,
)
async def get_voice_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = _build_service()
    result = await svc.get(db, resource_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Voice resource not found")
    return result


@router.post(
    "/api/voice-resources/{resource_id}/import",
    response_model=VoiceProfileResponse,
    status_code=201,
)
async def import_voice_resource(
    resource_id: str,
    model_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    svc = _build_service()
    resource = await svc.get(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Voice resource not found")

    from app.services.import_resolver import ImportResolver

    resolver = ImportResolver()
    try:
        profile = await resolver.resolve(db, resource, model_id=model_id)
    except ImportAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    logger.info(
        "Imported voice resource %s (type=%s, origin=%s) as voice %s",
        resource_id,
        resource.resource_type,
        resource.resource_origin,
        profile.id,
    )
    resp = VoiceProfileResponse.model_validate(profile)
    resp.creation_source = "PRESET_VOICE"
    return resp
