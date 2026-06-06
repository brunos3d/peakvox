import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.db import VoiceProfile, VoiceSourceAsset, Voice, VoiceVariant, VoiceVariantArtifact
from app.schemas.provider_voice import CreateFromPresetRequest
from app.schemas.voice import (
    FavoriteUpdate,
    VoiceGenerationDefaults,
    VoiceListPage,
    VoiceProfileResponse,
    VoiceSourceAssetResponse,
)
from app.services.voice_metadata import characteristics_from_defaults
from app.services.voice_onboarding import delete_voice_split, mirror_profile_to_split
from app.services.voice_repository import (
    VALID_SCOPES,
    list_voices_page,
    set_favorite,
)
from app.services.audio_preprocessing_service import (
    AudioPreprocessingError,
    process_audio,
    probe_duration,
    write_metadata_json,
    MAX_REFERENCE_DURATION,
)
from app.services.omnivoice_service import omnivoice_service
from app.services.storage import storage
from app.utils.streaming import stream_object

logger = logging.getLogger(__name__)
router = APIRouter()


async def resolve_voice_audio_key(profile_id: str) -> Optional[str]:
    """Return the object key for a profile's reference audio (reference.wav,
    falling back to the legacy voice.wav), or None if neither exists."""
    for name in ("reference.wav", "voice.wav"):
        key = f"voices/{profile_id}/{name}"
        if await storage.exists(key):
            return key
    return None


def _effective_crop_end(tmp_path: Path, crop_end: Optional[float]) -> float:
    if crop_end is not None:
        return crop_end
    total = probe_duration(tmp_path)
    return min(total, MAX_REFERENCE_DURATION)


def _parse_generation_defaults(raw: Optional[str]) -> Optional[dict]:
    """Parse a JSON string into a generation_defaults dict, returning None on failure."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
        # Validate via Pydantic — drops unknown fields, applies defaults
        return VoiceGenerationDefaults(**data).model_dump()
    except Exception:
        return None


def _parse_preset_tags(raw: Optional[str]) -> Optional[list[str]]:
    """Parse preset_tags from a JSON-encoded list (multipart form field)."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(t) for t in data]
    except Exception:
        pass
    return None


async def _process_and_upload(
    profile_id: str,
    file: UploadFile,
    crop_start: float,
    crop_end: Optional[float],
    name: str,
    language: Optional[str],
    transcript: Optional[str],
    created_at: Optional[str],
) -> dict:
    """Process an uploaded audio file in local scratch, then upload the
    reference.wav + metadata.json objects to MinIO. Returns the audio meta."""
    work_dir = settings.TMP_DIR / f"voice-{profile_id}-{uuid.uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix if file.filename else ".audio"
    tmp_path = work_dir / f"source{suffix}"
    output_path = work_dir / "reference.wav"
    meta_path = work_dir / "metadata.json"

    try:
        content = await file.read()
        with open(tmp_path, "wb") as f_:
            f_.write(content)

        crop_end_val = _effective_crop_end(tmp_path, crop_end)
        meta = process_audio(
            source_path=tmp_path,
            output_path=output_path,
            crop_start=crop_start,
            crop_end=crop_end_val,
            source_filename=file.filename or "",
        )

        write_metadata_json(
            meta_path,
            profile_id=profile_id,
            name=name,
            meta=meta,
            language=language,
            transcript=transcript,
            created_at=created_at,
        )

        await storage.put_file(f"voices/{profile_id}/reference.wav", output_path, "audio/wav")
        await storage.put_file(f"voices/{profile_id}/metadata.json", meta_path, "application/json")
        return meta
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


async def _fetch_source_asset_map(
    db: AsyncSession, profile_ids: list[str]
) -> dict[str, VoiceSourceAsset]:
    if not profile_ids:
        return {}
    result = await db.execute(
        select(VoiceSourceAsset).where(VoiceSourceAsset.voice_id.in_(profile_ids))
    )
    return {sa.voice_id: sa for sa in result.scalars().all()}


@router.get("", response_model=list[VoiceProfileResponse])
async def list_voices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VoiceProfile).order_by(
            VoiceProfile.last_used_at.desc().nullslast(),
            VoiceProfile.created_at.desc(),
        )
    )
    items = result.scalars().all()
    asset_map = await _fetch_source_asset_map(db, [v.id for v in items])
    responses = []
    for v in items:
        resp = VoiceProfileResponse.model_validate(v)
        sa = asset_map.get(v.id)
        if sa:
            resp.source_asset = VoiceSourceAssetResponse.model_validate(sa)
        responses.append(resp)
    return responses


