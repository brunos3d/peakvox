import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.models.db import Voice, VoiceProfile, VoiceVariant
from app.services.voice_onboarding import delete_voice_split, mirror_profile_to_split


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/dw.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


async def _make_profile(session, **overrides):
    profile = VoiceProfile(
        public_voice_id=overrides.get("public_voice_id", "voice_NEW001"),
        name=overrides.get("name", "Nova"),
        audio_filename=overrides.get("audio_filename", "voices/p1/reference.wav"),
        transcript=overrides.get("transcript", "hi"),
        generation_defaults=overrides.get("generation_defaults", {"num_step": 16}),
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def test_mirror_creates_voice_and_variant(session):
    profile = await _make_profile(session)
    await mirror_profile_to_split(session, profile)

    voice = (await session.execute(
        select(Voice).where(Voice.public_voice_id == "voice_NEW001")
    )).scalar_one()
    assert voice.id == profile.id

    variant = (await session.execute(
        select(VoiceVariant).where(VoiceVariant.voice_id == profile.id)
    )).scalar_one()
    assert variant.model_id == "omnivoice-base"
    assert variant.artifacts["audio"] == "voices/p1/reference.wav"


async def test_mirror_updates_existing_variant(session):
    profile = await _make_profile(session)
    await mirror_profile_to_split(session, profile)

    profile.transcript = "updated transcript"
    await session.commit()
    await mirror_profile_to_split(session, profile)

    variants = (await session.execute(
        select(VoiceVariant).where(VoiceVariant.voice_id == profile.id)
    )).scalars().all()
    assert len(variants) == 1  # upsert, not duplicate
    assert variants[0].params["transcript"] == "updated transcript"


async def test_delete_removes_voice_and_variants(session):
    profile = await _make_profile(session)
    await mirror_profile_to_split(session, profile)

    await delete_voice_split(session, profile.id)

    assert (await session.execute(
        select(Voice).where(Voice.id == profile.id)
    )).scalar_one_or_none() is None
    assert (await session.execute(
        select(VoiceVariant).where(VoiceVariant.voice_id == profile.id)
    )).scalar_one_or_none() is None
