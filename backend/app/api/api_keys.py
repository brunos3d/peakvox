"""Internal API-key management endpoints used by the dashboard.

These run unauthenticated in the self-hosted Community Edition (single local owner). In
a future Cloud/Enterprise edition they would sit behind the user session — the owner_id
plumbing is already in place.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.api import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse
from app.services.api_keys import create_api_key, list_api_keys, revoke_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(db: AsyncSession = Depends(get_db)):
    return await list_api_keys(db)


@router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def create_key(payload: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    key, raw = await create_api_key(db, name=payload.name)
    logger.info("Created API key %s (%s)", key.id, key.prefix)
    # The raw key is returned exactly once; it is never retrievable again.
    return ApiKeyCreateResponse(
        id=key.id,
        name=key.name,
        prefix=key.prefix,
        status=key.status,
        created_at=key.created_at,
        last_used_at=key.last_used_at,
        key=raw,
    )


@router.delete("/{key_id}", response_model=ApiKeyResponse)
async def revoke_key(key_id: str, db: AsyncSession = Depends(get_db)):
    key = await revoke_api_key(db, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    logger.info("Revoked API key %s", key_id)
    return key
