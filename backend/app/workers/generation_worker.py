import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.db import GenerationJob
from app.services.omnivoice_service import omnivoice_service
from app.core.config import settings

logger = logging.getLogger(__name__)


async def process_job(job_id: str) -> None:
    logger.info("Processing job %s", job_id)

    async with AsyncSessionLocal() as session:
        job = await session.get(GenerationJob, job_id)
        if not job:
            logger.warning("Job %s not found", job_id)
            return
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

    try:
        params = job.generation_params or {}
        output_path = Path(job.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        duration, logs = await omnivoice_service.generate_async(
            text=job.text,
            output_path=output_path,
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
        )

        async with AsyncSessionLocal() as session:
            job = await session.get(GenerationJob, job_id)
            job.status = "completed"
            job.audio_duration = duration
            job.logs = logs
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

        logger.info("Job %s completed (%.2fs)", job_id, duration)

    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        async with AsyncSessionLocal() as session:
            job = await session.get(GenerationJob, job_id)
            job.status = "failed"
            job.error_message = str(exc)
            job.logs = (job.logs or []) + [f"ERROR: {exc}"]
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()


async def poll_pending_jobs() -> None:
    """Re-process any pending jobs (useful after restart)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GenerationJob).where(GenerationJob.status == "pending")
        )
        pending = result.scalars().all()

    for job in pending:
        logger.info("Resuming pending job %s", job.id)
        asyncio.create_task(process_job(job.id))
