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
    ProviderVoiceCatalog,
    ProviderVoiceRegistry,
    build_provider_voice_id,
)
from app.services.runtime import (
    PeakVoxRuntime,
    ModelNotRegistered,
    VoiceNotFound,
    VariantUnavailable,
)


class FakeProviderAdapter(ModelAdapter):
    """An adapter that also implements ProviderVoiceCatalog."""

    def __init__(self, descriptor, voices: list[ProviderVoice] | None = None):
        super().__init__(descriptor)
        self.voices = voices or []
        self.generated: list[tuple[str, str]] = []  # (voice_profile_id, text)

    async def install(self): ...
    async def load(self): ...
    def unload(self): ...
    async def health_check(self) -> bool:
        return True

    async def generate(self, *, text, output_path, voice_profile_id=None, **kwargs):
        self.generated.append((voice_profile_id, text))
        return (2.0, [f"{self.model_id}:{text}"])

    async def clone_voice(self, *, db, voice, reference_audio_key):
        raise NotImplementedError

    async def build_variant(self, *, db, voice):
        raise NotImplementedError

    def list_provider_voices(self) -> list[ProviderVoice]:
        return self.voices

    def get_provider_voice(self, external_id: str) -> ProviderVoice | None:
        for v in self.voices:
            if v.external_id == external_id:
                return v
        return None

    def has_provider_voice(self, external_id: str) -> bool:
        return any(v.external_id == external_id for v in self.voices)


class FakeNonProviderAdapter(ModelAdapter):
    """An adapter that does NOT implement ProviderVoiceCatalog."""

    def __init__(self, descriptor):
        super().__init__(descriptor)
        self.generated: list[tuple[str, str]] = []

    async def install(self): ...
    async def load(self): ...
    def unload(self): ...
    async def health_check(self) -> bool:
        return True

    async def generate(self, *, text, output_path, voice_profile_id=None, **kwargs):
        self.generated.append((voice_profile_id, text))
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


def _provider_runtime():
    """Runtime with one provider adapter that has preset voices."""
    voices = [
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
            provider_id="kokoro",
            external_id="af_heart",
            name="Heart",
            language="en",
            gender="female",
        ),
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "am_morpheus"),
            provider_id="kokoro",
            external_id="am_morpheus",
            name="Morpheus",
            language="en",
            gender="male",
        ),
    ]
    rt = PeakVoxRuntime()
    rt.register_adapter(FakeProviderAdapter(
        _desc("kokoro", default=True, caps=ModelCapabilities(supports_tts=True)),
        voices=voices,
    ))
    return rt


_SEED = (
    "INSERT INTO voice_profiles (id, public_voice_id, owner_id, name, audio_filename, "
    "transcript, generation_defaults, is_public, is_community_voice, is_preset_voice, "
    "is_favorite, status, usage_count, created_at, updated_at) "
    "VALUES ('uuid-1','voice_ABC123','owner-1','Bruno','voices/uuid-1/reference.wav',"
    "'olá','{}',0,0,0,0,'ready',0,'2026-01-01','2026-01-01')"
)


