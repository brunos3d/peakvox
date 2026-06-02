"""Public audio serving — proxy-streams generated audio from MinIO.

Preserves the historical ``/audio/{filename}`` URL contract (previously a static
file mount); the frontend's ``audio_url`` values are unchanged.
"""

from fastapi import APIRouter, Request

from app.utils.streaming import stream_object

router = APIRouter()


@router.get("/audio/{filename}")
async def get_generated_audio(filename: str, request: Request):
    return await stream_object(f"generated/{filename}", request=request)
