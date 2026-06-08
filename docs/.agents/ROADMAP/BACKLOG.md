# Backlog

> Groomed list of future work not yet active. Active work lives in [`../ACTIVE_WORK.md`](../ACTIVE_WORK.md);
> the single next item in [`../NEXT_TASK.md`](../NEXT_TASK.md). Ordered by priority.

**As of:** 2026-06-07

## P0 — Gating

1. ~~**Stabilize + commit the in-flight working tree.**~~ ✅ Complete (commit landed).
2. ~~**First foreign-provider validation.**~~ ✅ **Kokoro G5 passed** (real audio generated
   E2E through the Runtime). Cloud readiness gate is **OPEN**.
3. ~~**ADR-0017 (Phase 2 implementation architecture).**~~ ✅ **Accepted** 2026-06-07.
   See [ADR-0017](../DECISIONS/adr-0017-runtime-services-implementation.md) and
   [`../SPECS/FEATURES/runtime-services-implementation/`](../SPECS/FEATURES/runtime-services-implementation/).
   Architecture review: 0 blocking issues. Non-blocking suggestions applied
   (Runtime Persistence → `OPEN_DECISIONS.md` Decision 12).
4. ~~**Runtime-Service migration — Phase 2 Sub-phase 2A (Foundations).**~~ ✅
   **Complete 2026-06-07.** 9 new modules + 9 test files (76 new tests);
   401/401 pre-existing tests pass; no Docker integration, no
   Runtime Service communication, no model framework imports, no
   HTTP clients. `PeakVoxRuntime` bridge is a transitional
   pass-through; behavior unchanged in 2A. See
   [`IMPLEMENTATION_STATUS.md` §"Phase 2A — Runtime Services
   Foundations"](../IMPLEMENTATION_STATUS.md).
5. ~~**Runtime-Service migration — Phase 2 Sub-phase 2B (`DockerRuntimeDriver`).**~~ ✅
   **Complete 2026-06-07.** 1 new module (`docker_runtime_driver.py`) +
   1 new script (`lint_no_docker_outside_driver.py`) + 2 modified
   modules (`runtime_manager.py`, `__init__.py` for the drivers
   package) + 2 new test files (40 new tests; 441 pre-existing
   tests pass; 0 regressions). Docker imports confined to the
   driver package (enforced by the lint script, exit 0 on the real
   tree). The `RuntimeManager.resolve()` is updated to return a
   non-None `RuntimeResolution` when a driver is wired; the 2A
   bridge in `runtime.py` is unchanged (the runtime-service branch
   is still a literal `pass`; activation is in 2C).
6. **Runtime-Service migration — Phase 2 Sub-phase 2C (`HTTPTransport` +
   KokoroAdapter `KOKORO_RUNTIME_URL` path).** TDD tasks in
   [`../SPECS/FEATURES/runtime-services-implementation/TASKS.md`](../SPECS/FEATURES/runtime-services-implementation/TASKS.md) §2C.
   First P0 work item: `HTTPTransport` for adapters;
   `KokoroAdapter` `KOKORO_RUNTIME_URL` integration; env plumbing;
   E2E validation report; status updates. The 2A bridge's
   runtime-service branch is activated in this sub-phase.
7. **Runtime-Service migration — Sub-phase 2D** (CE operations:
   install/activate/update/remove + `runtime-registry/` with Kokoro
   descriptor). Sequenced behind 2C.
8. **Runtime-Service migration — Phases 3–7** (Kokoro, F5-TTS, Fish, OmniVoice migrations,
   in-process path removal). Sequenced behind Phase 2.

## P1 — CE hardening (can proceed in parallel with Phase 2)

6. **Phase 9 — Public API harden:** freeze `/v1`, consistent error model (402/409/410/422),
   `pv_` key transition, publish OpenAPI, ship SDK, deprecation policy.
7. **OmniVoice end-to-end audio test** (gated/optional CI lane with weights) to move OmniVoice
   from PARTIAL to VALIDATED on the provider axis.
8. **Fish S2 Pro server deployment** (subject to existing hardware blocker — 24GB+ VRAM
   required; see
   [`../VALIDATION/PROVIDER_VALIDATIONS/`](../VALIDATION/PROVIDER_VALIDATIONS/)).
9. **Kokoro G7 (performance) and G8 (error recovery)** measurement — low priority.

## P2 — Provisioning decisions (write the reserved ADRs when decided)

10. ADR-0012 Variant Provisioning Policies (per Creation Source).
11. ADR-0013 Model Categories (cloning vs preset vs training).
12. **Future driver ADRs:** `KubernetesRuntimeDriver` (Cloud), `PodmanRuntimeDriver`,
    `LocalProcessDriver` (one ADR per driver when its edition begins; see
    [`../OPEN_DECISIONS.md`](../OPEN_DECISIONS.md) Decision 11).
13. **Runtime Persistence ADR** (see
    [`../OPEN_DECISIONS.md`](../OPEN_DECISIONS.md) Decision 12). Non-blocking.
    Future work for fleet management, operational dashboards, historical
    health tracking, Cloud orchestration, runtime metrics.

## P3 — Cloud ecosystem (no longer blocked on P0.2; sequencing is now deliberate)

13. Phase 4 Auth (Clerk adapter + principal resolution + roles).
14. Phase 5 Billing (credits ledger + metering + Stripe).
15. Phase 6 Creators (profiles + Connect + royalties).
16. Phase 7 Marketplace (listings + discovery + royalty-on-use).
17. Phase 8 Cloud Infra (Postgres + Alembic + worker pool + CDN + observability).
18. Phase 10 Production Scaling.

> Cloud phases are no longer blocked by the provider-validation gate, but
> investment in them before Runtime-Service Phase 2 lands would re-couple backend
> to model execution. **Phase 2 first, then deliberate Cloud sequencing.**

---

**Related:** [`ROADMAP.md`](../ARCHIVE/LEGACY/ROADMAP.md) · [`MILESTONES.md`](MILESTONES.md) ·
[`../OPEN_DECISIONS.md`](../OPEN_DECISIONS.md) ·
[`../SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/) ·
[`../SPECS/FEATURES/runtime-services-implementation/`](../SPECS/FEATURES/runtime-services-implementation/)
