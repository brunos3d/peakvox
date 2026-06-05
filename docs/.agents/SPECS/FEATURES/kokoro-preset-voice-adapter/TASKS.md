# TASKS — Kokoro Preset Voice Adapter (Phase 2)

> Phase 2: First-class preset Voices. Prerequisite: Phase 1 complete.
> Use TDD per task (RED → GREEN → REFACTOR).

## Phase 1 recap (done)

1–8. ProviderVoice domain, registry, catalog, KokoroAdapter lifecycle, 54 presets,
      generate(), wiring, tests (81 new, 339/339 pass).

## Phase 2 tasks

### A. Backend — Runtime refactor

1. [ ] **Remove two-tier resolution from `runtime.generate()`**
      - Remove `ProviderVoiceRegistry.get(voice_id)` check at top of `generate()`
      - Single path: resolve Voice by `public_voice_id` → VoiceVariant → Artifact
      - Pass `variant.params` as `**kwargs` to `adapter.generate()`
      - Test: provider voice IDs no longer resolve without DB record;
        standard Voice resolution unchanged;
        variant params flow through to adapter

### B. Backend — KokoroAdapter.build_variant()

2. [ ] **Implement `KokoroAdapter.build_variant()` as metadata-only**
      - Return `VariantBuildResult(params={provider, preset_name}, artifacts={}, status="ready")`
      - No audio processing, no embedding, no checkpoint
      - Test: build_variant returns ready status; params contain provider + preset_name;
        build_variant called twice produces version 2 artifact

### C. Backend — Provider voice API

3. [ ] **`GET /api/provider-voices` endpoint**
      - Returns presets from `ProviderVoiceRegistry`
      - Supports `provider`, `language`, `gender`, `search` query params
      - Returns `ProviderVoiceResponse` schema (camelCase for public API)
      - Test: returns all presets; filters work; empty results for unknown params
      - Register router in `main.py`

4. [ ] **`GET /api/provider-voices/{provider_voice_id}` endpoint**
      - Single preset detail from registry
      - Test: returns correct preset; 404 for unknown ID

5. [ ] **`POST /voices/from-preset` endpoint**
      - Accepts `{provider, preset_name, name, model_id}`
      - Validates preset exists in `ProviderVoiceRegistry`
      - Creates Voice (`creation_source="PRESET_VOICE"`, meta={provider, preset_name})
      - Creates VoiceVariant (`params={provider, preset_name}`, `status="ready"`)
      - Creates VoiceVariantArtifact (version 1, metadata-only)
      - Returns `VoiceProfileResponse`
      - Test: creates all 3 records; returns 404 for unknown preset;
        voice appears in My Voices list; generation defaults work

### D. Frontend — Preset Voices tab

6. [ ] **Add preset API functions to `lib/api.ts`**
      - `fetchProviderVoices(params)`, `fetchProviderVoice(id)`, `createVoiceFromPreset(data)`
      - Type: `ProviderVoiceResponse` and `CreateFromPresetRequest`

7. [ ] **Add "Preset Voices" tab to Voice Library**
      - Add `"preset"` to the `TABS` array in `page.tsx`
      - Enable "preset" scope in `useVoicesPage` hook
      - Create `PresetVoicesTab` component with filters
      - Provider/language/gender dropdowns + text search
      - "Use Now" → create Voice from preset → select → route to generate
      - "+ Library" → create Voice from preset → switch to My Voices tab
      - Test: visual verification (no automated frontend tests yet)

### E. Validation

8. [ ] **Run full test suite** — all 339 existing + new tests green
9. [ ] **Update state files** — VALIDATION.md, STATUS.md, IMPLEMENTATION_STATUS.md,
      EXECUTION_LEDGER.md, HANDOFF.md, PROJECT_STATE.md
10. [ ] **Atomic commits**

---

## Task summary

| # | Area | Description | Est. tests |
|---|---|---|---|
| 1 | Runtime | Remove two-tier resolution, pass variant params | ~5 |
| 2 | KokoroAdapter | build_variant() metadata-only | ~3 |
| 3 | API | GET /api/provider-voices | ~6 |
| 4 | API | GET /api/provider-voices/{id} | ~2 |
| 5 | API | POST /voices/from-preset | ~8 |
| 6 | Frontend | lib/api.ts + types | — |
| 7 | Frontend | Preset Voices tab | — |
| 8–10 | Validation | Tests + docs | — |

Related: `DESIGN.md` · `VALIDATION.md` · `STATUS.md`
