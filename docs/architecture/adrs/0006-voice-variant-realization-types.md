# ADR-0006: Voice Variant Realization Types

- **Status:** Accepted
- **Date:** 2026-06-04
- **Deciders:** Bruno Silva (product owner), architecture planning

## Context

We have proven a single Voice is realized differently per provider (ADR-0001, Phase 3.7–3.10):

- **OmniVoice** → a **reference sample** (+ transcript).
- **Fish Audio** → a **speaker embedding**.

Future providers will introduce more formats: reference audio, embeddings, fine-tuned
checkpoints, LoRA adapters, speaker tokens, voice packs, prompt-based voices, and
provider-specific formats not yet imagined. These formats are **implementation details of how a
provider stores a voice** — they must never leak into the public surface, and the platform must
accommodate new ones without changing the Voice contract.

The conceptual layering this ADR formalizes:

```
Voice                  the model-agnostic identity (public_voice_id)        [ADR-0001/0004]
  └── VoiceVariant     the (Voice × Model) realization row                  [ADR-0001]
        └── Realization   HOW this model stores the voice (the format)      [this ADR]
```

## Options considered

1. **Leave realization implicit / per-adapter ad-hoc.** Each adapter invents its own variant
   shape with no shared taxonomy. Works short-term; risks inconsistency and accidental leakage
   of provider internals into APIs/UI as providers multiply. Rejected.

2. **A formal, open Realization Type taxonomy on `VoiceVariant.artifact_type`,** owned by the
   Runtime/adapters and never exposed publicly. **Chosen.**

## Decision

A **VoiceVariant Realization Type** is a declared, enumerated kind on
`VoiceVariant.artifact_type`, describing *how* a model stores a voice. It is an
**implementation detail owned by the Runtime + the model's adapter** and is **never exposed** on
public APIs, Voice IDs, the Voice Library, or the marketplace.

### Realization taxonomy (open set)

| Realization | Meaning | Example provider |
|---|---|---|
| `reference_sample` | A reference audio clip (+ optional transcript) cloned at inference | OmniVoice |
| `reference_audio` | Raw reference audio, no transcript | (generic cloning) |
| `embedding` | A precomputed speaker embedding vector | Fish Audio |
| `checkpoint` | A fine-tuned model checkpoint for the voice | fine-tune providers |
| `lora` | A LoRA adapter for the voice | LoRA providers |
| `speaker_token` | A learned speaker token / id | token-based models |
| `voice_pack` | A preset voice pack / bundled asset | Kokoro-style presets |
| `prompt` | A prompt-based voice definition (text/style prompt) | prompt-driven models |
| `metadata` | Metadata-only realization (no heavy artifact) | lightweight cases |

The set is **open**: new realization types are **additive**. The canonical list lives in
`backend/app/services/realization.py` (`REALIZATION_TYPES`). An adapter declares its variant's
realization via `artifact_type`; unknown/new types are tolerated (forward-compatible) and simply
treated as opaque by anything that isn't the owning adapter.

### Rules (normative)

1. **Realization never leaks.** No `/v1` response, Voice ID, Voice Library, or marketplace
   surface exposes the realization type or its artifacts. The public contract is
   `public_voice_id` + `model` only ([ADR-0004](0004-voice-variant-model-separation.md)).
2. **The Runtime + owning adapter are the only readers** of a variant's realization/artifacts.
3. **Adding a realization type is additive** — no migration of existing variants, no change to
   the Voice contract, no UI redesign.
4. **A Voice may hold many realizations simultaneously** (one per model), all under one stable
   `public_voice_id`. Realization is a property of the (Voice × Model) variant, never of the
   Voice.

## Consequences

- **Positive:** a shared, documented vocabulary for variant formats; new provider formats are
  additive and encapsulated; the developer never needs to know how a provider stores a voice;
  the public contract is insulated from provider internals permanently.
- **Negative / costs:** adapters must set an accurate `artifact_type`; the taxonomy needs light
  governance (additions are deliberate). No enforcement that an adapter reads only its own
  realization — upheld by review + the boundary in [Runtime §6](../10-RUNTIME_ARCHITECTURE.md).
- **Follow-ups:** `REALIZATION_TYPES` constant + validation helper; adapters reference it
  (OmniVoice → `reference_sample`, Fish → `embedding`). Builds on
  [ADR-0001](0001-voice-variant-split.md); orthogonal to capabilities
  ([ADR-0003](0003-model-capability-contract.md)) and edition availability
  ([ADR-0005](0005-edition-scoped-model-availability.md)).
