"""ADR-0008 / ADR-0009 — Runtime owns variant build lifecycle + artifact versioning.

Uses the real OmniVoice (reference_sample, sync) and Fish (embedding) adapters so the build
strategy is exercised end-to-end through the Runtime, not mocked.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.services.model_adapters.fish_adapter import FishAudioAdapter
from app.services.model_adapters.omnivoice_adapter import (
    OmniVoiceAdapter,
    OmniVoiceSingingAdapter,
)
from app.services.model_catalog import builtin_by_id
from app.services.runtime import (
    ArtifactVersionNotFound,
    PeakVoxRuntime,
    VariantBuildFailed,
    VariantDeprecated,
    VoiceNotFound,
)
from app.services.voice_variant_repository import get_voice_identity_by_public_id

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/life.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


def _runtime():
    rt = PeakVoxRuntime()
    rt.register_adapter(OmniVoiceAdapter(builtin_by_id("omnivoice-base")))
    rt.register_adapter(OmniVoiceSingingAdapter(builtin_by_id("omnivoice-singing")))
    rt.register_adapter(FishAudioAdapter(builtin_by_id("fish-audio-s2")))
    return rt


async def _voice(session):
    return await get_voice_identity_by_public_id(session, "voice_ABC123")


async def test_ensure_variant_returns_existing_ready(session):
    rt = _runtime()
    voice = await _voice(session)
    variant = await rt.ensure_variant(session, voice=voice, model_id="omnivoice-base")
    assert variant.status == "ready"
    assert variant.active_artifact_id is not None


async def test_build_variant_creates_variant_with_artifact_version(session):
    rt = _runtime()
    voice = await _voice(session)
    variant = await rt.build_variant(session, voice=voice, model_id="omnivoice-singing")
    assert variant.status == "ready"
    active = await rt.get_active_artifact(session, voice=voice, model_id="omnivoice-singing")
    assert active is not None
    assert active.version == 1
    assert active.storage_keys["audio"] == "voices/uuid-1/reference.wav"


async def test_build_fish_variant_reference_sample(session):
    rt = _runtime()
    voice = await _voice(session)
    variant = await rt.build_variant(session, voice=voice, model_id="fish-audio-s2")
    assert variant.status == "ready"
    assert variant.artifact_type == "reference_sample"


async def test_rebuild_appends_version_and_preserves_old(session):
    rt = _runtime()
    voice = await _voice(session)
    await rt.rebuild_variant(session, voice=voice, model_id="omnivoice-base")
    versions = await rt.list_artifact_versions(session, voice=voice, model_id="omnivoice-base")
    assert [v.version for v in versions] == [1, 2]
    active = await rt.get_active_artifact(session, voice=voice, model_id="omnivoice-base")
    assert active.version == 2  # new version is active; v1 retained for rollback


async def test_ensure_variant_builds_when_missing(session):
    rt = _runtime()
    voice = await _voice(session)
    assert await rt.get_variant_status(session, voice=voice, model_id="omnivoice-singing") is None
    variant = await rt.ensure_variant(session, voice=voice, model_id="omnivoice-singing")
    assert variant.status == "ready"


async def test_rollback_artifact_changes_active_pointer(session):
    rt = _runtime()
    voice = await _voice(session)
    await rt.rebuild_variant(session, voice=voice, model_id="omnivoice-base")  # now v2 active
    variant = await rt.rollback_artifact(
        session, voice=voice, model_id="omnivoice-base", version=1
    )
    active = await rt.get_active_artifact(session, voice=voice, model_id="omnivoice-base")
    assert active.version == 1
    assert variant.active_artifact_id == active.id


async def test_rollback_unknown_version_raises(session):
    rt = _runtime()
    voice = await _voice(session)
    with pytest.raises(ArtifactVersionNotFound):
        await rt.rollback_artifact(session, voice=voice, model_id="omnivoice-base", version=99)


async def test_rebuild_auto_prunes_to_default_retention(session):
    rt = _runtime()
    voice = await _voice(session)
    # 5 rebuilds (versions climb to v6); each rebuild auto-prunes to the default retention
    # of 3 (ADR-0009 §6 — pruning trigger = on rebuild). So only the last 3 survive.
    for _ in range(5):
        await rt.rebuild_variant(session, voice=voice, model_id="omnivoice-base")
    versions = await rt.list_artifact_versions(session, voice=voice, model_id="omnivoice-base")
    assert [v.version for v in versions] == [4, 5, 6]


async def test_manual_prune_enforces_tighter_retention(session):
    rt = _runtime()
    voice = await _voice(session)
    for _ in range(5):
        await rt.rebuild_variant(session, voice=voice, model_id="omnivoice-base")
    # After auto-pruning, v4,v5,v6 remain; a tighter manual prune keeps only the last 2.
    deleted = await rt.prune_artifacts(
        session, voice=voice, model_id="omnivoice-base", keep_count=2
    )
    versions = await rt.list_artifact_versions(session, voice=voice, model_id="omnivoice-base")
    assert [v.version for v in versions] == [5, 6]
    assert len(deleted) == 1


async def test_ensure_variant_raises_on_deprecated(session):
    rt = _runtime()
    voice = await _voice(session)
    # Mark the base variant deprecated directly (e.g. model upgrade).
    await session.execute(
        text("UPDATE voice_variants SET status='deprecated' WHERE model_id='omnivoice-base'")
    )
    await session.commit()
    with pytest.raises(VariantDeprecated):
        await rt.ensure_variant(session, voice=voice, model_id="omnivoice-base")


async def test_ensure_variant_raises_on_failed(session):
    rt = _runtime()
    voice = await _voice(session)
    await session.execute(
        text("UPDATE voice_variants SET status='failed', error_message='boom' "
             "WHERE model_id='omnivoice-base'")
    )
    await session.commit()
    with pytest.raises(VariantBuildFailed):
        await rt.ensure_variant(session, voice=voice, model_id="omnivoice-base")


async def test_lifecycle_methods_require_known_voice(session):
    rt = _runtime()
    # A Voice with no public id row mapping — build still needs a real Voice object; this
    # asserts get_variant_status tolerates a voice with no variants.
    voice = await _voice(session)
    status = await rt.get_variant_status(session, voice=voice, model_id="fish-audio-s2")
    assert status is None
