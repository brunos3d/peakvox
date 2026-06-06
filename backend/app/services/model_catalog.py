"""Built-in model catalog — the authoritative list of models shipped with the platform.

Seeded into the ``models`` table on startup (idempotent upsert). Adding a model to the
platform means adding a descriptor here (built-in) or inserting a ``models`` row at runtime
(custom/community). The ``provider`` field names the runtime adapter that loads/runs it.

Dependency-light (no torch). Every built-in descriptor below corresponds to a real upstream
provider-backed model source (ADR-0007). Fictional or unverified upstream models must not ship.
"""

from app.models.registry_types import (
    ModelCapabilities,
    ModelDescriptor,
    ModelLicense,
    ModelRequirements,
    ParameterSchema,
    SettingsSchema,
)

# Tag sets ---------------------------------------------------------------------
_BASE_TAGS = [
    "laughter",
    "sigh",
    "confirmation-en",
    "question-en",
    "question-ah",
    "question-oh",
    "question-ei",
    "question-yi",
    "surprise-ah",
    "surprise-oh",
    "surprise-wa",
    "surprise-yo",
    "dissatisfaction-hnn",
]

_SINGING_TAGS = ["singing", "happy", "sad", "angry", "nervous", "whisper", "calm", "excited"]

# Speaker-attribute vocabulary OmniVoice accepts (mirrors frontend voice-design config).
_VOICE_DESIGN = [
    "male",
    "female",
    "child",
    "teenager",
    "young adult",
    "middle-aged",
    "elderly",
    "very low pitch",
    "low pitch",
    "moderate pitch",
    "high pitch",
    "very high pitch",
    "whisper",
    "american accent",
    "british accent",
    "australian accent",
    "canadian accent",
    "indian accent",
]


