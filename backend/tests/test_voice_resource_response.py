"""Tests for VoiceResourceResponse schema, VoiceResourceService, and ImportResolver."""

import pytest
from pydantic import ValidationError

from app.schemas.voice_resource import VoiceResourceResponse
from app.services.provider_voice import ProviderVoice, build_provider_voice_id


# ── H3: VoiceResourceResponse schema ──────────────────────────────────────


def test_voice_resource_response_minimal():
    resp = VoiceResourceResponse(
        id="voice_preset_kokoro",
        resource_type="preset",
        resource_origin="kokoro",
        name="Heart",
    )
    assert resp.id == "voice_preset_kokoro"
    assert resp.resource_type == "preset"
    assert resp.resource_origin == "kokoro"
    assert resp.name == "Heart"
    assert resp.description == ""
    assert resp.language is None
    assert resp.is_in_library is False
    assert resp.library_voice_id is None


def test_voice_resource_response_requires_id():
    with pytest.raises(ValidationError):
        VoiceResourceResponse(
            resource_type="preset",
            resource_origin="kokoro",
            name="x",
        )


def test_voice_resource_response_defaults_resource_type():
    resp = VoiceResourceResponse(
        id="x",
        resource_origin="kokoro",
        name="x",
    )
    assert resp.resource_type == "preset"


def test_voice_resource_response_requires_resource_origin():
    with pytest.raises(ValidationError):
        VoiceResourceResponse(
            id="x",
            resource_type="preset",
            name="x",
        )


def test_voice_resource_response_requires_name():
    with pytest.raises(ValidationError):
        VoiceResourceResponse(
            id="x",
            resource_type="preset",
            resource_origin="kokoro",
        )


def test_voice_resource_response_full():
    resp = VoiceResourceResponse(
        id="voice_kokoro_af_heart",
        resource_type="preset",
        resource_origin="kokoro",
        name="Heart",
        description="Warm female voice",
        language="en",
        preview_audio_url="/some/preview.wav",
        catalog_source={"type": "adapter", "adapter_id": "kokoro"},
        provider_id="kokoro",
        external_id="af_heart",
        gender="female",
        is_default=True,
        is_in_library=True,
        library_voice_id="lib-123",
        compatible_models=["kokoro-base"],
        recommended_model_id="kokoro-base",
    )
    assert resp.provider_id == "kokoro"
    assert resp.external_id == "af_heart"
    assert resp.is_in_library is True
    assert resp.library_voice_id == "lib-123"
    assert resp.compatible_models == ["kokoro-base"]


# ── H1: ProviderVoice resource_origin ─────────────────────────────────────


def test_provider_voice_resource_origin_defaults_to_provider_id():
    pv = ProviderVoice(
        provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
        provider_id="kokoro",
        external_id="af_heart",
        name="Heart",
    )
    assert pv.resource_origin == "kokoro"


def test_provider_voice_resource_origin_custom():
    pv = ProviderVoice(
        provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
        provider_id="kokoro",
        external_id="af_heart",
        name="Heart",
        resource_origin="community",
    )
    assert pv.resource_origin == "community"


def test_provider_voice_catalog_source():
    pv = ProviderVoice(
        provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
        provider_id="kokoro",
        external_id="af_heart",
        name="Heart",
        catalog_source={"type": "adapter", "adapter_id": "kokoro", "version": "1.0"},
    )
    assert pv.catalog_source == {"type": "adapter", "adapter_id": "kokoro", "version": "1.0"}


def test_provider_voice_catalog_source_default_none():
    pv = ProviderVoice(
        provider_voice_id=build_provider_voice_id("kokoro", "af_heart"),
        provider_id="kokoro",
        external_id="af_heart",
        name="Heart",
    )
    assert pv.catalog_source is None
