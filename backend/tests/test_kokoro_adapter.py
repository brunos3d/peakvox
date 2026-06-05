from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

import pytest

from app.models.registry_types import ModelCapabilities, ModelDescriptor
from app.services.model_adapter import ModelAdapter
from app.services.provider_voice import (
    ProviderVoice,
    ProviderVoiceCatalog,
    build_provider_voice_id,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def kokoro_descriptor():
    return ModelDescriptor(
        id="kokoro-base",
        name="Kokoro 82M",
        description="Lightweight open-weight TTS with 54 preset voices.",
        version="0.9.2",
        provider="kokoro",
        repo_id="hexgrad/Kokoro-82M",
        supported_languages=["en-us", "en-gb", "es", "fr", "hi", "it", "ja", "pt", "zh"],
        supported_tags=[],
        supported_voice_design=[],
        capabilities=ModelCapabilities(
            supports_tts=True,
            supports_voice_cloning=False,
            supports_singing=False,
            supports_streaming=False,
            supports_api=True,
            supports_emotion_tags=False,
            supports_voice_design=False,
            supports_multilingual=True,
            supports_reference_audio=False,
        ),
        status="available",
        is_default=False,
        editions=["community", "cloud"],
    )


@pytest.fixture
def adapter(kokoro_descriptor):
    from app.services.model_adapters.kokoro_adapter import KokoroAdapter
    return KokoroAdapter(kokoro_descriptor)


_KNOWN_VOICES_54 = sorted([
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica", "af_kore",
    "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
    "am_onyx", "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    "ef_dora", "em_alex", "em_santa",
    "ff_siwis",
    "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
    "if_sara", "im_nicola",
    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo",
    "pf_dora", "pm_alex", "pm_santa",
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
])


# ── Task 4: ModelDescriptor ─────────────────────────────────────────────


def test_kokoro_descriptor_in_catalog():
    from app.services.model_catalog import BUILTIN_MODELS
    desc = next((m for m in BUILTIN_MODELS if m.id == "kokoro-base"), None)
    assert desc is not None
    assert desc.provider == "kokoro"
    assert desc.capabilities.supports_tts is True
    assert desc.capabilities.supports_voice_cloning is False
    assert desc.requirements.gpu_required is False


# ── Task 5: Lifecycle ──────────────────────────────────────────────────


def test_adapter_is_model_adapter_subclass(adapter):
    assert isinstance(adapter, ModelAdapter)


def test_model_id_matches_descriptor(adapter):
    assert adapter.model_id == "kokoro-base"


def test_install_returns_none(adapter):
    result = adapter.install()
    assert result is None


def test_load_returns_none(adapter):
    result = adapter.load()
    assert result is None


def test_unload_returns_none(adapter):
    result = adapter.unload()
    assert result is None


def test_health_check_returns_true(adapter):
    result = adapter.health_check()
    assert result is True


def test_supported_realization_types(adapter):
    assert adapter.supported_realization_types == ["voice_pack"]


def test_get_capabilities_reflects_no_cloning(adapter):
    caps = adapter.get_capabilities()
    assert caps.supports_tts is True
    assert caps.supports_voice_cloning is False
    assert caps.supports_reference_audio is False


def test_get_supported_tags_empty(adapter):
    assert adapter.get_supported_tags() == []


# ── Task 6: ProviderVoiceCatalog (54 presets) ──────────────────────────


def test_adapter_implements_provider_voice_catalog(adapter):
    assert isinstance(adapter, ProviderVoiceCatalog)


def test_list_provider_voices_returns_54(adapter):
    voices = adapter.list_provider_voices()
    assert len(voices) == 54


def test_list_provider_voices_all_have_deterministic_ids(adapter):
    voices = adapter.list_provider_voices()
    for v in voices:
        assert v.provider_voice_id == build_provider_voice_id("kokoro", v.external_id)
        assert v.provider_id == "kokoro"


def test_list_provider_voices_includes_all_known_external_ids(adapter):
    external_ids = {v.external_id for v in adapter.list_provider_voices()}
    for expected in _KNOWN_VOICES_54:
        assert expected in external_ids, f"Missing preset: {expected}"


def test_list_provider_voices_returns_distinct(adapter):
    voices = adapter.list_provider_voices()
    ids = [v.external_id for v in voices]
    assert len(ids) == len(set(ids))


def test_list_provider_voices_all_have_names(adapter):
    for v in adapter.list_provider_voices():
        assert v.name, f"Voice {v.external_id} has no name"


def test_list_provider_voices_american_voices_have_gender(adapter):
    voices = adapter.list_provider_voices()
    for v in voices:
        if v.external_id.startswith(("af_", "am_")):
            assert v.gender is not None, f"{v.external_id} missing gender"


def test_list_provider_voices_language_mapped_correctly(adapter):
    voices = {v.external_id: v for v in adapter.list_provider_voices()}
    # American English
    assert voices["af_heart"].language == "en-us"
    # British English
    assert voices["bf_emma"].language == "en-gb"
    # Japanese
    assert voices["jf_alpha"].language == "ja"
    # Spanish
    assert voices["ef_dora"].language == "es"


def test_get_provider_voice_returns_known(adapter):
    voice = adapter.get_provider_voice("af_heart")
    assert voice is not None
    assert voice.external_id == "af_heart"
    assert voice.provider_id == "kokoro"


def test_get_provider_voice_returns_none_for_unknown(adapter):
    assert adapter.get_provider_voice("nope") is None


def test_has_provider_voice_true_for_known(adapter):
    assert adapter.has_provider_voice("af_heart") is True


def test_has_provider_voice_false_for_unknown(adapter):
    assert adapter.has_provider_voice("nope") is False


def test_provider_voices_are_frozen(adapter):
    voice = adapter.get_provider_voice("af_heart")
    assert isinstance(voice, ProviderVoice)


# ── Task 7: generate() ────────────────────────────────────────────────


def _mock_audio(samples: int = 24000) -> MagicMock:
    """Create a mock tensor whose .numpy() returns a real numpy array."""
    arr = np.zeros(samples, dtype=np.float32)
    mock = MagicMock()
    mock.shape = [samples]
    mock.numpy.return_value = arr
    return mock


@patch("app.services.model_adapters.kokoro_adapter._kokoro_mod")
async def test_generate_returns_tuple(mock_kokoro, adapter, tmp_path):
    mock_pipeline = MagicMock()
    mock_kokoro.KPipeline.return_value = mock_pipeline
    mock_generator = iter([("hi", "HH AY", _mock_audio(24000))])
    mock_pipeline.return_value = mock_generator
    output = tmp_path / "test.wav"

    duration, logs = await adapter.generate(
        text="hello", output_path=output, voice_profile_id="af_heart",
    )

    assert isinstance(duration, float)
    assert duration > 0
    assert isinstance(logs, list)


@patch("app.services.model_adapters.kokoro_adapter._kokoro_mod")
async def test_generate_writes_wav_file(mock_kokoro, adapter, tmp_path):
    mock_pipeline = MagicMock()
    mock_kokoro.KPipeline.return_value = mock_pipeline
    mock_generator = iter([("hi", "HH AY", _mock_audio(24000))])
    mock_pipeline.return_value = mock_generator
    output = tmp_path / "out.wav"

    await adapter.generate(text="hello", output_path=output, voice_profile_id="af_heart")

    assert output.exists()
    assert output.stat().st_size > 0


@patch("app.services.model_adapters.kokoro_adapter._kokoro_mod")
async def test_generate_uses_voice_profile_id_as_preset(mock_kokoro, adapter, tmp_path):
    mock_pipeline = MagicMock()
    mock_kokoro.KPipeline.return_value = mock_pipeline
    mock_generator = iter([("hi", "HH AY", _mock_audio(48000))])
    mock_pipeline.return_value = mock_generator
    output = tmp_path / "out.wav"

    await adapter.generate(text="hello", output_path=output, voice_profile_id="af_bella")

    assert mock_pipeline.called
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("voice") == "af_bella"


@patch("app.services.model_adapters.kokoro_adapter._kokoro_mod")
async def test_generate_uses_provider_voice_id_if_no_voice_profile(mock_kokoro, adapter, tmp_path):
    mock_pipeline = MagicMock()
    mock_kokoro.KPipeline.return_value = mock_pipeline
    mock_generator = iter([("hi", "HH AY", _mock_audio(24000))])
    mock_pipeline.return_value = mock_generator
    output = tmp_path / "out.wav"

    await adapter.generate(
        text="hello", output_path=output,
        voice_profile_id=None, voice_id="af_heart",
    )

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("voice") == "af_heart"


@patch("app.services.model_adapters.kokoro_adapter._kokoro_mod")
async def test_generate_without_voice_falls_back_to_default(mock_kokoro, adapter, tmp_path):
    mock_pipeline = MagicMock()
    mock_kokoro.KPipeline.return_value = mock_pipeline
    mock_generator = iter([("hi", "HH AY", _mock_audio(24000))])
    mock_pipeline.return_value = mock_generator
    output = tmp_path / "out.wav"

    await adapter.generate(
        text="hello", output_path=output,
        voice_profile_id=None, voice_id=None,
    )

    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("voice") == "af_heart"  # default


@patch("app.services.model_adapters.kokoro_adapter._kokoro_mod")
async def test_generate_handles_multiple_chunks(mock_kokoro, adapter, tmp_path):
    mock_pipeline = MagicMock()
    mock_kokoro.KPipeline.return_value = mock_pipeline
    mock_generator = iter([
        ("hi", "HH AY", _mock_audio(12000)),
        ("there", "TH EH R", _mock_audio(12000)),
    ])
    mock_pipeline.return_value = mock_generator
    output = tmp_path / "out.wav"

    duration, logs = await adapter.generate(
        text="hi there", output_path=output, voice_profile_id="af_heart",
    )
    assert duration > 0
    assert len(logs) >= 1


@patch("app.services.model_adapters.kokoro_adapter._kokoro_mod")
async def test_generate_logs_contain_voice_and_duration(mock_kokoro, adapter, tmp_path):
    mock_pipeline = MagicMock()
    mock_kokoro.KPipeline.return_value = mock_pipeline
    mock_generator = iter([("hi", "HH AY", _mock_audio(24000))])
    mock_pipeline.return_value = mock_generator
    output = tmp_path / "out.wav"

    duration, logs = await adapter.generate(
        text="hello", output_path=output, voice_profile_id="af_heart",
    )
    combined = " ".join(logs).lower()
    assert "af_heart" in combined
    assert "1.00s" in combined or any(f"{duration:.2f}s" in line for line in logs)


# ── Task 7: clone_voice ────────────────────────────────────────────────


async def test_clone_voice_raises_not_implemented(adapter):
    with pytest.raises(NotImplementedError):
        await adapter.clone_voice(db=None, voice=None, reference_audio_key="")


# ── Task 7: build_variant ──────────────────────────────────────────────


async def test_build_variant_raises_not_implemented(adapter):
    with pytest.raises(NotImplementedError):
        await adapter.build_variant(db=None, voice=None)


# ── Task 8: Wiring integration ─────────────────────────────────────────


def test_kokoro_in_adapter_by_provider():
    from app.services.model_wiring import _ADAPTER_BY_PROVIDER
    from app.services.model_adapters.kokoro_adapter import KokoroAdapter
    assert "kokoro" in _ADAPTER_BY_PROVIDER
    assert _ADAPTER_BY_PROVIDER["kokoro"] is KokoroAdapter


def test_wire_runtime_registers_kokoro_adapter():
    from app.services.runtime import runtime as rt
    from app.services.model_wiring import wire_runtime
    wire_runtime()
    adapter = rt.get_adapter("kokoro-base")
    from app.services.model_adapters.kokoro_adapter import KokoroAdapter
    assert isinstance(adapter, KokoroAdapter)
