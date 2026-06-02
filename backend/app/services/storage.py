"""MinIO object-storage abstraction — the source of truth for all audio.

The OmniVoice inference path works exclusively with local file paths, so this
service supports a download-to-temp / upload-result pattern: objects are pulled
to local scratch for the model to read/write, and results are pushed back to
MinIO. Serving is done by proxy-streaming object bytes (with HTTP range support)
so the public ``/audio/...`` URL contract is preserved.

Key layout (single bucket):
    voices/{id}/reference.wav
    voices/{id}/metadata.json
    uploads/{name}
    generated/{name}.wav
    generated/{name}.mp3
"""

import asyncio
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Iterator, Optional

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self) -> None:
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        return self._client

    @property
    def bucket(self) -> str:
        return settings.MINIO_BUCKET

    # ── bucket lifecycle ────────────────────────────────────────────────────
    def ensure_bucket(self) -> None:
        """Create the bucket if it does not exist. Safe to call repeatedly."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            logger.info("Created MinIO bucket %s", self.bucket)

    # ── synchronous primitives ──────────────────────────────────────────────
    def _put_file(self, key: str, local_path: Path, content_type: str) -> None:
        self.client.fput_object(self.bucket, key, str(local_path), content_type=content_type)

    def _put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type
        )

    def _exists(self, key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error:
            return False

    def _stat(self, key: str) -> tuple[int, str]:
        st = self.client.stat_object(self.bucket, key)
        return st.size, (st.content_type or "application/octet-stream")

    def _download_to_temp(self, key: str, suffix: str) -> Path:
        settings.TMP_DIR.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(suffix=suffix, dir=str(settings.TMP_DIR))
        os.close(fd)
        self.client.fget_object(self.bucket, key, tmp)
        return Path(tmp)

    def _delete(self, key: str) -> None:
        try:
            self.client.remove_object(self.bucket, key)
        except S3Error:
            pass

    def _delete_prefix(self, prefix: str) -> None:
        for obj in self.client.list_objects(self.bucket, prefix=prefix, recursive=True):
            self.client.remove_object(self.bucket, obj.object_name)

    # ── async wrappers ──────────────────────────────────────────────────────
    async def put_file(self, key: str, local_path: Path, content_type: str) -> None:
        await asyncio.to_thread(self._put_file, key, local_path, content_type)

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._put_bytes, key, data, content_type)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._exists, key)

    async def stat(self, key: str) -> tuple[int, str]:
        return await asyncio.to_thread(self._stat, key)

    async def download_to_temp(self, key: str, suffix: str = "") -> Path:
        return await asyncio.to_thread(self._download_to_temp, key, suffix)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete, key)

    async def delete_prefix(self, prefix: str) -> None:
        await asyncio.to_thread(self._delete_prefix, prefix)

    # ── streaming (sync generator for StreamingResponse) ────────────────────
    def stream(self, key: str, offset: int = 0, length: int = 0) -> Iterator[bytes]:
        """Yield object bytes. ``length=0`` streams to the end from ``offset``."""
        resp = self.client.get_object(self.bucket, key, offset=offset, length=length)
        try:
            for chunk in resp.stream(64 * 1024):
                yield chunk
        finally:
            resp.close()
            resp.release_conn()


storage = StorageService()
