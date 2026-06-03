import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Float, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base
from app.utils.ids import generate_public_voice_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """Minimal account record. SaaS-ready, but no authentication exists yet — the
    self-hosted Community Edition seeds a single system user (``settings.LOCAL_OWNER_ID``)
    that owns every resource."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    handle: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ApiKey(Base):
    """A hashed API key for the public REST API (`/api/v1`).

    The raw key (``ov_live_…``) is shown to the caller exactly once at creation and
    never stored — only its sha256 hash and a short display prefix. Keys belong to the
    local owner today, but ``owner_id`` keeps the schema multi-tenant ready."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Display-only prefix, e.g. "ov_live_1a2b3c4d" — safe to show in the dashboard.
    prefix: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    owner_id: Mapped[str] = mapped_column(
        String(36), index=True, default=lambda: settings.LOCAL_OWNER_ID
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    # Internal UUID (primary key, used for storage paths). Unchanged.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Public, stable, never-changing external identifier (APIs/SDKs/UI/community/export).
    public_voice_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=generate_public_voice_id
    )
    owner_id: Mapped[str] = mapped_column(
        String(36), index=True, default=lambda: settings.LOCAL_OWNER_ID
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generation_defaults: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Explicit tags + derived (read-only) characteristics snapshot.
    preset_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    characteristics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Visibility flags — schema only this cycle; Community/Publish UIs stay disabled.
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_community_voice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_preset_voice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    voice_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ref_audio_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ref_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    instruct: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    audio_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
