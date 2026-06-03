"""Schemas for API-key management and the public `/api/v1` surface.

The public API intentionally uses camelCase field names (voiceId, languageCode, …) to
match common SDK/REST conventions and the brief's examples, independent of the internal
snake_case models.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ── API key management (internal dashboard) ──────────────────────────────────
class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    status: str
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(ApiKeyResponse):
    """Returned only at creation — carries the raw key exactly once."""

    key: str


# ── Public /api/v1 voice resources ───────────────────────────────────────────
class V1Voice(BaseModel):
    voiceId: str
    name: str
    language: Optional[str] = None


class V1VoiceDetail(V1Voice):
    languageCode: Optional[str] = None
    description: Optional[str] = None
    usageCount: int = 0
    characteristics: Optional[dict[str, Any]] = None
    createdAt: datetime


class V1VoiceList(BaseModel):
    voices: list[V1Voice]
    nextCursor: Optional[str] = None


class TextToSpeechRequest(BaseModel):
    voiceId: str
    text: str = Field(..., min_length=1)
    modelId: Optional[str] = None
    language: Optional[str] = None
    format: Literal["wav", "mp3"] = "wav"


class TextToSpeechUrlResponse(BaseModel):
    """Returned when the caller requests a download URL instead of a stream."""

    jobId: str
    audioUrl: str
    format: str
    durationSeconds: Optional[float] = None