@router.get("/page", response_model=VoiceListPage)
async def list_voices_page_endpoint(
    scope: str = "mine",
    search: Optional[str] = None,
    language_code: Optional[str] = None,
    gender: Optional[str] = None,
    age_group: Optional[str] = None,
    accent: Optional[str] = None,
    favorite: Optional[bool] = None,
    limit: int = 24,
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filtered, searchable listing that powers the Voice Library."""
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=422, detail=f"Invalid scope: {scope}")
    items, next_cursor = await list_voices_page(
        db,
        scope=scope,
        search=search,
        language_code=language_code,
        gender=gender,
        age_group=age_group,
        accent=accent,
        favorite=favorite,
        limit=limit,
        cursor=cursor,
    )
    asset_map = await _fetch_source_asset_map(db, [v.id for v in items])
    responses = []
    for v in items:
        resp = VoiceProfileResponse.model_validate(v)
        sa = asset_map.get(v.id)
        if sa:
            resp.source_asset = VoiceSourceAssetResponse.model_validate(sa)
        responses.append(resp)
    return VoiceListPage(
        items=responses,
        next_cursor=next_cursor,
    )


@router.get("/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice(profile_id: str, db: AsyncSession = Depends(get_db)):
    profile = await db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    result = await db.execute(
        select(VoiceSourceAsset).where(VoiceSourceAsset.voice_id == profile.id).limit(1)
    )
    source_asset = result.scalar_one_or_none()
    resp = VoiceProfileResponse.model_validate(profile)
    if source_asset:
        resp.source_asset = VoiceSourceAssetResponse.model_validate(source_asset)
    return resp


@router.get("/{profile_id}/audio")
async def get_voice_audio(profile_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    profile = await db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    key = await resolve_voice_audio_key(profile.id)
    if key:
        return await stream_object(key, request=request, content_type="audio/wav")
    # No reference audio — return silence. Some voice types (e.g. Kokoro presets)
    # have no reference audio file; this endpoint exists for UI preview, and a
    # silent WAV is better than a 404 that breaks the HTML5 audio element.
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"")  # zero-length silence
    buf.seek(0)
    from fastapi.responses import Response
    return Response(content=buf.getvalue(), media_type="audio/wav")


@router.post("", response_model=VoiceProfileResponse, status_code=201)
async def create_voice(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    language_code: Optional[str] = Form(None),
    transcript: Optional[str] = Form(None),
    generation_defaults: Optional[str] = Form(None),
    preset_tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    crop_start: float = Form(0.0),
    crop_end: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    profile_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    try:
        meta = await _process_and_upload(
            profile_id, file, crop_start, crop_end,
            name=name, language=language, transcript=transcript,
            created_at=now.isoformat(),
        )
    except AudioPreprocessingError as exc:
        await storage.delete_prefix(f"voices/{profile_id}/")
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        await storage.delete_prefix(f"voices/{profile_id}/")
        logger.exception("Unexpected error processing audio for new voice profile")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {exc}")

    parsed_defaults = _parse_generation_defaults(generation_defaults)
    parsed_tags = _parse_preset_tags(preset_tags)

    profile = VoiceProfile(
        id=profile_id,
        name=name,
        description=description,
        language=language,
        language_code=language_code,
        transcript=transcript,
        audio_filename="reference.wav",
        audio_duration=meta["duration"],
        meta=meta,
        generation_defaults=parsed_defaults,
        preset_tags=parsed_tags,
        characteristics=characteristics_from_defaults(
            parsed_defaults, preset_tags=parsed_tags, language=language
        ),
        owner_id=settings.LOCAL_OWNER_ID,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    # PeakVox Phase 3: mirror into the split Voice + VoiceVariant tables (ADR-0001).
    await mirror_profile_to_split(db, profile)

    # PeakVox Phase 4: record the Voice Source Asset (ADR-0010).
    source_asset = VoiceSourceAsset(
        voice_id=profile_id,
        storage_key=f"voices/{profile_id}/reference.wav",
        asset_type="reference_audio",
        original_filename=file.filename,
        audio_duration=meta["duration"],
    )
    db.add(source_asset)
    await db.commit()

    logger.info(
        "Created voice profile %s (%s, %.2fs, src=%s)",
        profile_id, name, meta["duration"], meta["source_format"],
    )
    return profile


@router.put("/{profile_id}", response_model=VoiceProfileResponse)
async def update_voice(
    profile_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    language_code: Optional[str] = Form(None),
    transcript: Optional[str] = Form(None),
    generation_defaults: Optional[str] = Form(None),
    preset_tags: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    crop_start: float = Form(0.0),
    crop_end: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    if name is not None:
        profile.name = name
    if description is not None:
        profile.description = description
    if language is not None:
        profile.language = language
    if language_code is not None:
        profile.language_code = language_code
    if transcript is not None:
        profile.transcript = transcript
    if preset_tags is not None:
        profile.preset_tags = _parse_preset_tags(preset_tags)

    # Update generation_defaults when explicitly provided (empty string clears it)
    if generation_defaults is not None:
        profile.generation_defaults = _parse_generation_defaults(generation_defaults) if generation_defaults else None

    # voice_design or preset_tags may have changed — regenerate the read-only snapshot.
    if generation_defaults is not None or preset_tags is not None:
        profile.characteristics = characteristics_from_defaults(
            profile.generation_defaults,
            preset_tags=profile.preset_tags,
            language=profile.language,
        )

    if file is not None and file.filename:
        try:
            meta = await _process_and_upload(
                profile.id, file, crop_start, crop_end,
                name=profile.name if name is None else name,
                language=profile.language if language is None else language,
                transcript=profile.transcript if transcript is None else transcript,
                created_at=profile.created_at.isoformat() if profile.created_at else None,
            )
        except AudioPreprocessingError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            logger.exception("Unexpected error processing audio for profile %s", profile_id)
            raise HTTPException(status_code=500, detail=f"Audio processing failed: {exc}")

        profile.audio_filename = "reference.wav"
        profile.audio_duration = meta["duration"]
        profile.meta = meta
        omnivoice_service.invalidate_voice_cache(profile.id)
        logger.info(
            "Updated audio for profile %s (%.2fs, src=%s)",
            profile_id, meta["duration"], meta["source_format"],
        )

    await db.commit()
    await db.refresh(profile)

    # PeakVox Phase 3: keep the split Voice + VoiceVariant tables in sync (ADR-0001).
    await mirror_profile_to_split(db, profile)

    logger.info("Updated voice profile %s", profile_id)
    return profile


@router.patch("/{profile_id}/favorite", response_model=VoiceProfileResponse)
async def update_favorite(
    profile_id: str,
    payload: FavoriteUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Toggle the favorite flag for a voice."""
    voice = await set_favorite(db, profile_id, payload.is_favorite)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    return voice


@router.patch("/{profile_id}/defaults", response_model=VoiceProfileResponse)
async def save_voice_defaults(
    profile_id: str,
    defaults: VoiceGenerationDefaults,
    db: AsyncSession = Depends(get_db),
):
    """Persist generation defaults for a voice profile without touching audio."""
    profile = await db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    profile.generation_defaults = defaults.model_dump()
    # voice_design changed → regenerate the derived characteristics snapshot.
    profile.characteristics = characteristics_from_defaults(
        profile.generation_defaults,
        preset_tags=profile.preset_tags,
        language=profile.language,
    )
    await db.commit()
    await db.refresh(profile)
    logger.info("Saved generation defaults for voice profile %s", profile_id)
    return profile


@router.delete("/{profile_id}")
async def delete_voice(profile_id: str, db: AsyncSession = Depends(get_db)):
    profile = await db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    await storage.delete_prefix(f"voices/{profile.id}/")
    omnivoice_service.invalidate_voice_cache(profile.id)
    await db.delete(profile)
    await db.commit()
    # PeakVox Phase 3: remove the mirrored Voice + variants (ADR-0001).
    await delete_voice_split(db, profile_id)
    logger.info("Deleted voice profile %s", profile_id)
    return {"detail": "Voice profile deleted"}


@router.post("/from-preset", response_model=VoiceProfileResponse, status_code=201)
async def create_voice_from_preset(
    body: CreateFromPresetRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.services.provider_voice import build_provider_voice_id
    from app.services.runtime import runtime as rt

    provider_voice_id = build_provider_voice_id(body.provider, body.preset_name)
    provider_voice = rt._provider_voice_registry.get(provider_voice_id)
    if provider_voice is None:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{body.preset_name}' not found for provider '{body.provider}'",
        )

    profile_id = str(uuid.uuid4())
    public_id = f"voice_{uuid.uuid4().hex[:10].upper()}"

    profile = VoiceProfile(
        id=profile_id,
        public_voice_id=public_id,
        name=body.name,
        description=f"{body.provider} preset: {provider_voice.name} ({provider_voice.language or ''})",
        language=provider_voice.language,
        language_code=provider_voice.language,
        transcript="",
        audio_filename="",
        audio_duration=0.0,
        is_preset_voice=True,
        owner_id=settings.LOCAL_OWNER_ID,
        meta={"provider": body.provider, "preset_name": body.preset_name},
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    await mirror_profile_to_split(db, profile)

    # Create VoiceVariant
    voice = (await db.execute(
        select(Voice).where(Voice.id == profile_id)
    )).scalars().first()

    variant = VoiceVariant(
        id=str(uuid.uuid4()),
        voice_id=voice.id,
        model_id=body.model_id,
        artifact_type="voice_pack",
        params={"provider": body.provider, "preset_name": body.preset_name},
        artifacts={},
        source="preset",
        status="ready",
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)

    artifact = VoiceVariantArtifact(
        id=str(uuid.uuid4()),
        voice_variant_id=variant.id,
        version=1,
        storage_keys={},
        meta={"provider": body.provider, "preset_name": body.preset_name},
    )
    db.add(artifact)
    variant.active_artifact_id = artifact.id
    await db.commit()

    logger.info("Created preset voice %s (%s/%s)", profile_id, body.provider, body.preset_name)
    resp = VoiceProfileResponse.model_validate(profile)
    resp.creation_source = "PRESET_VOICE"
    return resp
