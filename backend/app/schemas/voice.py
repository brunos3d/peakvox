from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator

# Lifecycle status of a voice. Stored as a string column; constrained here.
VoiceStatus = Literal["ready", "archived", "processing", "failed"]


class VoiceCharacteristics(BaseModel):
    """Derived, read-only snapshot of a voice's traits.

    Generated from ``voice_design`` (the source of truth) + preset tags by
    ``services.voice_metadata.derive_characteristics``. Never edited by hand;
    filtering / search / pagination read this instead of recomputing.
    """

    gender: Optional[str] = None
    age_group: Optional[str] = None
    accent: Optional[str] = None
    pitch: Optional[str] = None
    style_tags: list[str] = []
    speaking_speed: Optional[str] = None
    emotional_range: Optional[str] = None


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
    language_code: Optional[str] = Field(None, max_length=16)
    transcript: Optional[str] = None
    preset_tags: Optional[list[str]] = None


class VoiceProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    language: Optional[str] = None
    language_code: Optional[str] = Field(None, max_length=16)
    transcript: Optional[str] = None
    preset_tags: Optional[list[str]] = None


class VoiceSourceAssetResponse(BaseModel):
    id: str
    asset_type: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    audio_duration: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PreviewSummary(BaseModel):
    """Derived preview availability for a voice.

    Always computed, never stored. Before the ``voice_previews`` table exists
    (Phase E), this is heuristically derived from ``audio_duration`` +
    ``creation_source``. After Phase E it is computed from the actual preview
    records.
    """

    origin: str  # "reference" | "provider" | "generated" | "user" | "marketplace" | "none"
    count: int = 0
    languages: list[str] = []


class VoiceProfileResponse(BaseModel):
    id: str
    public_voice_id: str
    owner_id: str
    name: str
    description: Optional[str]
    language: Optional[str]
    language_code: Optional[str] = None
    transcript: Optional[str]
    audio_filename: str
    audio_duration: Optional[float]
    meta: Optional[dict[str, Any]]
    generation_defaults: Optional[VoiceGenerationDefaults] = None
    preset_tags: Optional[list[str]] = None
    characteristics: Optional[dict[str, Any]] = None
    is_public: bool = False
    is_community_voice: bool = False
    is_preset_voice: bool = False
    is_favorite: bool = False
    status: VoiceStatus = "ready"
    usage_count: int = 0
    creation_source: str = "SOURCE_ASSET"
    compatible_models: list[str] = []
    preview_summary: PreviewSummary = PreviewSummary(origin="none")
    source_asset: Optional[VoiceSourceAssetResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _derive_creation_source(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "creation_source" not in data:
                data["creation_source"] = "PRESET_VOICE" if data.get("is_preset_voice") else "SOURCE_ASSET"
        elif hasattr(data, "is_preset_voice") and not getattr(data, "creation_source", None):
            # SQLAlchemy ORM path — ``VoiceProfile`` has no ``creation_source`` column,
            # so we derive it from ``is_preset_voice`` here too. Without this branch
            # every voice would fall back to the default ``SOURCE_ASSET`` and the
            # compat resolver would never match PRESET_VOICE-only adapters like Kokoro.
            data.creation_source = "PRESET_VOICE" if data.is_preset_voice else "SOURCE_ASSET"
        return data

    @model_validator(mode="after")
    def _derive_preview_summary(self) -> "VoiceProfileResponse":
        has_audio = (self.audio_duration or 0) > 0 and bool(self.audio_filename)
        if has_audio:
            origin_map = {
                "SOURCE_ASSET": "reference",
                "PRESET_VOICE": "provider",
            }
            self.preview_summary = PreviewSummary(
                origin=origin_map.get(self.creation_source, "reference"),
                count=1,
            )
        return self


class VoiceListPage(BaseModel):
    """One page of the paginated voice listing."""

    items: list[VoiceProfileResponse]
    next_cursor: Optional[str] = None


class FavoriteUpdate(BaseModel):
    is_favorite: bool
