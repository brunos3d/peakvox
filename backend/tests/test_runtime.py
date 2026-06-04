from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.migrations import run_migrations
from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.services.model_adapter import ModelAdapter
from app.services.runtime import (
    PeakVoxRuntime,
    ModelNotRegistered,
    VoiceNotFound,
    VariantUnavailable,
    UnsupportedTags,
    UnsupportedCapability,
)

_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


class FakeAdapter(ModelAdapter):
    def __init__(self, descriptor):
        super().__init__(descriptor)
        self.generated: list[str] = []

    async def install(self): ...
    async def load(self): ...
    def unload(self): ...
    async def health_check(self) -> bool:
        return True

    async def generate(self, *, text, output_path, **kwargs):
        self.generated.append(text)
        return (2.0, [f"{self.model_id}:{text}"])

    async def clone_voice(self, *, db, voice, reference_audio_key):
        raise NotImplementedError

    async def build_variant(self, *, db, voice):
        raise NotImplementedError


def _desc(model_id, *, default=False, tags=None, caps=None):
    return ModelDescriptor(
        id=model_id, name=model_id, description="d", provider="fake",
        supported_tags=tags or [], is_default=default,
        capabilities=caps or ModelCapabilities(),
    )


def _runtime():
    rt = PeakVoxRuntime()
    rt.register_adapter(FakeAdapter(_desc("omnivoice-base", default=True, tags=["happy"],
                                          caps=ModelCapabilities(supports_voice_cloning=True))))
    rt.register_adapter(FakeAdapter(_desc("omnivoice-singing", tags=["singing", "whisper"],
                                          caps=ModelCapabilities(supports_singing=True))))
    return rt


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/rt.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)  # backfill base variant
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


def test_adapter_registry_and_default():
    rt = _runtime()
    assert rt.get_adapter("omnivoice-singing").model_id == "omnivoice-singing"
    assert rt.resolve_model(None).id == "omnivoice-base"  # default
    with pytest.raises(ModelNotRegistered):
        rt.get_adapter("nope")


async def test_resolve_voice_and_variant(session):
    rt = _runtime()
    res = await rt.resolve(session, public_voice_id="voice_ABC123", model_id="omnivoice-base")
    assert res.voice.id == "uuid-1"
    assert res.model.id == "omnivoice-base"
    assert res.variant is not None
    assert res.adapter.model_id == "omnivoice-base"


async def test_resolve_unknown_voice_raises(session):
    rt = _runtime()
    with pytest.raises(VoiceNotFound):
        await rt.resolve(session, public_voice_id="voice_NOPE", model_id="omnivoice-base")


async def test_resolve_missing_variant_raises(session):
    rt = _runtime()
    with pytest.raises(VariantUnavailable):
        await rt.resolve(session, public_voice_id="voice_ABC123", model_id="omnivoice-singing")


def test_validate_tags_is_capability_data_driven():
    rt = _runtime()
    assert rt.validate_tags("omnivoice-base", "hello [happy]") == []
    bad = rt.validate_tags("omnivoice-base", "sing [singing] now")
    assert "singing" in bad


def test_validate_capabilities_reports_missing():
    rt = _runtime()
    assert rt.missing_capabilities("omnivoice-base", {"supports_voice_cloning"}) == set()
    assert rt.missing_capabilities("omnivoice-base", {"supports_singing"}) == {"supports_singing"}


async def test_generate_adhoc_without_voice(session):
    rt = _runtime()
    duration, logs = await rt.generate(
        session, text="hi", model_id="omnivoice-base", output_path=Path("/tmp/x.wav")
    )
    assert duration == 2.0
    assert "omnivoice-base:hi" in logs[0]


async def test_generate_rejects_unsupported_tags(session):
    rt = _runtime()
    with pytest.raises(UnsupportedTags):
        await rt.generate(
            session, text="x [singing]", model_id="omnivoice-base", output_path=Path("/tmp/x.wav")
        )


async def test_generate_rejects_unsupported_capability(session):
    rt = _runtime()
    with pytest.raises(UnsupportedCapability):
        await rt.generate(
            session, text="hi", model_id="omnivoice-base", output_path=Path("/tmp/x.wav"),
            required_capabilities={"supports_singing"},
        )
