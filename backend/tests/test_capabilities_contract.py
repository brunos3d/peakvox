from app.models.registry_types import ModelCapabilities


def test_defaults_are_backward_compatible():
    c = ModelCapabilities()
    # Legacy fields preserved
    assert c.supports_tts is True
    assert c.supports_api is True
    assert c.supports_voice_cloning is False
    # New fields default to safe "unsupported"
    assert c.supports_voice_conversion is False
    assert c.supports_emotion_tags is False
    assert c.supports_voice_design is False
    assert c.supports_multilingual is False
    assert c.supports_reference_audio is False
    assert c.supports_batch_generation is False


def test_capability_version_present_and_versioned():
    assert ModelCapabilities().capability_version >= 1


def test_unknown_capability_is_ignored_forward_compatible():
    # Extra/unknown fields from a newer model must not crash older readers.
    c = ModelCapabilities(**{"supports_tts": True, "supports_future_thing": True})
    assert c.supports_tts is True
    assert not hasattr(c, "supports_future_thing")
