# Execution Ledger

> Historical implementation memory. **Append-only** — never rewrite past entries. A future
> agent should understand implementation history here without mining git. One entry per
> meaningful unit of work.
>
> Entry format: Date · Task · Spec/Plan · ADR(s) · Files · Validation · Result.

---

### 2026-06-05 · Documentation Operating System
- **Task:** Build `docs/.agents/` as the single Agent Knowledge Base (agent OS, indexes, SDD scaffold).
- **Spec/Plan:** this task (documentation architecture).
- **ADRs:** none new (documentation-only).
- **Files:** all of `docs/.agents/**`; `frontend/AGENTS.md` (Documentation Operating System section).
- **Validation:** structural — references resolve to canonical docs; no app code touched.
- **Result:** Knowledge base created. References (not copies) the canonical architecture/ADR/spec docs.

### 2026-06-04 · Variant Backfill UX + manual provisioning
- **Task:** Manual + bulk variant creation from source assets; cross-model compatibility view.
- **Plan:** `superpowers/plans/2026-06-04-variant-backfill-ux.md`.
- **ADRs:** 0008, 0010, 0011.
- **Files:** `api/variants.py`, `api/variants_summary.py`, `scripts/backfill_variants.*`, frontend `VariantDashboard.tsx`, `ModelCompatibilitySection.tsx`, `VariantManager.tsx`.
- **Validation:** frontend build + backend syntax; commits `02bd6a4`, `f8803b4`, `ae44a3e`, `bc19dfb`.
- **Result:** Implemented. `/variants/backfill` endpoint + "Backfill Missing" UI; `expire_on_commit=False` fix (`3212254`).

### 2026-06-04 · Voice Library 2.0
- **Task:** Expose Voice → Source Asset → Variant → Artifact → Generation chain with progressive disclosure.
- **Plan:** `superpowers/plans/2026-06-04-voice-library-2.md`.
- **ADRs:** 0001, 0008, 0009, 0010, 0011.
- **Files:** `schemas/voice.py`, `api/voices.py`, frontend voice components, `types/index.ts`, `lib/api.ts`.
- **Validation:** backend tests + frontend build; commits `bb4af9d`…`b3f686b`.
- **Result:** Implemented. Tabbed drawer, source asset tab, variant matrix, artifact history + rollback, Variant Dashboard.

### 2026-06-04 · ADR-0011 Voice Creation Sources
- **Task:** Generalize ADR-0010; a voice's origin is a Creation Source, not always a WAV.
- **ADRs:** 0011 (generalizes 0010; cross-refs across 9 docs).
- **Files:** `adrs/0011-voice-creation-sources.md` + cross-references.
- **Validation:** terminology + link consistency; commit `7dac264`.
- **Result:** Accepted (architecture only).

### 2026-06-04 · ADR-0010 Voice Source Assets + Automatic Variant Provisioning
- **Task:** Architecture decision: variants provisioned from a Source Asset.
- **ADRs:** 0010 (extends 0006/0008/0009).
- **Files:** `adrs/0010-...md` + cross-references across the suite.
- **Validation:** documentation only; commit `930` (per memory).
- **Result:** Accepted (architecture only).

### 2026-06-04 · Phase 1 Retrospective + Provider Validation Program
- **Task:** Separate architecture validation from provider validation; document the 8-gate process; establish the readiness gate.
- **Files:** `architecture/11-PHASE-1-RETROSPECTIVE.md`, `architecture/12-PROVIDER-VALIDATION.md`, registry metadata corrections (OmniVoice/Singing/Fish).
- **Validation:** 237 backend tests / 55 files baseline.
- **Result:** Documented. Recommendation: no SaaS work before one real foreign provider validates.

### 2026-06-04 · Phases 3.5–3.11 (Runtime foundation → artifact versioning)
- **Task:** Runtime + capability contract + multi-model adapters + runtime exclusivity + edition scoping + universal voice asset + build lifecycle + artifacts.
- **ADRs:** 0003, 0004, 0005, 0006, 0008, 0009.
- **Files:** `services/runtime.py`, `model_adapter.py`, `model_adapters/`, `capabilities.py`, `variant_lifecycle.py`, `voice_variant_artifact_repository.py`.
- **Validation:** comprehensive backend test suite (architecture-validated).
- **Result:** Implemented; Fish adapter present but inference unwired.

### 2026-06-03 · Phases 1–3 (CE spine) + architecture hardening
- **Task:** Platform foundations, model registry, Voice/Variant split, dual-write CRUD; strategic vision + Runtime layer formalization + capability contract + separation rules.
- **ADRs:** 0001, 0002, 0003, 0004, 0007.
- **Files:** `models/db.py`, `model_registry.py`, `model_catalog.py`, `voice_variant_repository.py`, `variant_resolution.py`, `voice_onboarding.py`, architecture suite `00`–`10` + ADRs.
- **Validation:** full regression + frontend verification.
- **Result:** Implemented; architecture suite consistent before Phase 1 implementation.

