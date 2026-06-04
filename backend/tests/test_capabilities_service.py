from app.models.registry_types import ModelCapabilities
from app.services.capabilities import (
    CAPABILITY_REGISTRY,
    capability_dict,
    missing_capabilities,
    supports,
)


def test_registry_lists_all_capability_keys_with_labels():
    # Every capability has UI metadata (label) so the frontend renders without hardcoding.
    for key in (
        "supports_tts", "supports_voice_cloning", "supports_voice_conversion",
        "supports_singing", "supports_emotion_tags", "supports_voice_design",
        "supports_streaming", "supports_multilingual", "supports_reference_audio",
        "supports_batch_generation",
    ):
        assert key in CAPABILITY_REGISTRY
        assert CAPABILITY_REGISTRY[key].label


def test_supports_is_capability_driven_not_name_driven():
    singing = ModelCapabilities(supports_singing=True, supports_emotion_tags=True)
    base = ModelCapabilities(supports_voice_cloning=True)
    assert supports(singing, "supports_singing") is True
    assert supports(base, "supports_singing") is False
    # Unknown capability → safe False (forward-compatible).
    assert supports(base, "supports_warp_drive") is False


def test_missing_capabilities_returns_unmet_requirements():
    base = ModelCapabilities(supports_tts=True, supports_voice_cloning=True)
    required = {"supports_tts", "supports_singing"}
    assert missing_capabilities(base, required) == {"supports_singing"}
    assert missing_capabilities(base, {"supports_tts"}) == set()


def test_capability_dict_roundtrips_for_api_and_ui():
    caps = ModelCapabilities(supports_singing=True)
    d = capability_dict(caps)
    assert d["supports_singing"] is True
    assert d["supports_tts"] is True
    assert "capability_version" in d
