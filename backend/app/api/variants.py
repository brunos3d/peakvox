import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db import Voice, VoiceVariant
from app.schemas.variant import (
    ArtifactVersionResponse,
    VariantBuildResponse,
    VariantListItem,
    VariantStatusResponse,
)
from app.services.model_catalog import builtin_by_id
from app.services.runtime import (
    ArtifactVersionNotFound,
    ModelNotAvailableInEdition,
    ModelNotRegistered,
    runtime,
    VariantBuildFailed,
    VariantBuilding,
    VariantDeprecated,
    VariantUnavailable,
)
from app.services.voice_variant_artifact_repository import get_active_artifact, list_versions
from app.services.voice_variant_repository import get_voice_identity_by_public_id, resolve_variant

logger = logging.getLogger(__name__)
router = APIRouter()


async def _resolve_voice(db: AsyncSession, public_voice_id: str) -> Voice:
    voice = await get_voice_identity_by_public_id(db, public_voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail=f"Voice '{public_voice_id}' not found")
    return voice


def _variant_row_to_list_item(row: VoiceVariant) -> VariantListItem:
    desc = builtin_by_id(row.model_id)
    return VariantListItem(
        model_id=row.model_id,
        model_name=desc.name if desc else row.model_id,
        status=row.status,
        active_artifact_version=None,
    )


@router.get("/{public_voice_id}/variants", response_model=list[VariantListItem])
async def list_variants(public_voice_id: str, db: AsyncSession = Depends(get_db)):
    """List all variants for a voice with their lifecycle statuses."""
    voice = await _resolve_voice(db, public_voice_id)
    rows = (
        await db.execute(select(VoiceVariant).where(VoiceVariant.voice_id == voice.id))
    ).scalars().all()
    items = []
    for row in rows:
        item = _variant_row_to_list_item(row)
        if row.active_artifact_id:
            active = await get_active_artifact(db, row)
            if active:
                item.active_artifact_version = active.version
        items.append(item)
    return items


@router.get("/{public_voice_id}/variants/{model_id}", response_model=VariantStatusResponse)
async def get_variant_status(
    public_voice_id: str, model_id: str, db: AsyncSession = Depends(get_db)
):
    """Get the lifecycle status of a specific voice + model variant."""
    voice = await _resolve_voice(db, public_voice_id)
    try:
        runtime.get_adapter(model_id)
    except ModelNotRegistered:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not registered")

    desc = builtin_by_id(model_id)
    variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
    if variant is None:
        return VariantStatusResponse(
            model_id=model_id,
            model_name=desc.name if desc else model_id,
            status="pending",
            artifact_count=0,
        )

    active = None
    if variant.active_artifact_id:
        active = await get_active_artifact(db, variant)
    versions = await list_versions(db, variant.id)

    return VariantStatusResponse(
        model_id=model_id,
        model_name=desc.name if desc else model_id,
        status=variant.status,
        active_artifact_version=active.version if active else None,
        artifact_count=len(versions),
        error_message=variant.error_message,
    )


@router.post("/{public_voice_id}/variants", response_model=VariantBuildResponse, status_code=201)
async def ensure_variant_endpoint(
    public_voice_id: str,
    model_id: str = Query(None, description="Model to build variant for (default: platform default)"),
    db: AsyncSession = Depends(get_db),
):
    """Ensure a variant exists for this voice on the given model. Builds if needed.

    Returns the variant status: ``ready`` if already built, ``building`` after dispatching
    a new build, or an error for failed/deprecated variants.
    """
    voice = await _resolve_voice(db, public_voice_id)
    try:
        resolved = runtime.resolve_model(model_id)
    except ModelNotRegistered:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not registered")

    try:
        variant = await runtime.ensure_variant(db, voice=voice, model_id=resolved.id)
    except VariantBuilding:
        raise HTTPException(
            status_code=409,
            detail=f"Variant build already in progress for voice '{public_voice_id}' on '{resolved.id}'",
        )
    except VariantBuildFailed as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Variant build failed for voice '{public_voice_id}' on '{resolved.id}': {exc.error or 'unknown error'}",
        )
    except VariantDeprecated:
        raise HTTPException(
            status_code=409,
            detail=f"Variant for voice '{public_voice_id}' on '{resolved.id}' is deprecated; rebuild required",
        )
    except ModelNotAvailableInEdition as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except VariantUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    active_artifact_version = None
    if variant.active_artifact_id:
        active = await get_active_artifact(db, variant)
        if active:
            active_artifact_version = active.version

    return VariantBuildResponse(
        voice_id=voice.id,
        model_id=resolved.id,
        status=variant.status,
        active_artifact_version=active_artifact_version,
    )


@router.post("/{public_voice_id}/variants/{model_id}/rebuild", response_model=VariantBuildResponse)
async def rebuild_variant_endpoint(
    public_voice_id: str,
    model_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Force-rebuild an existing variant, appending a new artifact version."""
    voice = await _resolve_voice(db, public_voice_id)
    try:
        runtime.get_adapter(model_id)
    except ModelNotRegistered:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not registered")

    try:
        variant = await runtime.rebuild_variant(db, voice=voice, model_id=model_id)
    except VariantBuildFailed as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Rebuild failed for voice '{public_voice_id}' on '{model_id}': {exc.error or 'unknown error'}",
        )
    except ModelNotAvailableInEdition as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except VariantUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    active_artifact_version = None
    if variant.active_artifact_id:
        active = await get_active_artifact(db, variant)
        if active:
            active_artifact_version = active.version

    return VariantBuildResponse(
        voice_id=voice.id,
        model_id=model_id,
        status=variant.status,
        active_artifact_version=active_artifact_version,
    )


@router.post(
    "/{public_voice_id}/variants/{model_id}/rollback/{version}",
    response_model=VariantBuildResponse,
)
async def rollback_variant_endpoint(
    public_voice_id: str,
    model_id: str,
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """Rollback a variant to a prior artifact version without rebuilding."""
    voice = await _resolve_voice(db, public_voice_id)
    try:
        runtime.get_adapter(model_id)
    except ModelNotRegistered:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not registered")

    try:
        variant = await runtime.rollback_artifact(
            db, voice=voice, model_id=model_id, version=version
        )
    except ArtifactVersionNotFound:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact version {version} not found for voice '{public_voice_id}' on '{model_id}'",
        )
    except VariantUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    active_artifact_version = None
    if variant.active_artifact_id:
        active = await get_active_artifact(db, variant)
        if active:
            active_artifact_version = active.version

    return VariantBuildResponse(
        voice_id=voice.id,
        model_id=model_id,
        status=variant.status,
        active_artifact_version=active_artifact_version,
    )


@router.get(
    "/{public_voice_id}/variants/{model_id}/artifacts",
    response_model=list[ArtifactVersionResponse],
)
async def list_artifact_versions_endpoint(
    public_voice_id: str,
    model_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all artifact versions for a voice + model variant (ADR-0009)."""
    voice = await _resolve_voice(db, public_voice_id)
    try:
        runtime.get_adapter(model_id)
    except ModelNotRegistered:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not registered")

    variant = await resolve_variant(db, voice_id=voice.id, model_id=model_id)
    if variant is None:
        return []

    active = await get_active_artifact(db, variant)
    active_id = active.id if active else None
    versions = await list_versions(db, variant.id)

    return [
        ArtifactVersionResponse(
            version=v.version,
            created_at=v.created_at,
            is_active=v.id == active_id,
            model_version=v.model_version,
            size_bytes=v.size_bytes,
            storage_keys=v.storage_keys,
        )
        for v in versions
    ]
