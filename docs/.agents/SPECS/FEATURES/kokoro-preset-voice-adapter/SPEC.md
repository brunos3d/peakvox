# SPEC — Kokoro Preset Voice Adapter

> Specification: what & why. SDD stage 2 (after brainstorm).

## Problem

Kokoro is an 82M-param Apache-2.0 TTS model with 54 built-in preset voices (aff_heart,
af_bella, etc.). PeakVox currently assumes every voice originates from a user-provided
reference audio clip (SOURCE_ASSET, ADR-0010) and goes through the Voice/VoiceVariant/Artifact
lifecycle (ADR-0001/0008/0009). Kokoro cannot clone — it has no reference audio, no source
asset, no build step. Forcing it through the existing pipeline would either fabricate a fake
source or require Runtime special-casing.

PeakVox needs an architecture for **provider-native preset voices** — voices that are
ephemeral, model-native, and bypass the provisioning/build/artifact pipeline entirely. Kokoro
is the first provider to require this, but the abstraction must be provider-agnostic (Piper,
Polly, Azure, Cartesia will all have presets).

## Goals / Non-goals

- **Goals:**
  - `ProviderVoice` domain type — ephemeral, in-memory, model-native voice identity
  - `ProviderVoiceCatalog` optional protocol on `ModelAdapter` — provider-agnostic seam
  - `ProviderVoiceRegistry` on `PeakVoxRuntime` — O(1) lookup with full lifecycle
  - `KokoroAdapter(ModelAdapter, ProviderVoiceCatalog)` — implements both contracts
  - Unified generation contract: `runtime.generate(text, voice_id, model_id)` works for both
    persisted voices and provider presets — no separate preset_id field, no synthetic IDs
  - Kokoro model descriptor in `model_catalog.py` with correct capabilities
  - Deterministic voice IDs (`voice_kokoro_af_heart`) — stable across restarts
  - Full test coverage for all new code (TDD)

- **Non-goals (Phase 2):**
  - Voice Library / Preset Voices tab UI
  - `/api/v1/provider-voices` or `/api/v1/voices?type=preset` API endpoints
  - Preset voice "Use" / "Favorite" actions in UI
  - Creation source `PRESET_VOICE` onboarding flow
  - Persisted `PRESET_VOICE` Voice records (the ephemeral `ProviderVoice` is the primary path)
  - Async build queue or generation-time build orchestration
  - Auto-routing / model selector UX

## Requirements

- **Functional:**
  - KokoroAdapter must implement all abstract ModelAdapter methods (install, load, unload,
    health_check, generate, clone_voice, build_variant)
  - KokoroAdapter must implement ProviderVoiceCatalog (list_provider_voices,
    get_provider_voice, has_provider_voice) with all 54 Kokoro presets
  - ProviderVoiceRegistry must support: register, get, list, refresh (atomic replace per
    provider), reload (full rebuild from all ProviderVoiceCatalog adapters), remove,
    remove_provider (model uninstall)
  - Runtime.generate() must resolve provider voices via registry before falling through to
    persisted Voice resolution — no string prefix detection
  - Adapter.generate() receives external_id as voice_id for provider voices (e.g. "af_heart")
  - Kokoro ModelDescriptor in catalog with correct capabilities, languages, tags
  - All existing backend tests must remain green
  - ProviderVoice must NOT appear in db.py, VoiceVariant lifecycle, or ADR-0010 provisioning
  - Kokoro health_check must work without a remote server (Python library import)

- **Constraints (ADR-0004, ADR-0006, ADR-0008, ADR-0010, ADR-0011):**
  - No public API exposure of variant internals (ADR-0004 Rule 1)
  - Realization type `voice_pack` in known taxonomy (ADR-0006)
  - Build lifecycle unchanged — preset path never enters it (ADR-0008)
  - Preset-only providers exempt from ADR-0010 provisioning (ADR-0010 §8)
  - `PRESET_VOICE` creation source honored but no DB migration required (ADR-0011)

## Acceptance criteria

- [ ] `ProviderVoice` frozen dataclass with deterministic `provider_voice_id`
- [ ] `ProviderVoiceCatalog` runtime-checkable protocol
- [ ] `ProviderVoiceRegistry` with full lifecycle (register, refresh, reload, remove, remove_provider, search)
- [ ] Registry populated at wiring time from any `isinstance(adapter, ProviderVoiceCatalog)` adapter
- [ ] `KokoroAdapter` passes TDD for all abstract methods
- [ ] `KokoroAdapter.list_provider_voices()` returns 54 presets
- [ ] `KokoroAdapter.generate(voice_id="af_heart")` produces audio
- [ ] `runtime.generate(voice_id="voice_kokoro_af_heart")` resolves via registry and generates
- [ ] `runtime.generate(public_voice_id="voice_8JXQ29K4L3")` continues to resolve via DB unchanged
- [ ] No string-prefix detection in Runtime — pure registry lookup
- [ ] All 262 existing backend tests still pass
- [ ] ProviderVoice type has NO owner_id, NO creator_id, NO VoiceVariant, NO artifact

## Open questions

- Kokoro pip package name and import path (kokoro ≥0.9.0 published?)
- Kokoro CPU inference performance at 82M params
- Kokoro's `list_voices()` API shape — does it return metadata (name, language, gender) or just keys?
- Should `provider_voice_id` ever need migration / format change?
- Future provider registry must coexist — Piper presets, Polly presets — without name collisions

---

Related: `CONSTITUTION.md` · `DECISIONS/ADR_INDEX.md`