BUILTIN_MODELS: list[ModelDescriptor] = [
    ModelDescriptor(
        id="omnivoice-base",
        name="OmniVoice Base",
        description="The full-quality OmniVoice model. Voice cloning, multilingual TTS, and "
        "expressive reaction/question/surprise tags.",
        version="1.0.0",
        provider="omnivoice",
        repo_id="k2-fsa/OmniVoice",
        supported_languages=[],  # [] = auto / all languages the model handles
        supported_tags=_BASE_TAGS,
        supported_voice_design=_VOICE_DESIGN,
        capabilities=ModelCapabilities(
            supports_tts=True,
            supports_voice_cloning=True,
            supports_emotions=True,
            supports_singing=False,
            supports_streaming=False,
            supports_api=True,
            supports_emotion_tags=True,
            supports_voice_design=True,
            supports_multilingual=True,
            supports_reference_audio=True,
        ),
        requirements=ModelRequirements(gpu_required=False, runtime="torch"),
        settings_schema=SettingsSchema(
            properties={
                "num_step": ParameterSchema(
                    type="number", label="Inference Steps",
                    default=32, minimum=4, maximum=64, step=1,
                    description="Number of diffusion inference steps. Higher values improve quality at the cost of speed.",
                ),
                "guidance_scale": ParameterSchema(
                    type="number", label="Guidance Scale",
                    default=2.0, minimum=0, maximum=4, step=0.1,
                    description="How closely the output follows the conditioning. Higher = more faithful, lower = more creative.",
                ),
                "speed": ParameterSchema(
                    type="number", label="Speed",
                    default=None, minimum=0.5, maximum=1.5, step=0.05,
                    description="Speaking speed multiplier. Null = auto.",
                ),
                "duration": ParameterSchema(
                    type="number", label="Duration",
                    default=None, minimum=1, maximum=120,
                    description="Maximum audio duration in seconds. Null = auto.",
                ),
                "t_shift": ParameterSchema(
                    type="number", label="Time Shift",
                    default=0.1, minimum=0, maximum=1, step=0.01,
                    description="Time shift parameter for the diffusion process.",
                ),
                "denoise": ParameterSchema(
                    type="boolean", label="Denoise",
                    default=True,
                    description="Apply denoising to the generated audio.",
                ),
            },
        ),
        license=ModelLicense(
            name="Apache License 2.0",
            code="apache-2.0",
            commercial_use=True,
            url="https://huggingface.co/datasets/choosealicense/licenses/raw/main/markdown/apache-2.0.md",
        ),
        provider_metadata={
            "author": "k2-fsa",
            "provider_url": "https://huggingface.co/k2-fsa",
            "homepage_url": "https://huggingface.co/k2-fsa/OmniVoice",
            "repository_url": "https://github.com/k2-fsa/OmniVoice",
            "documentation_url": "https://github.com/k2-fsa/OmniVoice",
            "paper_url": "https://huggingface.co/papers/2604.00688",
            "architecture": "Diffusion language-model TTS finetuned from Qwen/Qwen3-0.6B-Base (paper: 'OmniVoice: Towards Omnilingual Zero-Shot Text-to-Speech with Diffusion Language Models')",
            "model_size": "0.6B params",
            "performance_summary": "RTF 0.025 (vendor-reported)",
            "languages_summary": "646 languages (Hugging Face model card)",
            "metadata_sources": [
                "https://huggingface.co/k2-fsa/OmniVoice",
                "https://github.com/k2-fsa/OmniVoice",
                "https://huggingface.co/datasets/choosealicense/licenses/raw/main/markdown/apache-2.0.md",
            ],
            "requirements_source": "upstream does not publish a minimum VRAM requirement; runtime=torch inferred from Python API",
            "edition_availability_basis": "Apache-2.0 upstream license; approved for CE and Cloud",
        },
        status="available",
        is_default=True,
        editions=["community", "cloud"],
    ),
    ModelDescriptor(
        id="omnivoice-singing",
        name="OmniVoice Singing + Emotion",
        description="Adds sung delivery and a rich emotion set (happy, sad, angry, nervous, "
        "calm, excited) plus whisper, on top of OmniVoice cloning.",
        version="1.0.0",
        provider="omnivoice-singing",
        repo_id="ModelsLab/omnivoice-singing",
        supported_languages=[
            "English", "Chinese", "Japanese", "Korean", "Spanish", "French",
            "German", "Italian", "Russian", "Hindi", "Gujarati",
        ],
        supported_tags=_SINGING_TAGS,
        supported_voice_design=_VOICE_DESIGN,
        capabilities=ModelCapabilities(
            supports_tts=True,
            supports_voice_cloning=True,
            supports_emotions=True,
            supports_singing=True,
            supports_streaming=False,
            supports_api=True,
            supports_emotion_tags=True,
            supports_voice_design=True,
            supports_multilingual=True,
            supports_reference_audio=True,
        ),
        requirements=ModelRequirements(gpu_required=True, runtime="torch"),
        license=ModelLicense(
            name="Apache License 2.0",
            code="apache-2.0",
            weights_license="Training datasets include non-commercial components; commercial use needs legal review before Cloud enablement.",
            commercial_use=True,
            url="https://huggingface.co/datasets/choosealicense/licenses/raw/main/markdown/apache-2.0.md",
        ),
        provider_metadata={
            "author": "ModelsLab",
            "provider_url": "https://huggingface.co/ModelsLab",
            "homepage_url": "https://huggingface.co/ModelsLab/omnivoice-singing",
            "repository_url": "https://huggingface.co/ModelsLab/omnivoice-singing",
            "documentation_url": "https://huggingface.co/ModelsLab/omnivoice-singing",
            "base_model": "k2-fsa/OmniVoice (finetuned from Qwen/Qwen3-0.6B)",
            "model_size": "0.6B params",
            "languages_summary": "11 languages listed on Hugging Face; model card says base multilingual behavior is preserved",
            "metadata_sources": [
                "https://huggingface.co/ModelsLab/omnivoice-singing",
                "https://huggingface.co/k2-fsa/OmniVoice",
                "https://huggingface.co/datasets/choosealicense/licenses/raw/main/markdown/apache-2.0.md",
            ],
            "requirements_source": "upstream examples use CUDA; no published minimum VRAM requirement",
            "edition_availability_basis": "Apache-2.0 model license; available in CE and Cloud, subject to training dataset compliance review",
        },
        status="disabled",
        editions=["community", "cloud"],
    ),
    # First non-OmniVoice provider — validates the multi-provider Runtime (Phase 3.8).
    # CE-only: Fish Audio licensing requires commercial review, so it is available in the
    # Community Edition only (ADR-0005). Disabled until weights/runtime are wired (Risk R-7).
    ModelDescriptor(
        id="kokoro-base",
        name="Kokoro 82M",
        description="Lightweight open-weight TTS with 54 preset voices across 9 languages. "
        "82M params, Apache-2.0, CPU-capable. No voice cloning — preset-only.",
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
        requirements=ModelRequirements(gpu_required=False, runtime="kokoro"),
        settings_schema=SettingsSchema(
            properties={
                "speed": ParameterSchema(
                    type="number", label="Speed",
                    default=1.0, minimum=0.5, maximum=2.0, step=0.1,
                    description="Speaking speed multiplier.",
                ),
            },
        ),
        license=ModelLicense(
            name="Apache License 2.0",
            code="apache-2.0",
            commercial_use=True,
            url="https://huggingface.co/datasets/choosealicense/licenses/raw/main/markdown/apache-2.0.md",
        ),
        provider_metadata={
            "author": "hexgrad",
            "provider_url": "https://huggingface.co/hexgrad",
            "homepage_url": "https://huggingface.co/hexgrad/Kokoro-82M",
            "repository_url": "https://github.com/hexgrad/kokoro",
            "architecture": "StyleTTS 2 + ISTFTNet (decoder-only, no diffusion)",
            "model_size": "82M params",
            "languages_summary": "9 languages across 54 preset voices",
            "metadata_sources": ["https://huggingface.co/hexgrad/Kokoro-82M"],
            "requirements_source": "CPU-capable at 82M params",
            "edition_availability_basis": "Apache-2.0 upstream license; approved for CE and Cloud",
        },
        status="available",
        is_default=False,
        editions=["community", "cloud"],
    ),
    ModelDescriptor(
        id="fish-audio-s2",
        name="Fish Audio S2 Pro",
        description="Fish Audio S2 Pro is Fish Audio's open-weight TTS system with multi-speaker, "
        "multi-turn generation, instruction-following control, streaming-oriented inference, and "
        "voice cloning via Fish-specific speaker embeddings.",
        version="S2",
        provider="fish-audio",
        repo_id="fishaudio/s2-pro",
        supported_languages=[],
        supported_tags=[],
        supported_voice_design=[],
        capabilities=ModelCapabilities(
            supports_tts=True,
            supports_voice_cloning=True,
            supports_api=True,
            supports_reference_audio=True,
            supports_multilingual=True,
            supports_voice_conversion=True,
            supports_streaming=True,
            supports_speaker_embeddings=True,
        ),
        requirements=ModelRequirements(gpu_required=True, runtime="torch/sglang"),
        license=ModelLicense(
            name="Fish Audio Research License",
            code="fish-audio-research",
            weights_license="Research and non-commercial use permitted; commercial use requires a separate Fish Audio license.",
            commercial_use=False,
            url="https://huggingface.co/fishaudio/s2-pro/blob/main/LICENSE.md",
        ),
        provider_metadata={
            "author": "Fish Audio",
            "provider_url": "https://huggingface.co/fishaudio",
            "homepage_url": "https://fish.audio",
            "repository_url": "https://github.com/fishaudio/fish-speech",
            "documentation_url": "https://github.com/fishaudio/fish-speech",
            "paper_url": "https://huggingface.co/papers/2603.08823",
            "architecture": "Dual-AR (Dual-Autoregressive) decoder-only transformer with RVQ audio codec; Slow AR ~4B + Fast AR ~400M params, 10 RVQ codebooks, ~21 Hz frame rate",
            "model_size": "5B params (BF16)",
            "languages_summary": "80+ languages per the Hugging Face model card (Tier-1: Japanese, English, Chinese; Tier-2: Korean, Spanish, Portuguese, Arabic, Russian, French, German)",
            "performance_summary": "RTF 0.195 and ~100 ms time-to-first-audio on a single NVIDIA H200 (vendor-reported)",
            "voice_cloning_method_source": "P0 validation (2026-06-04): Fish Audio S2 Pro uses reference audio for voice cloning, not pre-computed speaker embeddings. The VQ encoding (DAC codec) that produces speaker features is a model-internal step performed at inference time. The PeakVox adapter now treats Fish as reference_sample realization (same pattern as OmniVoice). See docs/architecture/12-PROVIDER-VALIDATION.md §3.2.",
            "metadata_sources": [
                "https://huggingface.co/fishaudio/s2-pro",
                "https://huggingface.co/fishaudio/s2-pro/blob/main/LICENSE.md",
                "https://github.com/fishaudio/fish-speech",
                "https://huggingface.co/papers/2603.08823",
            ],
            "requirements_source": "upstream publishes BF16 5B weights and an SGLang streaming engine; benchmarks tested on NVIDIA H200; no minimum VRAM requirement is published. The PeakVox adapter connects remotely (FISH_AUDIO_SERVER_URL) so no local GPU is required.",
            "edition_availability_basis": "Fish Audio Research License permits research/non-commercial use; Cloud disabled until commercial license review",
        },
        editions=["community"],  # CE-only (ADR-0005)
        status="disabled",
    ),
]


def builtin_by_id(model_id: str) -> ModelDescriptor | None:
    for m in BUILTIN_MODELS:
        if m.id == model_id:
            return m
    return None


def default_model() -> ModelDescriptor:
    for m in BUILTIN_MODELS:
        if m.is_default:
            return m
    raise RuntimeError("No default model defined in BUILTIN_MODELS")
