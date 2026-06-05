"""Tests for ProviderVoice domain type, ProviderVoiceCatalog protocol, and ProviderVoiceRegistry."""

import pytest
from dataclasses import FrozenInstanceError

from app.services.provider_voice import (
    ProviderVoice,
    ProviderVoiceCatalog,
    ProviderVoiceRegistry,
    build_provider_voice_id,
)


# ── ProviderVoice dataclass ────────────────────────────────────────────────

def test_build_provider_voice_id_deterministic():
    """Same provider_id + external_id always yields the same result."""
    a = build_provider_voice_id("kokoro", "af_heart")
    b = build_provider_voice_id("kokoro", "af_heart")
    assert a == b
    assert a == "voice_kokoro_af_heart"


def test_build_provider_voice_id_different_keys_differ():
    """Different external_ids produce different voice IDs."""
    heart = build_provider_voice_id("kokoro", "af_heart")
    bella = build_provider_voice_id("kokoro", "af_bella")
    assert heart != bella


def test_build_provider_voice_id_provider_scoping():
    """Same external_id under different providers yields different voice IDs."""
    for_kokoro = build_provider_voice_id("kokoro", "af_heart")
    for_piper = build_provider_voice_id("piper", "af_heart")
    assert for_kokoro != for_piper


def test_provider_voice_frozen():
    """ProviderVoice dataclass is immutable."""
    pv = ProviderVoice(
        provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
        provider_id="kokoro",
        external_id="af_heart",
        name="Heart",
    )
    with pytest.raises(FrozenInstanceError):
        pv.name = "Changed"


def test_provider_voice_minimal():
    """ProviderVoice can be created with only required fields."""
    pv = ProviderVoice(
        provider_voice_id="voice_kokoro_test",
        provider_id="kokoro",
        external_id="test",
        name="Test Voice",
    )
    assert pv.provider_voice_id == "voice_kokoro_test"
    assert pv.provider_id == "kokoro"
    assert pv.external_id == "test"
    assert pv.name == "Test Voice"
    assert pv.description == ""
    assert pv.language is None
    assert pv.gender is None
    assert pv.tags == ()


def test_provider_voice_all_fields():
    """ProviderVoice can be created with all optional fields."""
    pv = ProviderVoice(
        provider_voice_id="voice_kokoro_af_heart",
        provider_id="kokoro",
        external_id="af_heart",
        name="Heart",
        description="A warm, expressive female voice",
        language="en",
        gender="female",
        tags=("warm", "expressive"),
        is_default=True,
    )
    assert pv.language == "en"
    assert pv.gender == "female"
    assert pv.tags == ("warm", "expressive")
    assert pv.is_default is True


# ── ProviderVoiceCatalog protocol (runtime-checkable) ──────────────────────


def test_provider_voice_catalog_is_runtime_checkable():
    """ProviderVoiceCatalog is a runtime-checkable Protocol — isinstance works."""
    class Impl:
        def list_provider_voices(self): return []
        def get_provider_voice(self, _): return None
        def has_provider_voice(self, _): return False

    class NonImpl:
        pass

    assert isinstance(Impl(), ProviderVoiceCatalog)
    assert not isinstance(NonImpl(), ProviderVoiceCatalog)


# ── ProviderVoiceRegistry ──────────────────────────────────────────────────


@pytest.fixture
def registry():
    return ProviderVoiceRegistry()


@pytest.fixture
def sample_voices():
    return [
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
            provider_id="kokoro",
            external_id="af_heart",
            name="Heart",
            language="en",
            gender="female",
        ),
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "af_bella"),
            provider_id="kokoro",
            external_id="af_bella",
            name="Bella",
            language="en",
            gender="female",
        ),
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "am_adam"),
            provider_id="kokoro",
            external_id="am_adam",
            name="Adam",
            language="en",
            gender="male",
        ),
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("piper", "voice_1"),
            provider_id="piper",
            external_id="voice_1",
            name="Piper One",
            language="en",
        ),
    ]


# ── register / get ─────────────────────────────────────────────────────────


def test_register_and_get(registry, sample_voices):
    registry.register(sample_voices[0])
    result = registry.get("voice_kokoro_af_heart")
    assert result is not None
    assert result.external_id == "af_heart"
    assert result.name == "Heart"


def test_get_unknown(registry):
    result = registry.get("voice_nonexistent")
    assert result is None


def test_register_many(registry, sample_voices):
    registry.register_many(sample_voices)
    assert registry.get("voice_kokoro_af_heart") is not None
    assert registry.get("voice_kokoro_af_bella") is not None
    assert registry.get("voice_piper_voice_1") is not None


# ── list ───────────────────────────────────────────────────────────────────


def test_list_all(registry, sample_voices):
    registry.register_many(sample_voices)
    all_v = registry.list_all()
    assert len(all_v) == 4


def test_list_all_empty(registry):
    assert registry.list_all() == []


def test_list_by_provider(registry, sample_voices):
    registry.register_many(sample_voices)
    kokoro = registry.list_by_provider("kokoro")
    assert len(kokoro) == 3


