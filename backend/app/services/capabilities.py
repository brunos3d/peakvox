"""Centralized Model Capability Contract helpers (ADR-0003).

One source of truth that the Runtime, API, UI, and validation all consume. Behavior is driven
by *declared capabilities*, never by model id/name — there is deliberately no per-provider
branching anywhere in the platform. Adding a model means declaring its capabilities, not
editing call sites.
"""

from dataclasses import dataclass

from app.models.registry_types import ModelCapabilities


@dataclass(frozen=True)
class CapabilitySpec:
    key: str
    label: str
    description: str


# UI/marketplace metadata for each capability. The frontend renders controls/badges from this
# registry, so a new capability surfaces without any hardcoded per-model conditionals.
CAPABILITY_REGISTRY: dict[str, CapabilitySpec] = {
    "supports_tts": CapabilitySpec("supports_tts", "Text-to-Speech", "Synthesize speech from text."),
    "supports_voice_cloning": CapabilitySpec("supports_voice_cloning", "Voice cloning", "Clone a voice from reference audio."),
    "supports_voice_conversion": CapabilitySpec("supports_voice_conversion", "Voice conversion", "Convert source speech into a target voice."),
    "supports_singing": CapabilitySpec("supports_singing", "Singing", "Sung delivery."),
    "supports_emotions": CapabilitySpec("supports_emotions", "Emotions", "Expressive emotional delivery (legacy flag)."),
    "supports_emotion_tags": CapabilitySpec("supports_emotion_tags", "Emotion tags", "Inline emotion/reaction tags."),
    "supports_voice_design": CapabilitySpec("supports_voice_design", "Voice design", "Design a voice from controlled attributes."),
    "supports_streaming": CapabilitySpec("supports_streaming", "Streaming", "Low-latency streaming output."),
    "supports_multilingual": CapabilitySpec("supports_multilingual", "Multilingual", "Multiple languages."),
    "supports_reference_audio": CapabilitySpec("supports_reference_audio", "Reference audio", "Accepts a reference audio clip."),
    "supports_batch_generation": CapabilitySpec("supports_batch_generation", "Batch generation", "Generate multiple outputs in one request."),
    "supports_api": CapabilitySpec("supports_api", "Public API", "Usable through the public API."),
}


def supports(capabilities: ModelCapabilities, key: str) -> bool:
    """True if a capability is declared. Unknown capabilities are False (forward-compatible)."""
    return bool(getattr(capabilities, key, False))


def missing_capabilities(capabilities: ModelCapabilities, required: set[str]) -> set[str]:
    """Return the requested capabilities the model does not declare (empty == all satisfied)."""
    return {key for key in required if not supports(capabilities, key)}


def capability_dict(capabilities: ModelCapabilities) -> dict:
    """Serialise capabilities for API/UI consumption."""
    return capabilities.model_dump()
