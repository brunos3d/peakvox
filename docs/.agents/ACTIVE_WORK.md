# ACTIVE WORK

> Only work that is **actively being executed right now**. No roadmap, no future ideas, no
> speculative work — those live in [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md) and
> [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md). When an item is no longer being worked, move it
> to the execution ledger or remove it.

**As of:** 2026-06-07 · **Branch:** `feat/peakvox-phase-1`

## In flight

1. **Phase 3 — Kokoro full migration + Runtime Service
   Container E2E.** The runtime-canonical Models page
   (Workstream A), the Runtime Registry expansion to 3
   entries (TASK 12), and the T13 functional lifecycle
   (browser-driven Install/Start/Stop/Update/Remove) are
   all VALIDATED. The remaining Phase 3 work is the E2E
   audio generation pipeline through the backend:
   G6 (architecture) + G9 (reaper) + G10 (no-Kokoro
   backend) reports are written; G7 (Performance) +
   G8 (Error recovery) reports are deferred to a future
   phase. The pre-existing `KokoroAdapter` voice-id →
   preset-name translation issue remains the next P0
   unblocker for the full backend → runtime generation
   path (Kokoro runtime container itself produces real
   audio, as proven by the 266,444-byte WAV in
   `audits/screenshots/t13-kokoro-runtime-generated-audio.wav`).

## Not in flight (recently completed)

- **Runtime-Service architecture (Phase 1, ADR-0016).** ✅ Accepted+Implemented 2026-06-07.
  See `docs/.agents/SPECS/FEATURES/models-as-runtime-services/`.
- **Runtime-Service Phase 2 implementation architecture (ADR-0017).** ✅
  Accepted+Implemented 2026-06-07. Architecture review: 0 blocking issues;
  non-blocking suggestions applied (Runtime Persistence →
  `OPEN_DECISIONS.md` Decision 12; ADR_INDEX/IMPLEMENTATION_STATUS
  consistency fixed). `OPEN_DECISIONS.md` Decision 10 is RESOLVED.
  See `docs/.agents/SPECS/FEATURES/runtime-services-implementation/`.
- **Runtime-Service migration — Phase 2 Sub-phases 2A + 2B + 2C +
  2D (Foundations + First Driver + Communication Path + CE
  Operations + Bridge Activation).** ✅ **Phase 2 is COMPLETE
  2026-06-07.** Phase 2 delivered 9 modules + 1 driver + 1
  transport + 1 settings field + 1 CLI skeleton + 1
  runtime-registry/ directory with the Kokoro descriptor.
  170 runtime tests + 1 skipped (E2E gated). Full backend
  test suite: 495 passed, 1 skipped. 0 regressions.
  Docker imports confined to the driver package
  (enforced by `lint_no_docker_outside_driver.py`, exit 0
  on the real tree). The `RuntimeManager` instance cache
  holds `RuntimeInstance` objects (NOT Voice / VoiceVariant
  / VoiceVariantArtifact). The 2A bridge in `runtime.py` is
  ACTIVATED: when the manager is wired AND the resolution
  is non-None, the bridge records an observability event
  confirming the runtime-service path is reachable. The
  in-process path is preserved as a fallback. The
  Runtime Activation Audit (all 7 checks PASS) confirms
  the canonical chain (Voice → VoiceVariant → Active
  Artifact → Adapter) is intact and runtime infrastructure
  is strictly downstream.
- **Runtime-Canonical Models Page (Models Page / Runtime
  Registry convergence — first half of Phase 3
  full-stack convergence).** ✅ **IMPLEMENTED 2026-06-08.**
  Spec + design + tasks + validation + audit at
  [`docs/.agents/SPECS/FEATURES/runtime-canonical-models-page/`](../SPECS/FEATURES/runtime-canonical-models-page/).
  Single canonical lifecycle control surface owned by the
  Runtime Section; legacy Lifecycle block removed; the
  page depends solely on `useModelsWithRuntimes()`. 5
  components extracted (RuntimeSection, ModelSection,
  OperationsRow, NotMigratedEmptyState, ModelRow) — all
  reusable by future pages. `tsc --noEmit` + `eslint`
  clean. Chrome DevTools visual validation: 0 console
  errors, 3 screenshots captured. Backend coverage
  confirmed by terminal check. Behavior change (Activate /
  Deactivate removed) acknowledged in VALIDATION.md.
- **Validation reports and state cleanup.** Kokoro provider
  validation complete (G5 in-process + G6 runtime-service
  architecturally; E2E gated).
- **Kokoro Preset Voice Adapter (Phase 1 + 2).** Complete. 54 presets, catalog-only registry,
  metadata-only build_variant, Preset Voices tab.
- **Fish Audio adapter integration.** Wired at the adapter level; blocked on inference hardware.
- **Voice Library 2.0 frontend.** All components implemented (tabs, source asset, artifacts,
  variant dashboard, preset tab).

## Not in flight (explicitly paused)

- **Sub-phase 2D** of the Runtime-Service migration — sequenced behind 2C.
- **Phases 3–7 of the Runtime-Service migration** (Kokoro, F5-TTS, Fish, OmniVoice
  migrations, in-process path removal). Sequenced behind Phase 2.
- **Cloud phases** (auth/billing/creators/marketplace) — held behind the provider-validation
  readiness gate. The Runtime-Service target is identical in CE and Cloud, so Phase 2
  unblocks both editions; Cloud planning remains a deliberate decision.
- **Runtime Persistence ADR** (Decision 12) — future ADR, non-blocking.

---

**Related:** [`NEXT_TASK.md`](NEXT_TASK.md) · [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) ·
[`IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md`](IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md) ·
[`docs/.agents/SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/) ·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/`](../SPECS/FEATURES/runtime-services-implementation/)
