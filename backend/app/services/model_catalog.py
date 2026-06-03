"""Built-in model catalog — the authoritative list of models shipped with the platform.

Seeded into the ``models`` table on startup (idempotent upsert). Adding a model to the
platform means adding a descriptor here (built-in) or inserting a ``models`` row at runtime
(custom/community). The ``provider`` field names the runtime adapter that loads/runs it.

Dependency-light (no torch). ``repo_id`` values for Distilled/Singing must be confirmed
against the upstream OmniVoice releases before those models are enabled (see plan Risk R-7);
until verified they ship with ``status="disabled"``.
"""

from app.models.registry_types import ModelCapabilities, ModelDescriptor

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
        ),
        status="available",
        is_default=True,
    ),
    ModelDescriptor(
        id="omnivoice-distilled",
        name="OmniVoice Distilled",
        description="A faster, distilled variant of OmniVoice Base. Same tags and cloning, "
        "fewer diffusion steps for quicker generation.",
        version="1.0.0",
        provider="omnivoice",
        repo_id="k2-fsa/OmniVoice-distilled",
        supported_languages=[],
        supported_tags=_BASE_TAGS,
        supported_voice_design=_VOICE_DESIGN,
        capabilities=ModelCapabilities(
            supports_tts=True,
            supports_voice_cloning=True,
            supports_emotions=True,
            supports_singing=False,
            supports_streaming=False,
            supports_api=True,
        ),
        # Disabled until the upstream repo id/capabilities are confirmed (Risk R-7).
        status="disabled",
    ),
    ModelDescriptor(
        id="omnivoice-singing",
        name="OmniVoice Singing + Emotion",
        description="Adds sung delivery and a rich emotion set (happy, sad, angry, nervous, "
        "calm, excited) plus whisper, on top of OmniVoice cloning.",
        version="1.0.0",
        provider="omnivoice-singing",
        repo_id="k2-fsa/OmniVoice-singing",
        supported_languages=[],
        supported_tags=_SINGING_TAGS,
        supported_voice_design=_VOICE_DESIGN,
        capabilities=ModelCapabilities(
            supports_tts=True,
            supports_voice_cloning=True,
            supports_emotions=True,
            supports_singing=True,
            supports_streaming=False,
            supports_api=True,
        ),
        # Disabled until the upstream repo id/capabilities are confirmed (Risk R-7).
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
