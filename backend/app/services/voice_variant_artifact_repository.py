"""Repository for versioned VoiceVariant artifacts (ADR-0009).

Every build appends a row; the variant's ``active_artifact_id`` points at the version the
Runtime resolves for generation. Old versions are retained per policy (CE keeps the active plus
the last N) so rollback and generation reproducibility hold. This layer is below the Runtime and
never exposed on the public API — the Voice/VoiceVariant identity is the public surface.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db import VoiceVariant, VoiceVariantArtifact


async def next_version(db: AsyncSession, variant_id: str) -> int:
    """The next monotonic version number for a variant (1 if it has no artifacts yet)."""
    current = (
        await db.execute(
            select(func.max(VoiceVariantArtifact.version)).where(
                VoiceVariantArtifact.voice_variant_id == variant_id
            )
        )
    ).scalar_one_or_none()
    return (current or 0) + 1


async def append_artifact(
    db: AsyncSession,
    *,
    variant_id: str,
    storage_keys: Optional[dict],
    model_version: Optional[str] = None,
    storage_hash: Optional[str] = None,
    size_bytes: Optional[int] = None,
    checksum: Optional[str] = None,
    meta: Optional[dict] = None,
) -> VoiceVariantArtifact:
    """Append a new artifact version row. Does **not** flip the active pointer — call
    :func:`set_active` to make it the resolved version (keeps build/activate separable)."""
    artifact = VoiceVariantArtifact(
        voice_variant_id=variant_id,
        version=await next_version(db, variant_id),
        storage_keys=storage_keys,
        model_version=model_version,
        storage_hash=storage_hash,
        size_bytes=size_bytes,
        checksum=checksum,
        meta=meta,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


async def get_active_artifact(
    db: AsyncSession, variant: VoiceVariant
) -> Optional[VoiceVariantArtifact]:
    """The variant's currently active artifact version, or ``None`` if it has none."""
    if variant.active_artifact_id is None:
        return None
    return await db.get(VoiceVariantArtifact, variant.active_artifact_id)


async def get_version(
    db: AsyncSession, variant_id: str, version: int
) -> Optional[VoiceVariantArtifact]:
    return (
        await db.execute(
            select(VoiceVariantArtifact).where(
                VoiceVariantArtifact.voice_variant_id == variant_id,
                VoiceVariantArtifact.version == version,
            )
        )
    ).scalar_one_or_none()


async def list_versions(db: AsyncSession, variant_id: str) -> list[VoiceVariantArtifact]:
    """All artifact versions for a variant, ordered ascending by version."""
    return list(
        (
            await db.execute(
                select(VoiceVariantArtifact)
                .where(VoiceVariantArtifact.voice_variant_id == variant_id)
                .order_by(VoiceVariantArtifact.version.asc())
            )
        ).scalars()
    )


async def set_active(
    db: AsyncSession, variant: VoiceVariant, artifact: VoiceVariantArtifact
) -> None:
    """Point the variant at ``artifact`` (build completion or rollback).

    Dual-writes the inline ``voice_variants.artifacts`` column for backward compatibility during
    the ADR-0009 transition (consumers still reading the inline keys keep working).
    """
    variant.active_artifact_id = artifact.id
    variant.artifacts = artifact.storage_keys
    await db.commit()
    await db.refresh(variant)


async def prune_artifacts(
    db: AsyncSession, variant: VoiceVariant, keep_count: Optional[int] = None
) -> list[str]:
    """Enforce CE retention: keep the active version plus the ``keep_count`` most recent
    versions; delete the rest. The active artifact is **never** pruned (ADR-0009 §6).

    Returns the ids of the deleted artifact rows. (Storage-file reclamation of the orphaned keys
    is the storage layer's concern; in CE the object store is swept separately.)
    """
    keep_count = keep_count if keep_count is not None else settings.ARTIFACT_RETENTION_COUNT
    versions = await list_versions(db, variant.id)
    if len(versions) <= keep_count:
        return []

    keep_ids: set[str] = {v.id for v in versions[-keep_count:]}
    if variant.active_artifact_id is not None:
        keep_ids.add(variant.active_artifact_id)

    doomed = [v.id for v in versions if v.id not in keep_ids]
    if doomed:
        await db.execute(
            delete(VoiceVariantArtifact).where(VoiceVariantArtifact.id.in_(doomed))
        )
        await db.commit()
    return doomed
