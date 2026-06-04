# ADR-0001: Voice / VoiceVariant split as the core domain spine

- **Status:** Accepted
- **Date:** 2026-06-03
- **Deciders:** Bruno Silva (product owner), architecture planning

## Context

Today `VoiceProfile` fuses two concerns: a voice **identity** (`public_voice_id`, name,
language, characteristics, ownership) and **OmniVoice-specific artifacts** (`audio_filename`,
`transcript`, `voice_design`, `generation_defaults`). PeakVox is becoming **model-agnostic**:
the same voice must be renderable by many inference engines (OmniVoice Base/Singing, Fish,
Kokoro, OpenVoice, …), each needing different artifacts (embeddings, checkpoints, adapters,
reference samples, fine-tunes). The voice is also the **long-term economic asset** the
marketplace, creator economy, and royalties are built on, so its identity must be stable and
independent of any one model.

## Options considered

1. **Keep `VoiceProfile`, bolt per-model artifacts on as an optional side-table.** Lower
   immediate churn. But identity stays entangled with OmniVoice fields; every model-agnostic
   concern (marketplace, royalties, resolution) has to special-case the "primary" model;
   technical debt compounds as models are added. The identity is never cleanly the asset.

2. **Voice (identity) + VoiceVariant (per-model realization) as the primary spine.** A `Voice`
   is the model-agnostic identity and economic asset; a `VoiceVariant`, keyed `(voice_id,
   model_id)`, holds the artifacts one engine needs. The public contract is `Voice + Model →
   VoiceVariant`. Higher upfront migration cost (split + backfill), but every downstream
   concern (multi-model, marketplace, royalties, cloud) is clean.

3. **One row per (voice, model) with no separate identity table.** No identity/realization
   separation at all — duplicates identity metadata per model, breaks the "one stable asset"
   model, and makes royalties/ownership ambiguous.

## Decision

Adopt **Option 2**. `Voice` and `VoiceVariant` are the core domain spine. `VoiceVariant` is
**not** an optional side-table — it is the model-specific realization layer, and `Voice` is the
model-agnostic identity around which the entire architecture is organized. The stable public
contract is `Voice + Model → VoiceVariant`. Existing `VoiceProfile` rows migrate to one `Voice`
plus one OmniVoice `VoiceVariant`, carrying `public_voice_id` over unchanged.

## Consequences

- **Positive:** model-agnostic identity; lazy/regenerable per-model artifacts; clean
  foundation for marketplace, creators, royalties, multi-model, and cloud; the public API stays
  stable across model and artifact changes; `public_voice_id` remains the single external
  contract.
- **Negative / costs:** a non-trivial, central migration (split + backfill + storage-path
  moves + consumer repointing); more entities and a resolution step in the generation path.
- **Follow-ups:** drives the onboarding pipeline (build/regenerate variants), variant
  staleness on model updates ([ADR-0002](0002-model-as-first-class-entity.md)), and the
  resolution logic in [API §3](../04-API_ARCHITECTURE.md). Migration detailed in
  [Migration §2](../08-MIGRATION_ARCHITECTURE.md).
