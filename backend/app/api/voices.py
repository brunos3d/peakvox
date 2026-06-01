import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.db import VoiceProfile
from app.schemas.voice import VoiceProfileResponse
from app.services.audio_preprocessing_service import (
    AudioPreprocessingError,
    process_audio,
    probe_duration,
    write_metadata_json,
    MAX_REFERENCE_DURATION,
)
from app.services.omnivoice_service import omnivoice_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_audio_path(profile_id: str) -> Optional[Path]:
    """Return the audio path for a profile, checking reference.wav then voice.wav."""
    for name in ("reference.wav", "voice.wav"):
        p = settings.VOICES_DIR / profile_id / name
        if p.exists():
            return p
    return None


def _effective_crop_end(tmp_path: Path, crop_end: Optional[float]) -> float:
    if crop_end is not None:
        return crop_end
    total = probe_duration(tmp_path)
    return min(total, MAX_REFERENCE_DURATION)


@router.get("", response_model=list[VoiceProfileResponse])
async def list_voices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VoiceProfile).order_by(
            VoiceProfile.last_used_at.desc().nullslast(),
            VoiceProfile.created_at.desc(),
        )
    )
    return result.scalars().all()


@router.get("/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice(profile_id: str, db: AsyncSession = Depends(get_db)):
    profile = await db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    return profile


@router.get("/{profile_id}/audio")
async def get_voice_audio(profile_id: str, db: AsyncSession = Depends(get_db)):
    profile = await db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    audio_path = _resolve_audio_path(profile.id)
    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(audio_path), media_type="audio/wav")


@router.post("", response_model=VoiceProfileResponse, status_code=201)
async def create_voice(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    transcript: Optional[str] = Form(None),
    file: UploadFile = File(...),
    crop_start: float = Form(0.0),
    crop_end: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    profile_id = str(uuid.uuid4())
    voice_dir = settings.VOICES_DIR / profile_id
    voice_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix if file.filename else ".audio"
    tmp_path = voice_dir / f"source{suffix}"

    try:
        content = await file.read()
        with open(tmp_path, "wb") as f_:
            f_.write(content)

        crop_end_val = _effective_crop_end(tmp_path, crop_end)
        output_path = voice_dir / "reference.wav"

        meta = process_audio(
            source_path=tmp_path,
            output_path=output_path,
            crop_start=crop_start,
            crop_end=crop_end_val,
            source_filename=file.filename or "",
        )

    except AudioPreprocessingError as exc:
        shutil.rmtree(voice_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        shutil.rmtree(voice_dir, ignore_errors=True)
        logger.exception("Unexpected error processing audio for new voice profile")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)

    now = datetime.now(timezone.utc)
    write_metadata_json(
        voice_dir / "metadata.json",
        profile_id=profile_id,
        name=name,
        meta=meta,
        language=language,
        transcript=transcript,
        created_at=now.isoformat(),
    )

    profile = VoiceProfile(
        id=profile_id,
        name=name,
        description=description,
        language=language,
        transcript=transcript,
        audio_filename="reference.wav",
        audio_duration=meta["duration"],
        meta=meta,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    logger.info("Created voice profile %s (%s, %.2fs, src=%s)", profile_id, name, meta["duration"], meta["source_format"])
    return profile


@router.put("/{profile_id}", response_model=VoiceProfileResponse)
async def update_voice(
    profile_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    transcript: Optional[str] = Form(None),
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
    if transcript is not None:
        profile.transcript = transcript

    if file is not None and file.filename:
        voice_dir = settings.VOICES_DIR / profile.id
        voice_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename).suffix if file.filename else ".audio"
        tmp_path = voice_dir / f"source{suffix}"

        try:
            content = await file.read()
            with open(tmp_path, "wb") as f_:
                f_.write(content)

            crop_end_val = _effective_crop_end(tmp_path, crop_end)
            output_path = voice_dir / "reference.wav"

            meta = process_audio(
                source_path=tmp_path,
                output_path=output_path,
                crop_start=crop_start,
                crop_end=crop_end_val,
                source_filename=file.filename or "",
            )

        except AudioPreprocessingError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            logger.exception("Unexpected error processing audio for profile %s", profile_id)
            raise HTTPException(status_code=500, detail=f"Audio processing failed: {exc}")
        finally:
            tmp_path.unlink(missing_ok=True)

        # Refresh metadata.json
        meta_path = voice_dir / "metadata.json"
        write_metadata_json(
            meta_path,
            profile_id=profile.id,
            name=profile.name if name is None else name,
            meta=meta,
            language=profile.language if language is None else language,
            transcript=profile.transcript if transcript is None else transcript,
            created_at=profile.created_at.isoformat() if profile.created_at else None,
        )

        profile.audio_filename = "reference.wav"
        profile.audio_duration = meta["duration"]
        profile.meta = meta
        omnivoice_service.invalidate_voice_cache(profile.id)
        logger.info("Updated audio for profile %s (%.2fs, src=%s)", profile_id, meta["duration"], meta["source_format"])

    await db.commit()
    await db.refresh(profile)
    logger.info("Updated voice profile %s", profile_id)
    return profile


@router.delete("/{profile_id}")
async def delete_voice(profile_id: str, db: AsyncSession = Depends(get_db)):
    profile = await db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    voice_dir = settings.VOICES_DIR / profile.id
    if voice_dir.exists():
        shutil.rmtree(voice_dir)
    omnivoice_service.invalidate_voice_cache(profile.id)
    await db.delete(profile)
    await db.commit()
    logger.info("Deleted voice profile %s", profile_id)
    return {"detail": "Voice profile deleted"}
