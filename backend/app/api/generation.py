import asyncio
import hashlib
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.models.db import GenerationJob, VoiceProfile
from app.schemas.job import GenerationRequest, JobResponse
from app.services.model_registry import model_registry
from app.services.omnivoice_service import omnivoice_service
from app.services.storage import storage
from app.services.tag_validation import find_unsupported_tags
from app.services.voice_variant_repository import resolve_variant_stamp
from app.api.voices import resolve_voice_audio_key
from app.utils.streaming import stream_object

logger = logging.getLogger(__name__)
router = APIRouter()


def _audio_url_for(job: GenerationJob) -> Optional[str]:
    """Public audio URL for a completed job (preserves the /audio/{name} contract)."""
    if job.status == "completed" and job.output_path:
        return f"/audio/{Path(job.output_path).name}"
    return None


def _job_to_response(job: GenerationJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        status=job.status,
        text=job.text,
        model_id=job.model_id,
        voice_profile_id=job.voice_profile_id,
        language=job.language,
        instruct=job.instruct,
        generation_params=job.generation_params,
        audio_url=_audio_url_for(job),
        audio_duration=job.audio_duration,
        error_message=job.error_message,
        logs=job.logs,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


# Supported on-demand transcode targets keyed by extension. Each entry carries
# the ffmpeg codec/quality flags and the MIME type used when streaming.
AUDIO_FORMATS = {
    "mp3": {
        "codec": ["-codec:a", "libmp3lame", "-qscale:a", "2"],
        "content_type": "audio/mpeg",
    },
    "ogg": {
        "codec": ["-codec:a", "libvorbis", "-qscale:a", "5"],
        "content_type": "audio/ogg",
    },
}


async def _ensure_format(wav_key: str, fmt: str) -> str:
    """Ensure a transcoded sibling (e.g. MP3/OGG) of a generated WAV exists; return its key."""
    spec = AUDIO_FORMATS[fmt]
    ext = f".{fmt}"
    out_key = wav_key[: -len(".wav")] + ext if wav_key.endswith(".wav") else wav_key + ext
    if await storage.exists(out_key):
        return out_key
    if not await storage.exists(wav_key):
        raise HTTPException(status_code=404, detail="Audio file not found")

    wav_tmp = await storage.download_to_temp(wav_key, suffix=".wav")
    out_tmp = wav_tmp.with_suffix(ext)
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_tmp), *spec["codec"], str(out_tmp)],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("ffmpeg %s conversion failed for %s: %s", fmt, wav_key, result.stderr.decode())
            raise HTTPException(status_code=500, detail=f"Failed to convert audio to {fmt.upper()}")
        await storage.put_file(out_key, out_tmp, spec["content_type"])
    finally:
        wav_tmp.unlink(missing_ok=True)
        out_tmp.unlink(missing_ok=True)
    return out_key


