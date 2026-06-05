# SPEC — Kokoro Preset Voice Adapter

> Specification: what & why. SDD stage 2 (after brainstorm).

## Problem

Kokoro is an 82M-param Apache-2.0 TTS model with 54 built-in preset voices. PeakVox
previously assumed every voice originates from user-provided reference audio (SOURCE_ASSET)
and requires a build step (ADR-0008). Kokoro cannot clone — it has no reference audio, no
embedding, no build step.

PeakVox needs an architecture for **provider-native preset voices**. Kokoro is the first
provider to require this, but the abstraction must be provider-agnostic.

The architecture must also ensure that preset voices are **first-class Voices** — they
participate in the full Voice → VoiceVariant → VoiceVariantArtifact → Generation lifecycle.
No special-case generation path, no runtime branching on creation source.

## Goals / Non-goals

### Phase 1 (done) — Domain types + catalog + adapter
- `ProviderVoice` domain type — ephemeral, in-memory, model-native voice identity
- `ProviderVoiceCatalog` optional protocol on `ModelAdapter`
- `ProviderVoiceRegistry` — catalog of available presets (listing, filtering, search)
- `KokoroAdapter(ModelAdapter, ProviderVoiceCatalog)` — 54 presets, lazy kokoro import
- Kokoro model descriptor in `model_catalog.py`
- Deterministic voice IDs (`voice_kokoro_{external_id}`)

### Phase 2 (this spec) — First-class preset Voices
- **Preset Voices are first-class Voices** — created via `POST /voices/from-preset`
- Full participation in VoiceVariant lifecycle (ADR-0008, ADR-0009)
- `KokoroAdapter.build_variant()` creates metadata-only variant/artifact (no heavy build)
- Runtime has a **single generation path**: Voice → VoiceVariant → Active Artifact
- `ProviderVoiceRegistry` is **catalog-only** — no participation in generation resolution
- `GET /api/provider-voices` — list/search presets with filters
- Voice Library "Preset Voices" tab with provider/language/gender/search
- "Use Now" creates Voice + Variant + Artifact → selects → normal generation

### Non-goals
- Async build queue
- Auto-routing / model selector UX
- Provider voice audio preview in catalog
- Bulk import of presets

## Requirements

### Backend
- `POST /voices/from-preset` accepts `{provider, preset_name, name, model_id}`:
  - Creates `Voice` with `creation_source = "PRESET_VOICE"`
  - Creates `VoiceVariant` with `params = {provider, preset_name}`, `status = "ready"`
  - Creates `VoiceVariantArtifact` (version 1, metadata-only)
  - Returns `VoiceProfileResponse`
- `GET /api/provider-voices` lists presets from `ProviderVoiceRegistry`:
  - Supports `provider`, `language`, `gender`, `search` query params
- `runtime.generate()` has a single resolution path:
  - Resolve Voice by `public_voice_id`
  - Resolve VoiceVariant for the model
  - Extract variant params → pass as `**kwargs` to `adapter.generate()`
  - No ProviderVoiceRegistry check
- `KokoroAdapter.build_variant()` creates metadata-only variant/artifact:
  - `params = {provider: "kokoro", preset_name: "<name>"}`
  - `status = "ready"`
  - No audio processing, no embedding generation
- `KokoroAdapter.generate()` reads `provider` / `preset_name` from `**kwargs`

### Frontend
- Voice Library gets a "Preset Voices" tab (the `"preset"` VoiceScope already exists)
- Provider/language/gender dropdown filters + text search
- Each preset card shows: name, provider, language, gender, tags
- "Use Now" button → `POST /voices/from-preset` → select resulting Voice → normal generate
- "+ Library" button → `POST /voices/from-preset` → shows in My Voices tab

### Constraints
- `ProviderVoiceRegistry` must NOT participate in generation resolution
- No string-prefix detection in Runtime
- `build_variant()` must NOT raise `NotImplementedError` for any provider
- All existing backend tests must remain green

## Acceptance criteria

- [ ] `POST /voices/from-preset` creates Voice + Variant + Artifact with correct creation_source
- [ ] `GET /api/provider-voices` returns presets with filters
- [ ] `runtime.generate()` resolves presets through standard Voice DB path
- [ ] `KokoroAdapter.build_variant()` creates metadata-only variant (status=ready)
- [ ] `KokoroAdapter.generate()` accepts preset_name from kwargs
- [ ] Frontend Preset Voices tab shows presets with filters
- [ ] "Use Now" button creates Voice and routes to generation
- [ ] "+ Library" button creates Voice and shows in My Voices
- [ ] All 339 existing tests still pass (plus new tests)

---

Related: `DESIGN.md` · `TASKS.md` · `VALIDATION.md`