### 2026-06-05 · Kokoro Preset Voice Adapter (Phase 1)
- **Task:** ProviderVoice domain type, ProviderVoiceCatalog protocol, ProviderVoiceRegistry lifecycle, KokoroAdapter (54 presets, generate), runtime two-tier resolution, auto-population wiring.
- **Spec/Plan:** `docs/.agents/SPECS/FEATURES/kokoro-preset-voice-adapter/`
- **ADRs:** 0010 (exempt from asset/provisioning), 0008 (build_variant → NotImplementedError for presets).
- **Files:** `services/provider_voice.py`, `model_adapters/kokoro_adapter.py`, `runtime.py`, `model_catalog.py`, `model_wiring.py`, `tests/test_provider_voice.py`, `tests/test_kokoro_adapter.py`, `tests/test_runtime_provider_voice.py`, spec docs (SPEC/DESIGN/TASKS/STATUS/VALIDATION), `CHANGELOG.md`.
- **Validation:** 81 new tests (31 + 34 + 16), 339/339 all pass (full suite). Deterministic `voice_*` IDs. No string prefix detection. 54 presets across 9 languages.
- **Result:** Implemented. Kokoro is the first non-OmniVoice provider architecture-validated through the Runtime. ProviderVoice proves the preset-voice, non-cloning provider pattern (ADR-0008/0010 edge cases).

### 2026-06-05 · Stabilise and commit in-flight working tree
- **Task:** Commit Fish-adapter expansion, variant schema, migrations, voice_id dual-path, VoiceSourceAsset model — everything that had been uncommitted.
- **Plans:** `superpowers/plans/2026-06-04-voice-library-2.md`, `superpowers/plans/2026-06-04-variant-backfill-ux.md`.
- **ADRs:** 0008, 0009, 0010, 0011.
- **Fix:** Missing `creation_source` column in `_backfill_voice_split` INSERT (caused NOT NULL constraint failure).
- **Commits:** `2732236` (db model + migrations), `fcdfbc9` (schemas + generation API), `e714cb9` (Fish adapter + contract), `cd900f2` (tests).
- **Validation:** `262 passed in 14.34s` — full backend test suite green.
- **Result:** Clean `git status`; 4 Conventional Commits; state files updated.

### 2026-06-05 · Kokoro Preset Voice — Phase 2 (first-class preset Voices)
- **Task:** Make preset voices first-class Voice entities with full Voice→VoiceVariant→VoiceVariantArtifact→Generation lifecycle; catalog-only ProviderVoiceRegistry; metadata-only build_variant; Preset Voices frontend tab.
- **Spec/Plan:** `docs/.agents/SPECS/FEATURES/kokoro-preset-voice-adapter/` (Phase 2 sections); `docs/.agents/IMPLEMENTATION/PLANS/kokoro-preset-voice-phase-2.md`.
- **ADRs:** 0001 (Voice/Variant split), 0004 (separation), 0008 (build lifecycle — build_variant participation), 0009 (artifact versioning).
- **Files:**
  - `services/runtime.py` — removed two-tier resolution; single DB-path resolution; variant params flow as generate kwargs
  - `model_adapters/kokoro_adapter.py` — `build_variant()` creates metadata-only VoiceVariant (no audio/embedding)
  - `schemas/provider_voice.py` — NEW; `ProviderVoiceResponse`, `CreateFromPresetRequest`
  - `api/provider_voices.py` — NEW; `GET /api/provider-voices` endpoints with filters
  - `api/voices.py` — `POST /voices/from-preset` (materializes preset into VoiceProfile+VoiceVariant+Artifact)
  - `main.py` — registered provider_voices router
  - `tests/test_runtime_single_path.py` — NEW (2 tests)
  - `tests/test_provider_voices_api.py` — NEW (7 tests)
  - `tests/test_voices_from_preset.py` — NEW (2 tests)
  - `frontend/src/types/index.ts`, `lib/api.ts` — types + API functions
  - `frontend/src/components/voice/PresetVoicesTab.tsx` — NEW; preset voices tab with filters + cards
  - `frontend/src/app/voices/page.tsx` — added Preset Voices tab
  - `frontend/src/hooks/use-generation.ts` — no change (preset scope not added to useVoicesPage)
- **Design changes:**
  - ProviderVoiceRegistry is catalog-only — no longer participates in generation resolution
  - `KokoroAdapter.build_variant()` creates metadata-only variant (not NotImplementedError)
  - All providers participate identically in ADR-0008 lifecycle
  - `POST /voices/from-preset` (not `/from-preset/use`) — client orchestrates create→generate
- **Validation:** 347/347 backend tests pass (8 new + 339 baseline). Frontend: 0 new TS errors (only pre-existing `VariantDashboard.tsx` error). Full suite: `pytest tests/ --ignore=tests/test_voices.py` all green.
- **Result:** Phase 2 implemented and validated. All commits on `feat/peakvox-phase-1`. State files updated.