@router.post("/generate")
async def create_generation_job(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db),
):
    if not omnivoice_service.is_loaded:
        raise HTTPException(status_code=503, detail="Model is still loading. Please try again.")

    # Reject immediately if the GPU is already busy — prevents queue build-up
    # and gives the frontend an actionable signal rather than a silent wait.
    if model_registry.is_generating or omnivoice_service.is_generating:
        raise HTTPException(
            status_code=409,
            detail="A generation is already in progress. Please wait for it to complete.",
        )

    # Resolve and validate the requested model (None = platform default).
    try:
        model = model_registry.get_or_default(request.model_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Model '{request.model_id}' not found")
    if model.status == "disabled":
        raise HTTPException(status_code=409, detail=f"Model '{model.id}' is not available")

    # Authoritative tag validation: reject inline tags the model does not support.
    bad_tags = find_unsupported_tags(request.text, model.supported_tags)
    if bad_tags:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Unsupported tags for model '{model.id}'",
                "unsupported_tags": bad_tags,
                "model_id": model.id,
            },
        )

    ref_audio_key: str | None = None
    job_voice_id: str | None = None
    job_variant_id: str | None = None

    if request.voice_profile_id:
        profile = await db.get(VoiceProfile, request.voice_profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Voice profile not found")
        ref_audio_key = await resolve_voice_audio_key(profile.id)
        if not ref_audio_key:
            raise HTTPException(status_code=404, detail="Voice profile audio file not found")
        # Usage analytics — powers Recently Used / Popular / Trending later.
        profile.last_used_at = datetime.now(timezone.utc)
        profile.usage_count = (profile.usage_count or 0) + 1
        # PeakVox Phase 3: stamp the resolved Voice identity + its model-specific VoiceVariant
        # on the job (additive). The Voice id reuses the profile UUID; variant may be None when
        # the selected model has no built variant yet (generation still uses the reference audio).
        job_voice_id, job_variant_id = await resolve_variant_stamp(
            db, voice_internal_id=profile.id, model_id=model.id
        )

    gen_params = request.model_dump(
        exclude={"text", "model_id", "voice_profile_id", "ref_text", "language", "instruct"}
    )

    output_key = f"generated/{os.urandom(8).hex()}.wav"

    job = GenerationJob(
        text=request.text,
        model_id=model.id,
        voice_profile_id=request.voice_profile_id,
        voice_id=job_voice_id,
        voice_variant_id=job_variant_id,
        ref_audio_path=ref_audio_key,
        ref_text=request.ref_text,
        language=request.language,
        instruct=request.instruct,
        generation_params=gen_params,
        output_path=output_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    text_hash = hashlib.sha256(request.text.encode()).hexdigest()[:8]
    logger.info(
        "Job created | job_id=%s voice=%s text_hash=%s text_len=%d lang=%s instruct=%s output=%s",
        job.id,
        request.voice_profile_id or "none",
        text_hash,
        len(request.text),
        request.language or "auto",
        bool(request.instruct),
        output_key,
    )

    asyncio.create_task(_process_job(job.id))

    return {"job_id": job.id}


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    stmt = select(GenerationJob).order_by(GenerationJob.created_at.desc())
    if status:
        stmt = stmt.where(GenerationJob.status == status)
    stmt = stmt.limit(limit).offset(max(0, offset))
    jobs = (await db.execute(stmt)).scalars().all()
    return [_job_to_response(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.output_path:
        wav_key = job.output_path
        await storage.delete(wav_key)
        if wav_key.endswith(".wav"):
            base = wav_key[: -len(".wav")]
            for fmt in AUDIO_FORMATS:
                await storage.delete(f"{base}.{fmt}")
    await db.delete(job)
    await db.commit()
    logger.info("Deleted job %s", job_id)
    return {"detail": "Job deleted"}


@router.get("/jobs/{job_id}/audio")
async def get_job_audio(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    job = await db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    return await stream_object(
        job.output_path, request=request, content_type="audio/wav",
        download_name=f"omnivoice-{job.id}.wav",
    )


@router.get("/jobs/{job_id}/audio/{fmt}")
async def get_job_audio_converted(job_id: str, fmt: str, request: Request, db: AsyncSession = Depends(get_db)):
    if fmt not in AUDIO_FORMATS:
        raise HTTPException(status_code=404, detail="Unsupported audio format")
    job = await db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed" or not job.output_path:
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    out_key = await _ensure_format(job.output_path, fmt)
    return await stream_object(
        out_key, request=request, content_type=AUDIO_FORMATS[fmt]["content_type"],
        download_name=f"omnivoice-{job.id}.{fmt}",
    )


@router.get("/convert/{fmt}/{filename:path}")
async def convert_audio(fmt: str, filename: str, request: Request):
    if fmt not in AUDIO_FORMATS:
        raise HTTPException(status_code=404, detail="Unsupported audio format")
    if not filename.endswith(".wav"):
        raise HTTPException(status_code=404, detail="Audio file not found")
    wav_key = f"generated/{filename}"
    out_key = await _ensure_format(wav_key, fmt)
    base = Path(filename).stem
    return await stream_object(
        out_key, request=request, content_type=AUDIO_FORMATS[fmt]["content_type"],
        download_name=f"{base}.{fmt}",
    )


async def _process_job(job_id: str) -> None:
    """Background task: run inference for a single job, fully isolated by job_id.

    The OmniVoice model reads/writes local paths, so the reference object is
    downloaded to scratch first and the result is uploaded to MinIO afterwards.
    """

    # ── 1. Load the exact job payload from the database ──────────────────────
    async with AsyncSessionLocal() as session:
        job = await session.get(GenerationJob, job_id)
        if not job:
            logger.warning("Job %s not found — skipping", job_id)
            return

        voice_name: str | None = None
        if job.voice_profile_id:
            profile = await session.get(VoiceProfile, job.voice_profile_id)
            voice_name = profile.name if profile else None

        text_hash = hashlib.sha256(job.text.encode()).hexdigest()[:8]
        logger.info(
            "Job processing start | job_id=%s voice_id=%s voice_name=%s "
            "text_hash=%s text_len=%d lang=%s instruct=%s",
            job_id,
            job.voice_profile_id or "none",
            voice_name or "none",
            text_hash,
            len(job.text),
            job.language or "auto",
            bool(job.instruct),
        )

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

        # Snapshot fields needed outside the session
        job_text = job.text
        job_model_id = job.model_id
        job_voice_id = job.voice_profile_id
        job_ref_key = job.ref_audio_path
        job_ref_text = job.ref_text
        job_language = job.language
        job_instruct = job.instruct
        job_output_key = job.output_path
        job_params = job.generation_params or {}

    # ── 2. Stage local scratch files ─────────────────────────────────────────
    local_ref: Optional[Path] = None
    local_output = settings_tmp_output(job_output_key)
    try:
        if job_ref_key:
            local_ref = await storage.download_to_temp(job_ref_key, suffix=".wav")

        # ── 3. Run inference via the registry (resolves/loads the model) ─────
        duration, logs = await model_registry.generate(
            job_model_id,
            text=job_text,
            output_path=local_output,
            voice_profile_id=job_voice_id,
            ref_audio_path=str(local_ref) if local_ref else None,
            ref_text=job_ref_text,
            language=job_language,
            instruct=job_instruct,
            params=job_params,
            job_id=job_id,
        )

        # ── 4. Upload result to MinIO ────────────────────────────────────────
        await storage.put_file(job_output_key, local_output, "audio/wav")

        async with AsyncSessionLocal() as session:
            job = await session.get(GenerationJob, job_id)
            job.status = "completed"
            job.audio_duration = duration
            job.logs = logs
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

        logger.info(
            "Job completed | job_id=%s duration=%.2fs voice=%s text_hash=%s",
            job_id, duration, job_voice_id or "none", text_hash,
        )

    except Exception as exc:
        logger.exception("Job failed | job_id=%s error=%s", job_id, exc)
        async with AsyncSessionLocal() as session:
            job = await session.get(GenerationJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                job.logs = (job.logs or []) + [f"ERROR: {exc}"]
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
    finally:
        if local_ref:
            local_ref.unlink(missing_ok=True)
        local_output.unlink(missing_ok=True)


def settings_tmp_output(output_key: str) -> Path:
    """Local scratch path the model writes to before the WAV is uploaded."""
    from app.core.config import settings
    settings.TMP_DIR.mkdir(parents=True, exist_ok=True)
    return settings.TMP_DIR / Path(output_key).name
