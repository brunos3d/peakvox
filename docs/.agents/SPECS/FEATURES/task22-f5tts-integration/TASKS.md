# Task 22 — F5-TTS Integration: Tasks

## Backend

- [x] T22-B1: Create `F5TTSAdapter` with SOURCE_ASSET build strategy, voice-optional generate, build_variant
- [x] T22-B2: Register F5TTSAdapter in `model_wiring.py` (`_ADAPTER_BY_PROVIDER["f5-tts"]`)
- [x] T22-B3: Add `supports_voice_optional: bool = False` to `ModelCapabilities`
- [x] T22-B4: Add `supports_voice_optional=True` + settings schema to F5-TTS catalog entry
- [x] T22-B5: Remove `POST /variants/backfill` endpoint from `variants.py`
- [x] T22-B6: Update F5-TTS runtime server to handle `ref_audio_path=None` + expose tunable params

## Frontend

- [x] T22-F1: Add `supports_voice_optional?: boolean` to `ModelCapabilities` type; remove `BackfillResponse`
- [x] T22-F2: Remove `backfillMissingVariants()` from `api.ts`
- [x] T22-F3: Add `["models"]` cache invalidation to `useRuntimeLifecycleAction`
- [x] T22-F4: Fix `useActiveModel()` to prefer active models before catalog default
- [x] T22-F5: Fix `GenerationPanel` — replace `model?.loaded` with `activation_status === "active"`
- [x] T22-F6: Fix `GenerationPanel` — voice-optional `canGenerate` + hint text
- [x] T22-F7: Fix `ModelSelector` default selection to prefer active models
- [x] T22-F8: Remove Backfill Missing button from `VariantDashboard`
- [x] T22-F9: Fix offline banner in `page.tsx` to use `activation_status`

## Validation

- [ ] T22-V1: Backend test suite (659 baseline) — verified passing
- [ ] T22-V2: TypeScript type check — zero errors verified
- [ ] T22-V3: Browser E2E — 5 scenarios (see VALIDATION.md)
