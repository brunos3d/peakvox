"""Public REST API (`/api/v1`).

Authenticated with an API key (``Authorization: Bearer ov_live_…`` or ``X-API-Key``).
Voices are addressed externally by their stable ``public_voice_id``. Endpoints reuse the
existing voice + generation services so behavior matches the app exactly.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db import ApiKey, GenerationJob, VoiceProfile
from app.schemas.api import (
    TextToSpeechRequest,
    TextToSpeechUrlResponse,
    V1Voice,
    V1VoiceDetail,
    V1VoiceList,
)
from app.services.api_keys import extract_api_token, verify_api_key
from app.services.storage import storage
from app.services.omnivoice_service import omnivoice_service
from app.services.voice_metadata import characteristics_from_defaults
from app.services.voice_repository import get_voice_by_public_id, list_voices_page
from app.utils.streaming import stream_object
from app.api.voices import _process_and_upload, resolve_voice_audio_key
from app.api.generation import AUDIO_FORMATS, _ensure_format, _process_job

logger = logging.getLogger(__name__)
router = APIRouter()

# Public API enforces a shorter reference-audio limit than the app.
PUBLIC_REF_AUDIO_LIMIT_S = 10.0


async def enforce_rate_limit(key: ApiKey) -> None:
    """Rate-limit hook (no-op in Community Edition).

    Cloud/Enterprise editions plug a real limiter (per-key quotas, token buckets) here
    without touching call sites.
    """
    return None


async def require_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """Authenticate the request via API key, returning the key record."""
    token = extract_api_token(authorization, x_api_key)
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key")
    key = await verify_api_key(db, token)
    if key is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    await enforce_rate_limit(key)
    return key


def _to_detail(voice: VoiceProfile) -> V1VoiceDetail:
    return V1VoiceDetail(
        voiceId=voice.public_voice_id,
        name=voice.name,
        language=voice.language,
        languageCode=voice.language_code,
        description=voice.description,
        usageCount=voice.usage_count,
        characteristics=voice.characteristics,
        createdAt=voice.created_at,
    )


@router.get("/voices", response_model=V1VoiceList)
async def v1_list_voices(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    _key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    items, next_cursor = await list_voices_page(db, scope="mine", limit=limit, cursor=cursor)
    return V1VoiceList(
        voices=[
            V1Voice(voiceId=v.public_voice_id, name=v.name, language=v.language)
            for v in items
        ],
        nextCursor=next_cursor,
    )


@router.get("/voices/{voice_id}", response_model=V1VoiceDetail)
async def v1_get_voice(
    voice_id: str,
    _key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    voice = await get_voice_by_public_id(db, voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found")
    return _to_detail(voice)


@router.post("/voices", response_model=V1VoiceDetail, status_code=201)
async def v1_create_voice(
    name: str = Form(...),
    transcript: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    language_code: Optional[str] = Form(None),
    file: UploadFile = File(...),
    _key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    profile_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        # crop_end caps the reference at the public 10s limit (server-side enforcement).
        meta = await _process_and_upload(
            profile_id, file, 0.0, PUBLIC_REF_AUDIO_LIMIT_S,
            name=name, language=language, transcript=transcript,
            created_at=now.isoformat(),
        )
    except Exception as exc:
        await storage.delete_prefix(f"voices/{profile_id}/")
        raise HTTPException(status_code=422, detail=f"Audio processing failed: {exc}")

    voice = VoiceProfile(
        id=profile_id,
        name=name,
        language=language,
        language_code=language_code,
        transcript=transcript,
        audio_filename="reference.wav",
        audio_duration=meta["duration"],
        meta=meta,
        characteristics=characteristics_from_defaults(None, language=language),
    )
    db.add(voice)
    await db.commit()
    await db.refresh(voice)
    logger.info("Created voice %s via API (%s)", voice.public_voice_id, profile_id)
    return _to_detail(voice)


@router.delete("/voices/{voice_id}")
async def v1_delete_voice(
    voice_id: str,
    _key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    voice = await get_voice_by_public_id(db, voice_id)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found")
    await storage.delete_prefix(f"voices/{voice.id}/")
    omnivoice_service.invalidate_voice_cache(voice.id)
    await db.delete(voice)
    await db.commit()
    return {"deleted": voice_id}


@router.post("/text-to-speech")
async def v1_text_to_speech(
    payload: TextToSpeechRequest,
    request: Request,
    response: str = Query("stream", pattern="^(stream|url)$"),
    _key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Synchronously generate speech and return it as a stream or a download URL.

    The pipeline is the same job-based generation used by the app, so a voice's saved
    generation defaults (and voice design) are applied automatically.
    """
    if not omnivoice_service.is_loaded:
        raise HTTPException(status_code=503, detail="Model is still loading")

    voice = await get_voice_by_public_id(db, payload.voiceId)
    if voice is None:
        raise HTTPException(status_code=404, detail="Voice not found")
    ref_key = await resolve_voice_audio_key(voice.id)
    if not ref_key:
        raise HTTPException(status_code=404, detail="Voice audio not found")

    # Apply the voice's saved defaults so the API matches in-app behavior (Sub-project E).
    defaults = voice.generation_defaults or {}
    voice_design = defaults.get("voice_design") or []
    gen_params = {
        "num_step": defaults.get("num_step", 32),
        "guidance_scale": defaults.get("guidance_scale", 2.0),
        "speed": defaults.get("speed"),
        "duration": defaults.get("duration"),
        "t_shift": defaults.get("t_shift", 0.1),
        "denoise": defaults.get("denoise", True),
    }

    output_key = f"generated/{os.urandom(8).hex()}.wav"
    job = GenerationJob(
        text=payload.text,
        voice_profile_id=voice.id,
        ref_audio_path=ref_key,
        ref_text=voice.transcript,
        language=payload.language or voice.language_code,
        instruct=", ".join(voice_design) if voice_design else None,
        generation_params=gen_params,
        output_path=output_key,
    )
    db.add(job)
    voice.usage_count = (voice.usage_count or 0) + 1
    voice.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)

    # Run synchronously — the public API returns the finished audio in one call.
    await _process_job(job.id)
    await db.refresh(job)
    if job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=500, detail=job.error_message or "Generation failed")

    fmt = payload.format
    filename = Path(job.output_path).name
    if response == "url":
        audio_url = (
            f"/audio/{filename}" if fmt == "wav" else f"/convert/{fmt}/{filename}"
        )
        return TextToSpeechUrlResponse(
            jobId=job.id, audioUrl=audio_url, format=fmt, durationSeconds=job.audio_duration
        )

    out_key = job.output_path if fmt == "wav" else await _ensure_format(job.output_path, fmt)
    content_type = "audio/wav" if fmt == "wav" else AUDIO_FORMATS[fmt]["content_type"]
    return await stream_object(
        out_key, request=request, content_type=content_type,
        download_name=f"omnivoice-{job.id}.{fmt}",
    )
