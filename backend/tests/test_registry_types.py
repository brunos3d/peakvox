from app.models.registry_types import ModelCapabilities, ModelDescriptor


def test_capabilities_defaults():
    caps = ModelCapabilities()
    assert caps.supports_tts is True
    assert caps.supports_voice_cloning is False
    assert caps.supports_emotions is False
    assert caps.supports_singing is False
    assert caps.supports_streaming is False
    assert caps.supports_api is True


def test_descriptor_round_trips_through_dict():
    d = ModelDescriptor(
        id="omnivoice-base",
        name="OmniVoice Base",
        description="The base model",
        version="1.0.0",
        provider="omnivoice",
        repo_id="k2-fsa/OmniVoice",
        model_path=None,
        supported_languages=["en", "zh"],
        supported_tags=["laughter", "sigh"],
        supported_voice_design=["male", "female"],
        capabilities=ModelCapabilities(supports_voice_cloning=True, supports_emotions=True),
        status="available",
        is_default=True,
    )
    dumped = d.model_dump()
    assert dumped["id"] == "omnivoice-base"
    assert dumped["capabilities"]["supports_voice_cloning"] is True
    # Reconstructing from the dump yields an equal descriptor.
    assert ModelDescriptor(**dumped) == d


def test_descriptor_defaults():
    d = ModelDescriptor(id="m", name="M", description="d", provider="omnivoice")
    assert d.version == "1.0.0"
    assert d.supported_languages == []
    assert d.supported_tags == []
    assert d.supported_voice_design == []
    assert d.status == "available"
    assert d.is_default is False
    assert d.editions == ["community"]
    assert d.capabilities.supports_tts is True
