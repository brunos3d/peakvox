from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.services.model_adapter import ModelAdapter
from app.services.provider_voice import (
    ProviderVoice,
    build_provider_voice_id,
)
from app.services.runtime import PeakVoxRuntime


class TrackingAdapter(ModelAdapter):
    def __init__(self, descriptor):
        super().__init__(descriptor)
        self.captured_kwargs: dict = {}
    async def install(self): ...
    async def load(self): ...
    def unload(self): ...
    async def health_check(self) -> bool:
        return True
    async def generate(self, *, text, output_path, **kwargs):
        self.captured_kwargs = kwargs
        return (2.0, [f"{self.model_id}:{text}"])
    async def clone_voice(self, *, db, voice, reference_audio_key):
        raise NotImplementedError
    async def build_variant(self, *, db, voice):
        raise NotImplementedError


def _desc(model_id, *, default=False, caps=None):
    return ModelDescriptor(
        id=model_id, name=model_id, description="d", provider="fake",
        supported_tags=[], is_default=default,
        capabilities=caps or ModelCapabilities(),
    )


_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Test','','','{}',0,0,0,0,"
    "'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/single_path.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


def test_provider_voice_id_no_longer_resolves_without_db_record():
    """ProviderVoiceRegistry does NOT participate in generation resolution.
    voice_id works through the ad-hoc path; registry is no longer consulted."""
    rt = PeakVoxRuntime()
    voices = [ProviderVoice(
        provider_voice_id=build_provider_voice_id("test", "v1"),
        provider_id="test", external_id="v1", name="V1",
    )]
    adapter = TrackingAdapter(_desc("test-model", default=True, caps=ModelCapabilities(supports_tts=True)))
    adapter.list_provider_voices = lambda: voices
    adapter.get_provider_voice = lambda eid: voices[0] if eid == "v1" else None
    rt.register_adapter(adapter)
    import anyio
    duration, logs = anyio.run(
        lambda: rt.generate(
            None, text="hi", model_id="test-model",
            voice_id=build_provider_voice_id("test", "v1"),
            output_path=Path("/tmp/x.wav"),
        )
    )
    assert duration == 2.0


async def test_variant_params_flow_through_to_adapter(session):
    """Variant params are passed as kwargs to adapter.generate()."""
    from app.models.db import Voice, VoiceVariant as VV
    voice = await session.get(Voice, "uuid-1")
    if voice is None:
        voice = Voice(
            id="uuid-1", public_voice_id="voice_ABC123",
            owner_id="owner-1", name="Test",
            creation_source="SOURCE_ASSET", status="ready",
        )
        session.add(voice)
        await session.commit()

    variant = VV(
        voice_id="uuid-1", model_id="test-model",
        params={"provider": "kokoro", "preset_name": "af_heart"},
        artifacts={}, status="ready", source="preset",
    )
    session.add(variant)
    await session.commit()

    rt = PeakVoxRuntime()
    adapter = TrackingAdapter(_desc("test-model", default=True, caps=ModelCapabilities(supports_tts=True)))
    rt.register_adapter(adapter)

    await rt.generate(
        db=session, text="hello", model_id="test-model",
        public_voice_id="voice_ABC123", output_path=Path("/tmp/x.wav"),
    )
    """Variant params are merged into the params dict, not spread as top-level kwargs."""
    merged = adapter.captured_kwargs.get("params", {})
    assert merged.get("provider") == "kokoro"
    assert merged.get("preset_name") == "af_heart"
