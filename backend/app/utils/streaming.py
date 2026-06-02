"""HTTP streaming of MinIO objects with Range support.

Range support matters: the audio player seeks by issuing ``Range`` requests, so
proxy-streaming must honour them or scrubbing breaks.
"""

import logging
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from app.services.storage import storage

logger = logging.getLogger(__name__)


async def stream_object(
    key: str,
    request: Optional[Request] = None,
    content_type: Optional[str] = None,
    download_name: Optional[str] = None,
) -> StreamingResponse:
    """Stream an object from MinIO. Honours a ``Range`` header when present.

    Pass ``download_name`` to force an attachment (download); omit it for inline
    playback so the browser can stream/seek.
    """
    if not await storage.exists(key):
        raise HTTPException(status_code=404, detail="Audio file not found")

    size, ctype = await storage.stat(key)
    media_type = content_type or ctype
    headers: dict[str, str] = {"Accept-Ranges": "bytes"}
    if download_name:
        headers["Content-Disposition"] = f'attachment; filename="{download_name}"'

    range_header = request.headers.get("range") if request else None
    if range_header and range_header.startswith("bytes="):
        rng = range_header.split("=", 1)[1]
        start_s, _, end_s = rng.partition("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else size - 1
        end = min(end, size - 1)
        if start > end:
            raise HTTPException(status_code=416, detail="Requested range not satisfiable")
        length = end - start + 1
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(length)
        return StreamingResponse(
            storage.stream(key, offset=start, length=length),
            status_code=206,
            media_type=media_type,
            headers=headers,
        )

    headers["Content-Length"] = str(size)
    return StreamingResponse(storage.stream(key), media_type=media_type, headers=headers)
