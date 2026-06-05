# HANDOFF

> Agent-to-agent transfer document. Goal: minimize context loss between agents. The incoming
> agent reads this after [`PROJECT_STATE.md`](PROJECT_STATE.md) to know exactly where the
> previous agent stopped. Overwrite the "Current handoff" section each session; append a dated
> line to the log.

---

## Current handoff

**From:** Kokoro Preset Voice Adapter (Phase 1) · **Date:** 2026-06-05 ·
**Branch:** `feat/peakvox-phase-1`

### Last completed work

- **Kokoro Preset Voice Adapter — Phase 1 backend, complete.** 8 tasks implemented via TDD:
  1. `ProviderVoice` frozen dataclass + `build_provider_voice_id()` — ephemeral preset identity.
  2. `ProviderVoiceRegistry` — O(1) dict lifecycle (register, refresh, reload, remove, remove_provider, search).
  3. `ProviderVoiceCatalog` — `@runtime_checkable Protocol` on `ModelAdapter`.
  4. Kokoro `ModelDescriptor` ("kokoro-base") in `BUILTIN_MODELS` — 82M, 9 languages, CPU-capable, TTS-only.
  5. `KokoroAdapter` lifecycle — `install/load/unload` all no-op, `health_check()`→True.
  6. `KokoroAdapter` catalog — 54 presets across 9 languages with deterministic IDs (`voice_kokoro_*`).
  7. `KokoroAdapter.generate()` — lazy `kokoro` import, KPipeline, WAV 24kHz via `soundfile`.
  8. Wiring — `"kokoro": KokoroAdapter` in `model_wiring.py`, auto-population on `register_adapter()`.
- **Runtime two-tier resolution:** registry-first (O(1) dict) → persisted Voice DB → ad-hoc. No string prefix detection (`is_provider_voice_id()` does not exist).
- **339/339 tests passing** (81 new + 258 existing). `test_voices.py` excluded (requires `torch` — Docker only).
- All 5 spec docs written and approved: SPEC.md, DESIGN.md, TASKS.md, STATUS.md (→ IMPLEMENTED), VALIDATION.md (339/339).
- Committed as `ae509d2` (amended with spec docs).

### Files changed (this session)

- **New:** `services/provider_voice.py`, `model_adapters/kokoro_adapter.py`
- **Modified:** `services/runtime.py`, `services/model_catalog.py`, `services/model_wiring.py`, `CHANGELOG.md`
- **Tests (new):** `tests/test_provider_voice.py` (31), `tests/test_kokoro_adapter.py` (34), `tests/test_runtime_provider_voice.py` (16)
- **Docs:** `docs/.agents/SPECS/FEATURES/kokoro-preset-voice-adapter/*` (5 files), `docs/.agents/IMPLEMENTATION_STATUS.md`, `docs/.agents/IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md`

### Architectural decisions taken

- `ProviderVoice` is ephemeral in-memory only — NOT in `db.py`, no migration, no variant, no asset, no artifact (ADR-0010 §8 exempt).
- `voice_` prefix for ALL voice IDs (both persisted and provider) — no `provider_voice_` internal prefix leak.
- Single generation contract: `generate(text, voice_id, model_id)` — no separate `preset_id` field.
- `ProviderVoiceRegistry` is the SOLE resolution mechanism — no `is_provider_voice_id()` string inspection.
- `KokoroAdapter.generate()` imports `kokoro` lazily at call time; `build_variant()` and `clone_voice()` raise `NotImplementedError`.

### Risks (updated)

- **Kokoro real inference still deferred.** Architecture-validated via mock-kokoro tests; real inference requires `kokoro` pip package (not installed in local venv).
- **Fish Audio real inference still blocked.** S2 Pro server needs 24GB+ VRAM.
- **Single-real-provider runtime now challenged by Kokoro pattern.** Kokoro proves the preset-voice, non-cloning provider path — but still no real audio E2E for any non-OmniVoice provider.
- ProviderVoice/presets add new API surface (`/api/v1/presets` planned for Phase 2) not yet designed.

### Open issues

- Phase 2 work items (Voice Library Preset Voices tab, API endpoints for provider voices, creation source onboarding) not started.
- `test_voices.py` requires `torch` — not runnable in local venv.

### Recommended next task

**Phase 2 — UX/API:** Voice Library Preset Voices tab, `/api/v1/presets` endpoints, creation source onboarding for preset voice selection.

---

## Handoff log

- 2026-06-05 — Kokoro Preset Voice Adapter Phase 1 complete. 81 tests, 339/339 all pass.
- 2026-06-05 — Documentation Operating System created under `docs/.agents/`; `AGENTS.md` updated. Application code unchanged. Next: stabilize the dirty working tree.
