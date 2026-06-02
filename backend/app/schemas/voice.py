from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class VoiceGenerationDefaults(BaseModel):
    num_step: int = 32
    guidance_scale: float = 2.0
    speed: Optional[float] = None
    duration: Optional[float] = None
    t_shift: float = 0.1
    denoise: bool = True
    use_gpu: bool = True
    # Structured Voice Design attributes (one per category). Old profiles whose
    # stored JSON lacks this field stay valid via the empty-list default.
    voice_design: list[str] = []


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
    generation_defaults: Optional[VoiceGenerationDefaults] = None
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}
