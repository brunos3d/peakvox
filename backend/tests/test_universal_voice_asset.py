"""Phase 3.10 — Universal Voice Asset validation.

Proves `Voice ≠ VoiceVariant ≠ Model` holds across *fundamentally different providers*
(OmniVoice, OmniVoice Singing, Fish Audio) and that the public `public_voice_id` is a stable
contract: the same Voice resolves to a per-provider variant through one Runtime, while the
identity never changes.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.models.db import VoiceVariant
from app.services.model_adapters.fish_adapter import FishAudioAdapter
from app.services.model_adapters.omnivoice_adapter import (
    OmniVoiceAdapter,
    OmniVoiceSingingAdapter,
)
from app.services.model_catalog import builtin_by_id
from app.services.runtime import PeakVoxRuntime
from app.services.voice_variant_repository import get_voice_identity_by_public_id

VOICE = "voice_8JXQ29K4L3"

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    f"VALUES ('uuid-1','{VOICE}','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/asset.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)  # backfill omnivoice-base variant
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


async def test_one_voice_id_many_providers_one_runtime(session):
    rt = _runtime()
    voice = await get_voice_identity_by_public_id(session, VOICE)

    # Build a variant for each provider from the SAME voice's canonical reference.
    await rt.get_adapter("omnivoice-singing").build_variant(db=session, voice=voice)
    await rt.get_adapter("fish-audio-s2").build_variant(db=session, voice=voice)

    base = await rt.resolve(session, public_voice_id=VOICE, model_id="omnivoice-base")
    singing = await rt.resolve(session, public_voice_id=VOICE, model_id="omnivoice-singing")
    fish = await rt.resolve(session, public_voice_id=VOICE, model_id="fish-audio-s2")

    resolutions = [base, singing, fish]

    # Identity is constant across every provider (the public contract).
    assert all(r.voice.public_voice_id == VOICE for r in resolutions)
    assert len({r.voice.id for r in resolutions}) == 1

    # Model + Variant differ per provider (realization changes).
    assert [r.model.id for r in resolutions] == [
        "omnivoice-base", "omnivoice-singing", "fish-audio-s2"
    ]
    assert len({r.variant.id for r in resolutions}) == 3
    assert {r.variant.model_id for r in resolutions} == {
        "omnivoice-base", "omnivoice-singing", "fish-audio-s2"
    }

    # Providers span ecosystems; one Runtime resolves them all.
    assert isinstance(base.adapter, OmniVoiceAdapter)
    assert isinstance(singing.adapter, OmniVoiceSingingAdapter)
    assert isinstance(fish.adapter, FishAudioAdapter)


async def test_variant_formats_are_encapsulated_per_provider(session):
    rt = _runtime()
    voice = await get_voice_identity_by_public_id(session, VOICE)
    await rt.get_adapter("fish-audio-s2").build_variant(db=session, voice=voice)

    variants = (await session.execute(
        select(VoiceVariant).where(VoiceVariant.voice_id == voice.id)
    )).scalars().all()
    by_model = {v.model_id: v for v in variants}

    # Both OmniVoice and Fish use reference_sample realization — the difference is in
    # the engine, not in the variant format (P0 validation corrected this assumption).
    assert by_model["omnivoice-base"].artifact_type == "reference_sample"
    assert by_model["fish-audio-s2"].artifact_type == "reference_sample"


def test_capabilities_belong_to_models_not_voices():
    rt = _runtime()
    # Singing capability is the Model's, not the Voice's (ADR-0003/0004).
    assert rt.missing_capabilities("omnivoice-base", {"supports_singing"}) == {"supports_singing"}
    assert rt.missing_capabilities("omnivoice-singing", {"supports_singing"}) == set()
    assert rt.missing_capabilities("fish-audio-s2", {"supports_voice_cloning"}) == set()
