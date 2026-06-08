# CURRENT CONTEXT

> Operational memory. Changes frequently — update at the start and end of every working
> session. Keep it short and current; move history to the execution ledger.

**As of:** 2026-06-07

- **Current focus:** Phase 2 implementation. ADR-0016
  (Implemented 2A+2B+2C) + ADR-0017 (Implemented 2A+2B+2C)
  are the architectural baseline. **Sub-phases 2A, 2B AND 2C
  are COMPLETE (2026-06-07).** 2A: 9 new modules + 9 test
  files (76 new tests). 2B: `DockerRuntimeDriver` + lint
  script + manager wiring (40 new tests). 2C: `HTTPTransport`
  + `KokoroAdapter` `KOKORO_RUNTIME_URL` integration + env
  plumbing + E2E scaffold (25 new tests, 1 skipped). 0
  regressions; 466 pre-existing tests pass. The next sub-phase
  is **2D (CE operations + runtime-registry + bridge
  activation)**, the LAST sub-phase of Phase 2.
- **Current branch:** `feat/peakvox-phase-1`
- **Working tree:** clean — this commit lands the Phase 2C
  state file updates (IMPLEMENTATION_STATUS, NEXT_TASK,
  ACTIVE_WORK, CURRENT_CONTEXT, PROJECT_STATE,
  ROADMAP/CURRENT_PHASE) promoting 2C complete and 2D next.
- **Current ADRs in play:** ADR-0008/0009/0010/0011/0012
  (variant lifecycle, artifacts, source assets, creation
  sources, catalog resources) — the surface touched by the
  Runtime-Service architecture. ADR-0016 and ADR-0017 preserve
  all five. ADR-0017 is the implementation architecture.
- **Current specs:**
  `docs/.agents/SPECS/FEATURES/models-as-runtime-services/`
  (ADR-0016) and
  `docs/.agents/SPECS/FEATURES/runtime-services-implementation/`
  (ADR-0017), plus existing specs.
- **Current blockers:** Fish Audio real inference deferred
  (codec/VRAM); no GPU in CI. These predate Phase 2A and are
  unaffected.
- **Current validation goal:** Sub-phase 2D lands the Kokoro
  G6 provider-validated E2E report (peakvox backend +
  `peakvox/kokoro-runtime` container, real audio E2E through
  the runtime service). The 2A bridge's `pass` placeholder
  becomes the live runtime-service branch in 2D.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`NEXT_TASK.md`](NEXT_TASK.md) ·
[`HANDOFF.md`](HANDOFF.md) · [`PROJECT_STATE.md`](PROJECT_STATE.md) ·
[`docs/.agents/SPECS/FEATURES/models-as-runtime-services/`](SPECS/FEATURES/models-as-runtime-services/) ·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/`](SPECS/FEATURES/runtime-services-implementation/) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md) ·
[`docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md`](DECISIONS/adr-0017-runtime-services-implementation.md)
