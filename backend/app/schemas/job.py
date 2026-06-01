from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice_profile_id: Optional[str] = None
    ref_text: Optional[str] = None
    language: Optional[str] = None
    instruct: Optional[str] = None
    num_step: int = Field(32, ge=1, le=200)
    guidance_scale: float = Field(2.0, ge=0.0, le=10.0)
    speed: Optional[float] = Field(None, ge=0.1, le=5.0)
    duration: Optional[float] = Field(None, ge=1.0, le=120.0)
    t_shift: float = Field(0.1, ge=0.0, le=1.0)
    denoise: bool = True


class JobResponse(BaseModel):
    id: str
    status: str
    text: str
    voice_profile_id: Optional[str]
    language: Optional[str]
    instruct: Optional[str]
    generation_params: Optional[dict[str, Any]]
    audio_url: Optional[str]
    audio_duration: Optional[float]
    error_message: Optional[str]
    logs: Optional[list[str]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}
