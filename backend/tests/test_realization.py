from app.services.realization import (
    REALIZATION_TYPES,
    is_known_realization,
    DEFAULT_REALIZATION,
)


def test_canonical_realization_types_present():
    for r in (
        "reference_sample", "reference_audio", "embedding", "checkpoint",
        "lora", "speaker_token", "voice_pack", "prompt", "metadata",
    ):
        assert r in REALIZATION_TYPES


def test_known_realization_check_is_forward_compatible():
    assert is_known_realization("embedding") is True
    # Unknown/new types are tolerated (opaque), not rejected — they just aren't "known" yet.
    assert is_known_realization("quantum_voice_field") is False


def test_default_realization_is_reference_sample():
    assert DEFAULT_REALIZATION == "reference_sample"
    assert DEFAULT_REALIZATION in REALIZATION_TYPES
