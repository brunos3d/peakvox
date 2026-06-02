import asyncio
import hashlib
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.config import settings
from app.models.db import GenerationJob, VoiceProfile
from app.schemas.job import GenerationRequest, JobResponse
from app.services.omnivoice_service import omnivoice_service
from app.utils.audio import get_audio_duration, load_audio_as_wav

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate")
async def create_generation_job(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db),
):
    if not omnivoice_service.is_loaded:
        raise HTTPException(status_code=503, detail="Model is still loading. Please try again.")

    # Reject immediately if the GPU is already busy — prevents queue build-up
    # and gives the frontend an actionable signal rather than a silent wait.
    if omnivoice_service.is_generating:
        raise HTTPException(
            status_code=409,
            detail="A generation is already in progress. Please wait for it to complete.",
        )

    ref_audio_path: str | None = None

    if request.voice_profile_id:
        profile = await db.get(VoiceProfile, request.voice_profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Voice profile not found")
        for _name in ("reference.wav", "voice.wav"):
            audio_file = settings.VOICES_DIR / profile.id / _name
            if audio_file.exists():
                break
        else:
            raise HTTPException(status_code=404, detail="Voice profile audio file not found")
        ref_audio_path = str(audio_file)
        profile.last_used_at = datetime.now(timezone.utc)

    gen_params = request.model_dump(exclude={"text", "voice_profile_id", "ref_text", "language", "instruct"})

    output_filename = f"{os.urandom(8).hex()}.wav"
    output_path = str(settings.GENERATED_DIR / output_filename)

    job = GenerationJob(
        text=request.text,
        voice_profile_id=request.voice_profile_id,
        ref_audio_path=ref_audio_path,
        ref_text=request.ref_text,
        language=request.language,
        instruct=request.instruct,
        generation_params=gen_params,
        output_path=output_path,
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
        output_filename,
    )

    asyncio.create_task(_process_job(job.id))

    return {"job_id": job.id}


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    audio_url = None
    if job.status == "completed" and job.output_path:
        filename = Path(job.output_path).name
        audio_url = f"/audio/{filename}"

    return JobResponse(
        id=job.id,
        status=job.status,
        text=job.text,
        voice_profile_id=job.voice_profile_id,
        language=job.language,
        instruct=job.instruct,
        generation_params=job.generation_params,
        audio_url=audio_url,
        audio_duration=job.audio_duration,
        error_message=job.error_message,
        logs=job.logs,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs/{job_id}/audio")
async def get_job_audio(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(job.output_path, media_type="audio/wav", filename=f"omnivoice-{job.id}.wav")


@router.get("/jobs/{job_id}/audio/mp3")
async def get_job_audio_mp3(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    wav_path = job.output_path
    mp3_path = wav_path.replace(".wav", ".mp3")

    if not Path(mp3_path).exists():
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("ffmpeg MP3 conversion failed for job %s: %s", job_id, result.stderr.decode())
            raise HTTPException(status_code=500, detail="Failed to convert audio to MP3")

    return FileResponse(mp3_path, media_type="audio/mpeg", filename=f"omnivoice-{job.id}.mp3")


@router.get("/convert/mp3/{filename:path}")
async def convert_to_mp3(filename: str):
    wav_path = str(settings.GENERATED_DIR / filename)
    if not wav_path.endswith(".wav") or not Path(wav_path).exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    mp3_path = wav_path.replace(".wav", ".mp3")
    if not Path(mp3_path).exists():
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("ffmpeg conversion failed: %s", result.stderr.decode())
            raise HTTPException(status_code=500, detail="Failed to convert audio to MP3")
    base = Path(filename).stem
    return FileResponse(mp3_path, media_type="audio/mpeg", filename=f"{base}.mp3")


async def _process_job(job_id: str) -> None:
    """Background task: run inference for a single job, fully isolated by job_id."""

    # ── 1. Load the exact job payload from the database ──────────────────────
    async with AsyncSessionLocal() as session:
        job = await session.get(GenerationJob, job_id)
        if not job:
            logger.warning("Job %s not found — skipping", job_id)
            return

        # Resolve voice name for structured logging
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

    # ── 2. Run inference — all inputs come exclusively from the job record ────
    try:
        params = job.generation_params or {}

        duration, logs = await omnivoice_service.generate_async(
            text=job.text,
            output_path=Path(job.output_path),
            voice_profile_id=job.voice_profile_id,
            ref_audio_path=job.ref_audio_path,
            ref_text=job.ref_text,
            language=job.language,
            instruct=job.instruct,
            num_step=params.get("num_step", 32),
            guidance_scale=params.get("guidance_scale", 2.0),
            speed=params.get("speed"),
            duration=params.get("duration"),
            t_shift=params.get("t_shift", 0.1),
            denoise=params.get("denoise", True),
            job_id=job_id,
        )

        # ── 3. Persist successful result ──────────────────────────────────────
        async with AsyncSessionLocal() as session:
            job = await session.get(GenerationJob, job_id)
            job.status = "completed"
            job.audio_duration = duration
            job.logs = logs
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

        logger.info(
            "Job completed | job_id=%s duration=%.2fs voice=%s text_hash=%s",
            job_id,
            duration,
            job.voice_profile_id or "none",
            text_hash,
        )

    except Exception as exc:
        # ── 4. Persist failure — GPU cleanup already happened in _do_generate's
        #       finally block, so VRAM is safe regardless of where the error was.
        logger.exception("Job failed | job_id=%s error=%s", job_id, exc)
        async with AsyncSessionLocal() as session:
            job = await session.get(GenerationJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                job.logs = (job.logs or []) + [f"ERROR: {exc}"]
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
