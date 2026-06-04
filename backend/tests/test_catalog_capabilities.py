from app.services.model_catalog import builtin_by_id


def test_base_declares_design_multilingual_reference():
    caps = builtin_by_id("omnivoice-base").capabilities
    assert caps.supports_tts and caps.supports_voice_cloning
    assert caps.supports_voice_design
    assert caps.supports_multilingual
    assert caps.supports_reference_audio
    assert caps.supports_emotion_tags
    assert caps.supports_singing is False  # base does not sing


def test_singing_declares_singing_and_emotion_tags():
    caps = builtin_by_id("omnivoice-singing").capabilities
    assert caps.supports_singing is True
    assert caps.supports_emotion_tags is True
    assert caps.supports_voice_cloning is True
    assert caps.supports_reference_audio is True


def test_singing_tags_include_singing_set():
    singing = builtin_by_id("omnivoice-singing")
    assert "singing" in singing.supported_tags
    assert "whisper" in singing.supported_tags