def test_list_by_provider_unknown(registry):
    assert registry.list_by_provider("nonexistent") == []


# ── remove / remove_provider ──────────────────────────────────────────────


def test_remove(registry, sample_voices):
    registry.register_many(sample_voices)
    registry.remove("voice_kokoro_af_heart")
    assert registry.get("voice_kokoro_af_heart") is None
    assert len(registry.list_all()) == 3


def test_remove_unknown(registry):
    registry.remove("voice_nonexistent")  # should not raise


def test_remove_provider(registry, sample_voices):
    registry.register_many(sample_voices)
    registry.remove_provider("kokoro")
    assert registry.get("voice_kokoro_af_heart") is None
    assert registry.get("voice_kokoro_af_bella") is None
    assert registry.get("voice_kokoro_am_adam") is None
    # piper voices survive
    assert registry.get("voice_piper_voice_1") is not None


def test_remove_provider_unknown(registry):
    registry.remove_provider("nonexistent")  # should not raise


# ── refresh (atomic provider-level replace) ───────────────────────────────


def test_refresh_replaces_provider_voices(registry, sample_voices):
    registry.register_many(sample_voices)
    new_voices = [
        ProviderVoice(
            provider_voice_id=build_provider_voice_id("kokoro", "af_new"),
            provider_id="kokoro",
            external_id="af_new",
            name="New Voice",
        ),
    ]
    registry.refresh("kokoro", new_voices)
    # Old kokoro voices gone
    assert registry.get("voice_kokoro_af_heart") is None
    # New kokoro voice present
    assert registry.get("voice_kokoro_af_new") is not None
    # Other providers untouched
    assert registry.get("voice_piper_voice_1") is not None


def test_refresh_empty_clears_provider(registry, sample_voices):
    registry.register_many(sample_voices)
    registry.refresh("kokoro", [])
    assert len(registry.list_by_provider("kokoro")) == 0
    assert len(registry.list_all()) == 1  # only piper remains


def test_refresh_mismatched_provider_raises(registry):
    with pytest.raises(ValueError, match="provider_id mismatch"):
        registry.refresh("kokoro", [
            ProviderVoice(
                provider_voice_id="voice_piper_x",
                provider_id="piper",
                external_id="x",
                name="Wrong",
            ),
        ])


# ── reload (full rebuild) ──────────────────────────────────────────────────


class _FakeCatalogAdapter:
    """Minimal adapter that implements ProviderVoiceCatalog."""
    def __init__(self, provider_id: str, count: int):
        self._provider_id = provider_id
        self._voices = [
            ProviderVoice(
                provider_voice_id=build_provider_voice_id(provider_id, f"v{i}"),
                provider_id=provider_id,
                external_id=f"v{i}",
                name=f"Voice {i}",
            )
            for i in range(count)
        ]

    def list_provider_voices(self):
        return self._voices

    def get_provider_voice(self, external_id: str):
        for v in self._voices:
            if v.external_id == external_id:
                return v
        return None

    def has_provider_voice(self, external_id: str):
        return self.get_provider_voice(external_id) is not None


def test_reload_populates_from_adapters(registry):
    adapters = [
        _FakeCatalogAdapter("kokoro", 3),
        _FakeCatalogAdapter("piper", 2),
    ]
    registry.reload(adapters)
    assert len(registry.list_all()) == 5
    assert len(registry.list_by_provider("kokoro")) == 3
    assert len(registry.list_by_provider("piper")) == 2


def test_reload_clears_existing(registry, sample_voices):
    registry.register_many(sample_voices)
    registry.reload([])
    assert len(registry.list_all()) == 0


def test_reload_ignores_non_catalog_adapters(registry):
    class NonCatalog:
        pass
    adapters = [_FakeCatalogAdapter("kokoro", 2), NonCatalog()]
    registry.reload(adapters)
    assert len(registry.list_all()) == 2


# ── search ─────────────────────────────────────────────────────────────────


def test_search_by_name(registry, sample_voices):
    registry.register_many(sample_voices)
    results = registry.search("heart")
    assert len(results) == 1
    assert results[0].external_id == "af_heart"


def test_search_case_insensitive(registry, sample_voices):
    registry.register_many(sample_voices)
    results = registry.search("HEART")
    assert len(results) == 1


def test_search_empty_query_returns_all(registry, sample_voices):
    registry.register_many(sample_voices)
    results = registry.search("")
    assert len(results) == 4


def test_search_no_match(registry, sample_voices):
    registry.register_many(sample_voices)
    results = registry.search("zzzzz")
    assert results == []


def test_search_filter_by_provider(registry, sample_voices):
    registry.register_many(sample_voices)
    results = registry.search("", provider_id="kokoro")
    assert len(results) == 3


def test_search_filter_by_language(registry, sample_voices):
    registry.register_many(sample_voices)
    results = registry.search("", language="en")
    assert len(results) == 4
    results = registry.search("", language="fr")
    assert results == []


def test_search_filter_by_gender(registry, sample_voices):
    registry.register_many(sample_voices)
    results = registry.search("", gender="female")
    assert len(results) == 2
    results = registry.search("", gender="male")
    assert len(results) == 1
