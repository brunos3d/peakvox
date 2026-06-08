# CURRENT CONTEXT

> Operational memory. Changes frequently — update at the start and end of every working
> session. Keep it short and current; move history to the execution ledger.

**As of:** 2026-06-07

- **Current focus:** Phase 2 implementation. ADR-0016 (Accepted) +
  ADR-0017 (Accepted) are the architectural baseline. **Sub-phases
  2A and 2B are COMPLETE (2026-06-07).** 2A: 9 new modules + 9
  test files (76 new tests). 2B: `DockerRuntimeDriver` + lint
  script + manager wiring (40 new tests). 0 regressions; 441
  pre-existing tests pass. The next sub-phase is **2C
  (HTTPTransport + KokoroAdapter migration)**, the first
  sub-phase to introduce the runtime-service communication path.
- **Current branch:** `feat/peakvox-phase-1`
- **Working tree:** clean — this commit lands the Phase 2B
  implementation: 1 new module (`docker_runtime_driver.py`) +
  1 new script (`lint_no_docker_outside_driver.py`) + 2
  modified modules (`runtime_manager.py`, `__init__.py` for the
  drivers package) + 2 new test files (40 new tests). Plus
  state file updates (IMPLEMENTATION_STATUS, NEXT_TASK,
  CURRENT_CONTEXT, ACTIVE_WORK, PROJECT_STATE, ROADMAP/*).
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
- **Current validation goal:** Sub-phase 2C is the first
  provider-validated runtime-service migration (Kokoro +
  runtime service E2E). The 2A bridge's `pass` placeholder
  becomes the live runtime-service branch in 2C.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`NEXT_TASK.md`](NEXT_TASK.md) ·
[`HANDOFF.md`](HANDOFF.md) · [`PROJECT_STATE.md`](PROJECT_STATE.md) ·
[`docs/.agents/SPECS/FEATURES/models-as-runtime-services/`](SPECS/FEATURES/models-as-runtime-services/) ·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/`](SPECS/FEATURES/runtime-services-implementation/) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md) ·
[`docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md`](DECISIONS/adr-0017-runtime-services-implementation.md)