### 2026-06-05 · Kokoro Provider Validation (G5 passed)
- **Task:** Validate Kokoro as the first non-OmniVoice provider — install kokoro, generate real audio E2E through Runtime, record results.
- **Spec/Plan:** P0 from `NEXT_TASK.md`; `OPEN_DECISIONS.md` Decision 1 Option 3.
- **ADRs:** 0008 (build lifecycle), 0010 (variant provisioning), 0011 (onboarding), 0012/0013 (reserved).
- **Files:**
  - `backend/requirements.txt` — added `kokoro`
  - `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-validation-report.md` — NEW; 8-gate assessment
  - `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/provider-validation.md` — updated Kokoro scorecard (G5 ✅), section 4, Go/no-go, status
  - `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/README.md` — Kokoro → Validated
  - `docs/.agents/ACTIVE_WORK.md` — Kokoro validation moved from "In flight" to "Completed"
  - `docs/.agents/NEXT_TASK.md` — rewritten: gate is open
  - `docs/.agents/OPEN_DECISIONS.md` — Decision 1 → RESOLVED
  - `docs/.agents/PROJECT_STATE.md` — priorities, risks, readiness gate updated
  - `docs/.agents/HANDOFF.md` — risks, next task, handoff log updated
  - `docs/.agents/IMPLEMENTATION_STATUS.md` — Kokoro row updated
  - `docs/.agents/IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md` — this entry
- **Validation:** 347/347 backend tests pass (with real kokoro installed). Real audio generated: 4.05s WAV (24kHz, 194KB) via `af_heart`.
- **State change:** OPEN_DECISIONS Decision 1 → RESOLVED. Cloud readiness gate → OPEN.
- **Branch:** `feat/peakvox-phase-1`. All changes committed.

### 2026-06-10 · T24 — TTS Generation Regression Investigation (OmniVoice + F5-TTS)
- **Task:** Root-cause and eliminate the production generation failures of both real TTS providers; validate live; add regression tests.
- **Spec/Plan:** `docs/.agents/SPECS/FEATURES/task24-tts-generation-regression/` (SPEC/DESIGN/TASKS/VALIDATION/STATUS → VALIDATED).
- **ADRs:** 0017 (runtime service contract — generation routing), 0003 (capability contract — voice-optional classification), 0004 (variant internals stay internal).
- **Root causes fixed:**
  1. `OmniVoiceAdapter.generate()` unconditionally raised — never consumed `runtime_endpoint` (T21 gap). Now routes via `HTTPTransport.post_binary("/v1/generate")` with a 600 s timeout (CPU inference ~3.5 min).
  2. F5-TTS meta-tensor crash: `transcript: null` → `ref_text=""` → f5-tts Whisper ASR → torch 2.12 crash. Effective-ref_text chain + neutral placeholder at the adapter AND the runtime server.
  3. OmniVoice runtime server used a nonexistent API: `OmniVoicePipeline` → `OmniVoice.from_pretrained("k2-fsa/OmniVoice")`, `generate()` surface, voice_design list joined to one instruct string, `(1, N)` batch tensors squeezed (duration was 0 ms).
- **By-design confirmations:** voice-optional UI differences are capability-driven (`supports_voice_optional` only on F5-TTS); sample-voice compatibility already reports `['f5-tts-base']` for all SOURCE_ASSET voices (Jarvis/Lucas Montano just lack a built variant).
- **Files:**
  - `backend/app/services/model_adapters/omnivoice_adapter.py` — HTTP routing + 600 s transport
  - `backend/app/services/model_adapters/f5_adapter.py` — effective-ref_text + ASR-bypass placeholder
  - `runtime-registry/omnivoice-base/server.py` — correct class/API, instruct join, squeeze
  - `runtime-registry/f5-tts-base/server.py` — cloning-mode transcript fallback
  - NEW tests: `backend/tests/test_t24_omnivoice_adapter_routing.py` (11), `backend/tests/test_t24_f5_adapter_ref_text.py` (10), `runtime-registry/omnivoice-base/tests/test_server.py` (17), `runtime-registry/f5-tts-base/tests/test_server.py` (15)
  - Docs: T24 spec folder; `CURRENT_CONTEXT.md`, `ACTIVE_WORK.md`, `NEXT_TASK.md`, `HANDOFF.md`, this ledger
- **Validation:** Live — F5-TTS: Fireship 8.10 s (the crashing voice), Donald Trump 6.87 s, Bruno PT-BR 3.46 s, voice-optional 5.75 s; OmniVoice: 5.92 s via container with correct duration. Tests — backend 680 passed, 1 skipped; runtime suites 41/41/19 passed.
- **Deployment note:** running containers patched via `docker exec` + `docker commit` + restart; registry sources are canonical and supersede on next image build.
- **Branch:** `feat/peakvox-phase-1`.
