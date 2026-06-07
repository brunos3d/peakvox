# ACTIVE WORK

> Only work that is **actively being executed right now**. No roadmap, no future ideas, no
> speculative work — those live in [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md) and
> [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md). When an item is no longer being worked, move it
> to the execution ledger or remove it.

**As of:** 2026-06-07 · **Branch:** `feat/peakvox-phase-1`

## In flight

1. **Runtime-Service migration — Phase 1 (ADR + design).** ✅ **Complete** 2026-06-07.
   ADR-0016 (Models as Runtime Services) is Accepted. The
   `docs/.agents/SPECS/FEATURES/models-as-runtime-services/` folder contains SPEC, DESIGN,
   TASKS, VALIDATION, STATUS. No code; per Constitution §22 the ADR is APPROVED, not
   IMPLEMENTED. State files updated (PROJECT_STATE, NEXT_TASK, CURRENT_CONTEXT, ADR_INDEX,
   IMPLEMENTATION_STATUS).

## In flight — next

2. **Runtime-Service migration — Phase 2 (Runtime Manager skeleton + DockerRuntimeDriver).**
   **Not started.** Blocked on a Phase 2 implementation ADR that addresses the deferred
   open questions from ADR-0016: runtime endpoint discovery, GPU allocation, runtime
   health contract, backend-to-runtime auth. The next sequential ADR number after 0016
   is reserved for this.

## Not in flight (recently completed)

- **Runtime-Service architecture (Phase 1).** ✅ Accepted. See
  `docs/.agents/SPECS/FEATURES/models-as-runtime-services/`.
- **Validation reports and state cleanup.** Kokoro provider validation complete (G5 passed).
- **Kokoro Preset Voice Adapter (Phase 1 + 2).** Complete. 54 presets, catalog-only registry,
  metadata-only build_variant, Preset Voices tab.
- **Fish Audio adapter integration.** Wired at the adapter level; blocked on inference hardware.
- **Voice Library 2.0 frontend.** All components implemented (tabs, source asset, artifacts,
  variant dashboard, preset tab).

## Not in flight (explicitly paused)

- **Phases 3–7 of the Runtime-Service migration** (Kokoro, F5-TTS, Fish, OmniVoice
  migrations, in-process path removal). Sequenced behind Phase 2.
- **Cloud phases** (auth/billing/creators/marketplace) — held behind the provider-validation
  readiness gate. The Runtime-Service target is identical in CE and Cloud, so Phase 2
  unblocks both editions; Cloud planning remains a deliberate decision.

---

**Related:** [`NEXT_TASK.md`](NEXT_TASK.md) · [`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) ·
[`IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md`](IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md) ·
[`docs/.agents/SPECS/FEATURES/models-as-runtime-services/`](SPECS/FEATURES/models-as-runtime-services/)
