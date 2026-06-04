"""ADR-0009 — voice_variant_artifacts repository: append, active pointer, list, prune."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.models.db import VoiceVariant
from app.services.voice_variant_artifact_repository import (
    append_artifact,
    get_active_artifact,
    get_version,
    list_versions,
    next_version,
    prune_artifacts,
    set_active,
)

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/repo.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def _variant(session) -> VoiceVariant:
    from sqlalchemy import select
    return (
        await session.execute(
            select(VoiceVariant).where(VoiceVariant.model_id == "omnivoice-base")
        )
    ).scalar_one()


async def test_backfilled_variant_has_v1_active(session):
    variant = await _variant(session)
    active = await get_active_artifact(session, variant)
    assert active is not None
    assert active.version == 1


async def test_next_version_increments(session):
    variant = await _variant(session)
    assert await next_version(session, variant.id) == 2


async def test_append_then_set_active_dual_writes_inline(session):
    variant = await _variant(session)
    art = await append_artifact(
        session,
        variant_id=variant.id,
        storage_keys={"audio": "voices/uuid-1/variants/omnivoice-base/v2/reference.wav"},
        model_version="2.0",
    )
    assert art.version == 2
    await set_active(session, variant, art)
    await session.refresh(variant)
    assert variant.active_artifact_id == art.id
    # Inline column is dual-written for back-compat (ADR-0009 §10 transition).
    assert variant.artifacts["audio"].endswith("v2/reference.wav")


async def test_list_versions_is_ordered(session):
    variant = await _variant(session)
    await append_artifact(session, variant_id=variant.id, storage_keys={"audio": "v2"})
    await append_artifact(session, variant_id=variant.id, storage_keys={"audio": "v3"})
    versions = await list_versions(session, variant.id)
    assert [v.version for v in versions] == [1, 2, 3]


async def test_rollback_via_set_active_to_old_version(session):
    variant = await _variant(session)
    v2 = await append_artifact(session, variant_id=variant.id, storage_keys={"audio": "v2"})
    await set_active(session, variant, v2)
    v1 = await get_version(session, variant.id, 1)
    await set_active(session, variant, v1)  # rollback
    await session.refresh(variant)
    assert variant.active_artifact_id == v1.id


async def test_prune_keeps_active_plus_n_recent(session):
    variant = await _variant(session)
    for v in range(2, 7):  # build up to v6
        art = await append_artifact(
            session, variant_id=variant.id, storage_keys={"audio": f"v{v}"}
        )
    await set_active(session, variant, art)  # active = v6
    deleted = await prune_artifacts(session, variant, keep_count=3)
    remaining = [v.version for v in await list_versions(session, variant.id)]
    # Keep last 3 (v4,v5,v6); active (v6) always retained. v1,v2,v3 pruned.
    assert remaining == [4, 5, 6]
    assert len(deleted) == 3


async def test_prune_never_deletes_active_even_if_old(session):
    variant = await _variant(session)
    arts = [
        await append_artifact(session, variant_id=variant.id, storage_keys={"audio": f"v{v}"})
        for v in range(2, 7)
    ]
    # Active is an OLD version (v2) — simulating a rollback held in place.
    await set_active(session, variant, arts[0])  # v2
    await prune_artifacts(session, variant, keep_count=2)
    remaining = [v.version for v in await list_versions(session, variant.id)]
    assert 2 in remaining  # active v2 preserved despite being old
