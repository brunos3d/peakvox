# CURRENT CONTEXT

> Operational memory. Changes frequently — update at the start and end of every working
> session. Keep it short and current; move history to the execution ledger.

**As of:** 2026-06-07

- **Current focus:** Phase 3 implementation. **Phase 2 is
  COMPLETE (2026-06-07).** ADR-0016 + ADR-0017 are
  Accepted+Implemented (2A+2B+2C+2D). The Runtime
  Activation Audit (all 7 checks PASS) confirms the
  canonical chain (Voice → VoiceVariant → Active Artifact
  → Adapter) is intact and runtime infrastructure is
  strictly downstream. 2A: 9 modules + 9 test files
  (76 new tests). 2B: `DockerRuntimeDriver` + lint script
  + manager wiring (40 new tests). 2C: `HTTPTransport` +
  `KokoroAdapter` `KOKORO_RUNTIME_URL` integration + env
  plumbing + E2E scaffold (25 new tests, 1 skipped).
  2D: `runtime-registry/` with Kokoro descriptor +
  `RuntimeManager` instance cache + CE operations + 2A
  bridge activation + CLI skeleton + Kokoro G6
  provider-validated report (32 new tests). **Phase 2
  total: 170 runtime tests + 1 skipped (E2E gated).**
  Full backend test suite: 495 passed, 1 skipped. 0
  regressions. The next workstream is **Phase 3 (Kokoro
  full migration)**: make the runtime-service path the
  DEFAULT for Kokoro in CE.
- **Current branch:** `feat/peakvox-phase-1`
- **Working tree:** clean — this commit lands the Phase 2D
  state file updates (IMPLEMENTATION_STATUS, NEXT_TASK,
  ACTIVE_WORK, CURRENT_CONTEXT, PROJECT_STATE,
  ROADMAP/CURRENT_PHASE) promoting Phase 2 complete and
  Phase 3 next.
- **Current ADRs in play:** ADR-0008/0009/0010/0011/0012
  (variant lifecycle, artifacts, source assets, creation
  sources, catalog resources) — the surface touched by the
  Runtime-Service architecture. ADR-0016 and ADR-0017
  preserve all five. ADR-0017 is the implementation
  architecture; both are now Accepted+Implemented.
- **Current specs:**
  `docs/.agents/SPECS/FEATURES/models-as-runtime-services/`
  (ADR-0016) and
  `docs/.agents/SPECS/FEATURES/runtime-services-implementation/`
  (ADR-0017), plus existing specs.
- **Current blockers:** Fish Audio real inference deferred
  (codec/VRAM); no GPU in CI. These predate Phase 2A and
  are unaffected. Phase 3 requires a real
  `peakvox/kokoro-runtime` container in the docker-compose
  CI lane; the E2E scaffold is in place but gated.
- **Current validation goal:** Phase 3 lands the
  E2E-validated Kokoro G6 report (real audio E2E through
  the runtime service in the docker-compose CI lane), G7
  (Performance) and G8 (Error recovery) reports. Phase 3
  makes the runtime-service path the DEFAULT for Kokoro in
  CE; the in-process path is preserved as a fallback.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`NEXT_TASK.md`](NEXT_TASK.md) ·
[`HANDOFF.md`](HANDOFF.md) · [`PROJECT_STATE.md`](PROJECT_STATE.md) ·
[`docs/.agents/SPECS/FEATURES/models-as-runtime-services/`](SPECS/FEATURES/models-as-runtime-services/) ·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/`](SPECS/FEATURES/runtime-services-implementation/) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md) ·
[`docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md`](DECISIONS/adr-0017-runtime-services-implementation.md)
