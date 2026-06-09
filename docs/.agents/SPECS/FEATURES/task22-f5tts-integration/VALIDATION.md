# Task 22 — F5-TTS Integration: Validation

## Automated

| Check | Result |
|---|---|
| Backend pytest (659 tests) | PASSED |
| TypeScript `tsc --noEmit` | PASSED (0 errors) |

## Browser E2E Scenarios

These require F5-TTS runtime container running and OmniVoice runtime active.

### Scenario 1: Voice-free F5-TTS generation
1. Select F5-TTS as model, no voice selected
2. Enter text, click Generate
3. Expected: generation proceeds; hint "will use its built-in default voice" shown

### Scenario 2: F5-TTS cloning with sample voice
1. Select a sample voice from library
2. Select F5-TTS as model
3. Compatibility grid shows voice as "buildable"
4. Generate — variant is built on demand, audio returns with cloned voice characteristic

### Scenario 3: Install → selectors update
1. Install a runtime from Models page
2. Expected: model selectors immediately reflect `activation_status: active`
3. Verified via `["models"]` cache invalidation in `useRuntimeLifecycleAction`

### Scenario 4: Stop → selectors react
1. Stop active runtime
2. Expected: model shows `inactive` in Generate panel model selector and offline banner appears

### Scenario 5: Remove → unavailable
1. Remove a runtime
2. Expected: model disappears from active model list; no crash

## Architecture Correctness

- Compatibility derived from `CompatibilityResolver` + build strategies — no hardcoded model lists
- `activation_status` is the single source of truth for model readiness (not `model?.loaded`)
- Backfill endpoint removed — capability-driven architecture makes it obsolete
- `supports_voice_optional` capability flag governs generate button and UI hints
