"""Voice lookup helpers.

External surfaces (public API, SDKs, Copy-Voice-ID) address voices by their stable
``public_voice_id``; internal code uses the UUID primary key. These helpers centralize
both lookups so future API work has a single entry point.
"""

import base64
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from sqlalchemy import String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db import VoiceProfile

VALID_SCOPES = ("mine", "recent", "community", "preset")
VALID_SORT_FIELDS = ("name", "created_at", "last_used_at", "language", "usage_count")
SortField = Literal["name", "created_at", "last_used_at", "language", "usage_count"]
SortDir = Literal["asc", "desc"]


async def get_voice_by_public_id(
    db: AsyncSession, public_voice_id: str
) -> Optional[VoiceProfile]:
    """Resolve a voice by its public, stable identifier (the external contract)."""
    result = await db.execute(
        select(VoiceProfile).where(VoiceProfile.public_voice_id == public_voice_id)
    )
    return result.scalar_one_or_none()


async def get_voice_by_internal_id(
    db: AsyncSession, voice_id: str
) -> Optional[VoiceProfile]:
    """Resolve a voice by its internal UUID primary key."""
    return await db.get(VoiceProfile, voice_id)


async def public_id_exists(db: AsyncSession, public_voice_id: str) -> bool:
    """True when a public_voice_id is already taken (used for collision-safe generation)."""
    result = await db.execute(
        select(VoiceProfile.id).where(VoiceProfile.public_voice_id == public_voice_id)
    )
    return result.first() is not None


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def _decode_cursor(cursor: Optional[str]) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(base64.urlsafe_b64decode(cursor.encode()).decode()))
    except Exception:
        return 0


def _characteristic(field: str):
    """JSON path accessor for a characteristics field (SQLite json_extract)."""
    return func.json_extract(VoiceProfile.characteristics, f"$.{field}")


async def list_voices_page(
    db: AsyncSession,
    *,
    scope: str = "mine",
    search: Optional[str] = None,
    language_code: Optional[str] = None,
    gender: Optional[str] = None,
    age_group: Optional[str] = None,
    accent: Optional[str] = None,
    favorite: Optional[bool] = None,
    limit: int = 24,
    cursor: Optional[str] = None,
    sort_by: Optional[SortField] = None,
    sort_dir: SortDir = "desc",
    creation_source: Optional[str] = None,
    provider: Optional[str] = None,
    recently_used: Optional[str] = None,
) -> tuple[list[VoiceProfile], Optional[str]]:
    """Paginated, filtered, searchable voice listing.

    Returns ``(items, next_cursor)``. The cursor is an opaque offset token today; the
    contract is keyset-ready so the internals can change without affecting callers.
    """
    limit_val = max(1, min(limit, 100))
    offset = _decode_cursor(cursor)

    stmt = select(VoiceProfile)

    # Scope.
    if scope == "community":
        stmt = stmt.where(VoiceProfile.is_public.is_(True), VoiceProfile.is_community_voice.is_(True))
    elif scope == "preset":
        stmt = stmt.where(VoiceProfile.is_preset_voice.is_(True))
    elif scope == "recent":
        stmt = stmt.where(
            VoiceProfile.owner_id == settings.LOCAL_OWNER_ID,
            VoiceProfile.last_used_at.is_not(None),
        )
    else:  # "mine" (default)
        stmt = stmt.where(VoiceProfile.owner_id == settings.LOCAL_OWNER_ID)

    # Filters.
    if language_code:
        stmt = stmt.where(VoiceProfile.language_code == language_code)
    if gender:
        stmt = stmt.where(_characteristic("gender") == gender)
    if age_group:
        stmt = stmt.where(_characteristic("age_group") == age_group)
    if accent:
        stmt = stmt.where(_characteristic("accent") == accent)
    if favorite:
        stmt = stmt.where(VoiceProfile.is_favorite.is_(True))
    if creation_source:
        if creation_source == "PRESET_VOICE":
            stmt = stmt.where(VoiceProfile.is_preset_voice.is_(True))
        elif creation_source == "SOURCE_ASSET":
            stmt = stmt.where(VoiceProfile.is_preset_voice.is_(False))
    if provider:
        stmt = stmt.where(func.json_extract(VoiceProfile.meta, "$.provider") == provider)

    if recently_used:
        periods = {"7d": 7, "30d": 30, "90d": 90}
        days = periods.get(recently_used)
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = stmt.where(VoiceProfile.last_used_at >= cutoff)

    # Search across name/language/code + characteristics & preset_tags (raw JSON LIKE).
    if search and search.strip():
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(VoiceProfile.name).like(q),
                func.lower(func.coalesce(VoiceProfile.language, "")).like(q),
                func.lower(func.coalesce(VoiceProfile.language_code, "")).like(q),
                func.lower(func.coalesce(func.cast(VoiceProfile.characteristics, String), "")).like(q),
                func.lower(func.coalesce(func.cast(VoiceProfile.preset_tags, String), "")).like(q),
            )
        )

    # Sorting.
    sort_col = None
    if sort_by == "name":
        sort_col = VoiceProfile.name
    elif sort_by == "last_used_at":
        sort_col = VoiceProfile.last_used_at
    elif sort_by == "language":
        sort_col = VoiceProfile.language_code
    elif sort_by == "usage_count":
        sort_col = VoiceProfile.usage_count
    else:
        sort_col = VoiceProfile.created_at

    if sort_dir == "asc":
        stmt = stmt.order_by(sort_col.asc().nullslast(), VoiceProfile.id.asc())
    else:
        stmt = stmt.order_by(sort_col.desc().nullslast(), VoiceProfile.id.desc())

    # Fetch one extra row to detect whether another page exists.
    stmt = stmt.offset(offset).limit(limit_val + 1)
    rows = list((await db.execute(stmt)).scalars().all())

    next_cursor = _encode_cursor(offset + limit_val) if len(rows) > limit_val else None
    return rows[:limit_val], next_cursor


async def set_favorite(
    db: AsyncSession, voice_id: str, value: bool
) -> Optional[VoiceProfile]:
    """Set the favorite flag on a voice, returning the updated row (or None if absent)."""
    voice = await db.get(VoiceProfile, voice_id)
    if voice is None:
        return None
    voice.is_favorite = value
    await db.commit()
    await db.refresh(voice)
    return voice
