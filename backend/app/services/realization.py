"""Voice Variant Realization Types (ADR-0006).

A *realization* is HOW a model stores a voice — the format of a ``VoiceVariant``'s artifacts
(``VoiceVariant.artifact_type``). It is an implementation detail owned by the Runtime and the
owning model's adapter, and must NEVER leak into public APIs, Voice IDs, the Voice Library, or
the marketplace (ADR-0004). The set is open: new types are additive and tolerated by everything
that isn't the owning adapter (forward-compatible).
"""

DEFAULT_REALIZATION = "reference_sample"

# Canonical (open) taxonomy. Adapters declare their variant's realization via this value.
REALIZATION_TYPES: frozenset[str] = frozenset(
    {
        "reference_sample",   # reference clip (+ optional transcript) — e.g. OmniVoice
        "reference_audio",    # raw reference audio, no transcript
        "embedding",          # precomputed speaker embedding — e.g. Fish Audio
        "checkpoint",         # fine-tuned checkpoint for the voice
        "lora",               # LoRA adapter for the voice
        "speaker_token",      # learned speaker token / id
        "voice_pack",         # preset voice pack / bundled asset
        "prompt",             # prompt-based voice definition
        "metadata",           # metadata-only realization
    }
)


def is_known_realization(realization: str) -> bool:
    """True if the realization is in the canonical taxonomy.

    Unknown types are *valid* (forward-compatible) but simply not yet canonical — callers treat
    them as opaque rather than rejecting them.
    """
    return realization in REALIZATION_TYPES
