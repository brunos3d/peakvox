"""ADR-0008 — adapter declares supported_realization_types; VariantBuildResult shape."""

from app.services.model_adapter import ModelAdapter
from app.services.model_adapters.fish_adapter import FishAudioAdapter
from app.services.model_adapters.omnivoice_adapter import (
    OmniVoiceAdapter,
    OmniVoiceSingingAdapter,
)
from app.services.model_catalog import builtin_by_id


def test_omnivoice_declares_reference_sample():
    adapter = OmniVoiceAdapter(builtin_by_id("omnivoice-base"))
    assert adapter.supported_realization_types == ["reference_sample"]
    assert OmniVoiceSingingAdapter(
        builtin_by_id("omnivoice-singing")
    ).supported_realization_types == ["reference_sample"]


def test_fish_declares_reference_sample():
    adapter = FishAudioAdapter(builtin_by_id("fish-audio-s2"))
    assert adapter.supported_realization_types == ["reference_sample"]


def test_realization_types_is_part_of_the_contract():
    # Every adapter exposes the property; the base default is reference_sample.
    assert "supported_realization_types" in dir(ModelAdapter)



