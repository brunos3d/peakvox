from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class VoiceProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    language: Optional[str] = None
    transcript: Optional[str] = None


class VoiceProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    language: Optional[str] = None
    transcript: Optional[str] = None


class VoiceProfileResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    language: Optional[str]
    transcript: Optional[str]
    audio_filename: str
    audio_duration: Optional[float]
    meta: Optional[dict[str, Any]]
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}
