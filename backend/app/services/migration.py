"""One-time, idempotent migration of legacy filesystem audio into MinIO.

Safe to run on every startup: it only uploads objects that are missing and only
rewrites DB path columns that still point at the local ``/data`` filesystem.
A fresh deployment (empty volume) makes this a no-op.
"""

import logging
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.db import GenerationJob
from app.services.storage import storage

logger = logging.getLogger(__name__)


def _content_type(path: Path) -> str:
    if path.suffix == ".wav":
        return "audio/wav"
    if path.suffix == ".mp3":
        return "audio/mpeg"
    if path.suffix == ".json":
        return "application/json"
    return "application/octet-stream"


def _fs_path_to_key(value: str) -> str:
    """Convert a stored filesystem path to its MinIO object key.

    /data/generated/x.wav        -> generated/x.wav
    /data/voices/{id}/ref.wav    -> voices/{id}/ref.wav
    Already-key values are returned unchanged.
    """
    if not value:
        return value
    prefix = str(settings.DATA_DIR).rstrip("/") + "/"
    if value.startswith(prefix):
        return value[len(prefix):]
    if value.startswith("/data/"):
        return value[len("/data/"):]
    return value


async def _upload_tree(local_root: Path, key_prefix: str) -> int:
    """Upload every file under local_root to ``{key_prefix}/<relative path>``."""
    if not local_root.exists():
        return 0
    count = 0
    for path in local_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(local_root).as_posix()
        key = f"{key_prefix}/{rel}"
        if await storage.exists(key):
            continue
        await storage.put_file(key, path, _content_type(path))
        count += 1
    return count


async def run_migration() -> None:
    uploaded = 0
    uploaded += await _upload_tree(settings.VOICES_DIR, "voices")
    uploaded += await _upload_tree(settings.GENERATED_DIR, "generated")

    rewritten = 0
    async with AsyncSessionLocal() as session:
        jobs = (await session.execute(select(GenerationJob))).scalars().all()
        for job in jobs:
            changed = False
            if job.output_path and (job.output_path.startswith("/data") or job.output_path.startswith(str(settings.DATA_DIR))):
                job.output_path = _fs_path_to_key(job.output_path)
                changed = True
            if job.ref_audio_path and (job.ref_audio_path.startswith("/data") or job.ref_audio_path.startswith(str(settings.DATA_DIR))):
                job.ref_audio_path = _fs_path_to_key(job.ref_audio_path)
                changed = True
            if changed:
                rewritten += 1
        if rewritten:
            await session.commit()

    if uploaded or rewritten:
        logger.info("MinIO migration: uploaded %d files, rewrote %d job paths", uploaded, rewritten)
