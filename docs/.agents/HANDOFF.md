# HANDOFF

> Agent-to-agent transfer document. Goal: minimize context loss between agents. The incoming
> agent reads this after [`PROJECT_STATE.md`](PROJECT_STATE.md) to know exactly where the
> previous agent stopped. Overwrite the "Current handoff" section each session; append a dated
> line to the log.

---

## Current handoff

**From:** Kokoro Preset Voice — Phase 2 · **Date:** 2026-06-05 ·
**Branch:** `feat/peakvox-phase-1`

### Last completed work

- **Kokoro Preset Voice — Phase 2, complete.** Preset voices are now first-class Voice entities.
  1. **A1 — Two-tier resolution removed.** `runtime.generate()` now always resolves through DB (Voice→VoiceVariant→Artifact). ProviderVoiceRegistry is catalog-only.
  2. **A2 — Metadata-only build_variant.** `KokoroAdapter.build_variant()` creates VoiceVariant with params={provider, preset_name}, artifacts={}, status=pending. All providers participate identically in ADR-0008 lifecycle.
  3. **A3 — Provider-voices API.** `GET /api/provider-voices` (list/filter/search) and `GET /api/provider-voices/{id}` (single detail).
  4. **A4 — From-preset creation.** `POST /voices/from-preset` materializes presets into VoiceProfile + VoiceVariant + VoiceVariantArtifact.
  5. **B5–B7 — Frontend.** PresetVoicesTab with provider/language/gender/search filters, PresetVoiceCard with "Use Now" (create+select+navigate to TTS) and "+ Library" (create+switch to My Voices).
- **347/347 tests passing** (8 new Phase 2 + 339 Phase 1 baseline). Frontend: 0 new TS errors.
- All Phase 2 spec docs updated: SPEC.md, DESIGN.md, TASKS.md, STATUS.md (→ IMPLEMENTED), VALIDATION.md (Phase 2 table).

### Files changed (this session)

- **Modified (backend):** `services/runtime.py`, `model_adapters/kokoro_adapter.py`, `api/voices.py`, `main.py`, `tests/test_runtime_provider_voice.py`, `tests/test_kokoro_adapter.py`
- **New (backend):** `schemas/provider_voice.py`, `api/provider_voices.py`, `tests/test_runtime_single_path.py`, `tests/test_provider_voices_api.py`, `tests/test_voices_from_preset.py`
- **Modified (frontend):** `types/index.ts`, `lib/api.ts`, `app/voices/page.tsx`, `hooks/use-generation.ts`
- **New (frontend):** `components/voice/PresetVoicesTab.tsx`
- **Docs:** Phase 2 implementation plan, updated VALIDATION/STATUS/IMPLEMENTATION_STATUS/EXECUTION_LEDGER/HANDOFF

### Architectural decisions taken

- `ProviderVoiceRegistry` is catalog-only — no longer participates in generation resolution (ADR-0001/0004/0008/0009/0010/0011 aligned).
- `KokoroAdapter.build_variant()` creates metadata-only VoiceVariant — no audio, no embedding, no checkpoint. All providers participate identically in ADR-0008 lifecycle.
- Provider metadata stored as `{provider, preset_name}` (not `{provider_voice_id}`).
- Single generation endpoint (`POST /generate`). No `/from-preset/use` shortcut. Client orchestrates: `POST /voices/from-preset` → `POST /generate`.
- `voice_` prefix for all voice IDs (both persisted and provider) — no `provider_voice_` internal prefix leak.

### Risks (updated)

- **Kokoro real inference still deferred.** Architecture-validated via mock-kokoro tests; real inference requires `kokoro` pip package.
- **Fish Audio real inference still blocked.** S2 Pro server needs 24GB+ VRAM.
- **Kokoro build_variant creates metadata-only variants.** The runtime's `_run_build()` still calls `append_artifact()` + `set_active()` after `build_variant()`. For Kokoro, this creates empty artifacts. This is correct behavior but untested for the Kokoro-specific path.

### Open issues

- Phase 3 work items (provider voice marketplace / community presets, multi-provider preset merging) not started.
- `test_voices.py` requires `torch` — not runnable in local venv.
- `VariantDashboard.tsx` has a pre-existing TypeScript error (unrelated).

### Recommended next task

**Provider validation:** Install `kokoro` pip package, run real Kokoro inference E2E, validate audio output quality.

---

## Handoff log

- 2026-06-05 — Kokoro Preset Voice Adapter Phase 1 complete. 81 tests, 339/339 all pass.
- 2026-06-05 — Documentation Operating System created under `docs/.agents/`; `AGENTS.md` updated. Application code unchanged. Next: stabilize the dirty working tree.
- 2026-06-05 — Kokoro Preset Voice Phase 2 complete. 8 new tests, 347/347 all pass. Frontend Preset Voices tab added.
