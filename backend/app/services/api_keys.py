"""API key management for the public REST API (`/api/v1`).

Keys are formatted ``ov_live_<random>``. The raw key is returned to the caller exactly
once at creation; the database stores only a sha256 hash plus a short display prefix.
Keys belong to the local owner today, but ``owner_id`` keeps this multi-tenant ready.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db import ApiKey

KEY_PREFIX = "ov_live_"
_SECRET_BYTES = 24  # → 48 hex chars after the prefix
_DISPLAY_PREFIX_LEN = len(KEY_PREFIX) + 8


def extract_api_token(
    authorization: Optional[str], x_api_key: Optional[str]
) -> Optional[str]:
    """Pull the raw key from request headers.

    Accepts ``X-API-Key: <key>`` (preferred) or ``Authorization: Bearer <key>``.
    Returns None when neither is present/valid.
    """
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization[:7].lower() == "bearer ":
        return authorization[7:].strip()
    return None


def hash_key(raw_key: str) -> str:
    """Return the sha256 hex digest stored for a raw key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Return ``(raw_key, display_prefix, secret_hash)`` for a fresh key."""
    raw = f"{KEY_PREFIX}{secrets.token_hex(_SECRET_BYTES)}"
    return raw, raw[:_DISPLAY_PREFIX_LEN], hash_key(raw)


async def create_api_key(
    db: AsyncSession, *, name: str, owner_id: Optional[str] = None
) -> tuple[ApiKey, str]:
    """Create a key and return ``(row, raw_key)``. The raw key is only available here."""
    raw, prefix, secret_hash = generate_api_key()
    key = ApiKey(
        name=name,
        prefix=prefix,
        secret_hash=secret_hash,
        owner_id=owner_id or settings.LOCAL_OWNER_ID,
        status="active",
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key, raw


async def list_api_keys(
    db: AsyncSession, owner_id: Optional[str] = None
) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.owner_id == (owner_id or settings.LOCAL_OWNER_ID))
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, key_id: str) -> Optional[ApiKey]:
    key = await db.get(ApiKey, key_id)
    if key is None:
        return None
    key.status = "revoked"
    await db.commit()
    await db.refresh(key)
    return key


async def verify_api_key(db: AsyncSession, raw_key: str) -> Optional[ApiKey]:
    """Return the active key matching ``raw_key`` (updating last_used_at), else None."""
    if not raw_key or not raw_key.startswith(KEY_PREFIX):
        return None
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.secret_hash == hash_key(raw_key),
            ApiKey.status == "active",
        )
    )
    key = result.scalar_one_or_none()
    if key is None:
        return None
    key.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(key)
    return key