@pytest.fixture
async def session(tmp_path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/rtrpv.db", future=True)
    async with eng.begin() as conn:
        await run_migrations(conn)
        await conn.execute(text(_SEED))
        await run_migrations(conn)
    maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await eng.dispose()


# ── Registry lifecycle on Runtime ──────────────────────────────────────────


def test_runtime_has_provider_voice_registry():
    rt = PeakVoxRuntime()
    assert hasattr(rt, "_provider_voice_registry")
    assert isinstance(rt._provider_voice_registry, ProviderVoiceRegistry)


def test_register_provider_voice_delegates_to_registry():
    rt = PeakVoxRuntime()
    voice = ProviderVoice(
        provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
        provider_id="kokoro", external_id="af_heart", name="Heart",
    )
    rt.register_provider_voice(voice)
    assert rt._provider_voice_registry.get(voice.provider_voice_id) is voice


def test_list_provider_voices_returns_all():
    rt = _provider_runtime()
    all_voices = rt.list_provider_voices()
    assert len(all_voices) == 2


def test_list_provider_voices_filters_by_provider():
    rt = _provider_runtime()
    kokoro = rt.list_provider_voices(provider_id="kokoro")
    assert len(kokoro) == 2
    unknown = rt.list_provider_voices(provider_id="nope")
    assert unknown == []


def test_list_provider_voices_empty_before_registration():
    rt = PeakVoxRuntime()
    assert rt.list_provider_voices() == []


# ── Generate with provider voice (registry path) ──────────────────────────


async def test_generate_with_provider_voice_resolves_via_registry():
    """When voice_id matches a provider voice, resolve via registry, not DB."""
    rt = _provider_runtime()
    voice_id = build_provider_voice_id("kokoro", "af_heart")
    adapter = rt.get_adapter("kokoro")
    orig_count = len(adapter.generated)

    duration, logs = await rt.generate(
        db=None, text="hello", model_id="kokoro",
        voice_id=voice_id, output_path=Path("/tmp/x.wav"),
    )
    assert duration == 2.0
    assert len(adapter.generated) == orig_count + 1
    # The provider voice_id is passed as voice_profile_id to the adapter
    assert adapter.generated[-1][0] == voice_id
    assert adapter.generated[-1][1] == "hello"


async def test_generate_with_unknown_voice_falls_through_to_db(session):
    """When voice_id is NOT in the registry and public_voice_id IS given,
    fall through to persisted Voice DB path."""
    rt = PeakVoxRuntime()
    rt.register_adapter(FakeNonProviderAdapter(
        _desc("omnivoice-base", default=True, caps=ModelCapabilities(supports_voice_cloning=True)),
    ))
    # Registry has no voices. Unknown voice_id falls through. public_voice_id
    # triggers DB path → VoiceNotFound for a non-existent id.
    with pytest.raises(VoiceNotFound):
        await rt.generate(
            db=session, text="hi", model_id="omnivoice-base",
            voice_id="voice_UNKNOWN", public_voice_id="voice_NONEXISTENT",
            output_path=Path("/tmp/x.wav"),
        )


async def test_generate_with_public_voice_id_still_uses_db_path(session):
    """Existing persisted Voice path via public_voice_id is unchanged."""
    rt = PeakVoxRuntime()
    rt.register_adapter(FakeNonProviderAdapter(
        _desc("omnivoice-base", default=True, caps=ModelCapabilities(supports_voice_cloning=True)),
    ))
    duration, logs = await rt.generate(
        session, text="hi", model_id="omnivoice-base",
        public_voice_id="voice_ABC123",
        output_path=Path("/tmp/x.wav"),
    )
    assert duration == 2.0


async def test_generate_provider_voice_without_model_id_resolves_default():
    """Provider voice generate uses the default model when model_id is None."""
    rt = _provider_runtime()
    voice_id = build_provider_voice_id("kokoro", "af_heart")
    adapter = rt.get_adapter("kokoro")
    orig_count = len(adapter.generated)

    duration, logs = await rt.generate(
        db=None, text="hi", model_id=None,
        voice_id=voice_id, output_path=Path("/tmp/x.wav"),
    )
    assert duration == 2.0
    assert len(adapter.generated) == orig_count + 1


async def test_generate_provider_voice_rejects_unregistered_model():
    """Provider voice generation fails when the model is not registered."""
    rt = _provider_runtime()
    voice_id = build_provider_voice_id("kokoro", "af_heart")
    # "nope" is not a registered model_id.
    with pytest.raises(ModelNotRegistered):
        await rt.generate(
            db=None, text="hi", model_id="nope",
            voice_id=voice_id, output_path=Path("/tmp/x.wav"),
        )


async def test_generate_provider_voice_does_not_touch_db():
    """Provider voice generation should NOT require a DB session."""
    rt = _provider_runtime()
    voice_id = build_provider_voice_id("kokoro", "af_heart")

    duration, logs = await rt.generate(
        db=None, text="no db needed", model_id="kokoro",
        voice_id=voice_id, output_path=Path("/tmp/x.wav"),
    )
    assert duration == 2.0


# ── Two-tier priority: registry before DB ─────────────────────────────────


async def test_provider_voice_takes_priority_over_persisted_voice():
    """When voice_id exists in registry AND a persisted voice has the same id,
    the registry (provider) path is used — no DB lookup."""
    rt = _provider_runtime()
    voice_id = build_provider_voice_id("kokoro", "af_heart")
    adapter = rt.get_adapter("kokoro")

    duration, logs = await rt.generate(
        db=None, text="priority", model_id="kokoro",
        voice_id=voice_id, output_path=Path("/tmp/x.wav"),
    )
    assert duration == 2.0
    assert adapter.generated[-1][0] == voice_id


# ── Auto-population on register_adapter ──────────────────────────────────


def test_register_adapter_auto_populates_provider_voices():
    """Registering a ProviderVoiceCatalog adapter auto-populates the registry."""
    rt = PeakVoxRuntime()
    voices = [
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
            provider_id="kokoro", external_id="af_heart", name="Heart",
        ),
    ]
    adapter = FakeProviderAdapter(
        _desc("kokoro", default=True, caps=ModelCapabilities(supports_tts=True)),
        voices=voices,
    )
    rt.register_adapter(adapter)
    assert rt._provider_voice_registry.get("voice_kokoro_af_heart") is voices[0]


def test_register_adapter_non_provider_does_not_populate():
    """Registering an adapter without ProviderVoiceCatalog leaves registry empty."""
    rt = PeakVoxRuntime()
    adapter = FakeNonProviderAdapter(
        _desc("base", caps=ModelCapabilities(supports_tts=True)),
    )
    rt.register_adapter(adapter)
    assert rt.list_provider_voices() == []


def test_register_adapter_with_empty_catalog():
    """Registering a ProviderVoiceCatalog adapter with no voices is a no-op."""
    rt = PeakVoxRuntime()
    adapter = FakeProviderAdapter(
        _desc("kokoro", default=True, caps=ModelCapabilities(supports_tts=True)),
        voices=[],
    )
    rt.register_adapter(adapter)
    assert rt.list_provider_voices() == []


# ── Registration of multiple voices ───────────────────────────────────────


def test_register_multiple_provider_voices():
    rt = PeakVoxRuntime()
    voices = [
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
            provider_id="kokoro", external_id="af_heart", name="Heart",
        ),
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "am_morpheus"),
            provider_id="kokoro", external_id="am_morpheus", name="Morpheus",
        ),
    ]
    rt.register_provider_voices(voices)
    assert len(rt.list_provider_voices()) == 2
