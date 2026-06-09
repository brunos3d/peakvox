# Validation — Voice ↔ Model Compatibility (Task 19)

## Phase 1 — Unit tests

All 620 backend tests pass after both fixes.

Key test files that cover the activation_status path:
- `tests/test_api_models_with_runtimes.py` — 12 tests (all pass)
- `tests/test_bridge_activation_phase2d.py` — tests activation bridge
- `tests/test_runtime_registry_authority_t13.py` — Registry as single source of truth

## Phase 2 — Browser E2E (VALIDATED 2026-06-09)

### Validated flow

**Setup:** OmniVoice Base container running; Kokoro 82M not installed.

1. **Models page** — OmniVoice Base shows `Installed / Active` badge (purple). Kokoro 82M
   shows `Not Installed / Inactive`. F5-TTS shows `Not Installed / Inactive`.
   → `activation_status` now comes from `RuntimeManager.resolve()`, not legacy `ModelDescriptor.status`.

2. **Voice Library — Lax detail panel** — Compatible Models shows:
   - "OmniVoice Base [Recommended] [Ready]"
   - "1 ready · 0 buildable · 0 not available"
   - Kokoro 82M absent (inactive → filtered out).

3. **TTS Model Selector** — Shows only "OmniVoice Base [Default] [Loaded]".
   No "No compatible models for the selected voice" error.

4. **TTS Voice Selector** — "Showing 17 compatible with OmniVoice Base · 1 hidden"
   (Alloy Kokoro preset hidden because its model is inactive).
   All 17 cloned voices show the `Compatible` badge.

5. **Generation** — Earlier session (2026-06-09 03:34:44) produced a 0:25 Lax/OmniVoice
   audio clip (history entry: "Seja muito bem-vindo a mais um episódio..." — Completed).
   The runtime pipeline is end-to-end proven.

### Additional fix confirmed

`_build_library_map` Python `and` → `sqlalchemy.and_()`:
Voice Library preset-voice compatibility queries now filter by `(provider, preset_name)`
compound key rather than silently returning only `preset_name`-matched rows.

### Post-fix state

| Surface | Before fix | After fix |
|---|---|---|
| `activation_status` source | `ModelDescriptor.status` (always "active") | `RuntimeManager.resolve()` |
| Models page | OmniVoice shown as inactive | OmniVoice shown as Installed/Active |
| Compatible Models panel | Kokoro appeared (not available) | OmniVoice appears; Kokoro absent |
| TTS Model Selector | "No compatible models" | OmniVoice Base listed |
| Voice cards | "Not compatible" badges | "Compatible" badges (17 voices) |
| Backend tests | 620 pass | 620 pass |
