# CURRENT CONTEXT

> Operational memory. Changes frequently — update at the start and end of every working
> session. Keep it short and current; move history to the execution ledger.

**As of:** 2026-06-07

- **Current focus:** Runtime-Service migration (ADR-0016, accepted). Phase 1 (ADR + design
  docs) complete; Phase 2 (Runtime Manager skeleton + `DockerRuntimeDriver`) is the next
  workstream. Existing in-process model execution continues unchanged.
- **Current branch:** `feat/peakvox-phase-1`
- **Working tree:** clean — this commit adds ADR-0016 and the
  `docs/.agents/SPECS/FEATURES/models-as-runtime-services/` folder (SPEC, DESIGN, TASKS,
  VALIDATION, STATUS). No code, no migrations, no `runtime-registry/` directory.
- **Current ADRs in play:** ADR-0008/0009/0010/0011/0012 (variant lifecycle, artifacts,
  source assets, creation sources, catalog resources) — the surface touched by the
  Runtime-Service architecture. ADR-0016 preserves all five.
- **Current specs:** `docs/.agents/SPECS/FEATURES/models-as-runtime-services/` (new) and
  the existing specs for Voice Library 2.0, Voice System Evolution, etc.
- **Current blockers:** Fish Audio real inference deferred (codec/VRAM); no GPU in CI.
  These predate ADR-0016 and are unaffected by it.
- **Current validation goal:** Phase 1 (this) is architecture-only. Next validation
  milestone is Phase 3 (Kokoro as a remote runtime) — the first provider-validated
  runtime-service migration.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`NEXT_TASK.md`](NEXT_TASK.md) ·
[`HANDOFF.md`](HANDOFF.md) · [`PROJECT_STATE.md`](PROJECT_STATE.md) ·
[`docs/.agents/SPECS/FEATURES/models-as-runtime-services/`](SPECS/FEATURES/models-as-runtime-services/) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md)
