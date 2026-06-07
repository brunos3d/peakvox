# Backlog

> Groomed list of future work not yet active. Active work lives in [`../ACTIVE_WORK.md`](../ACTIVE_WORK.md);
> the single next item in [`../NEXT_TASK.md`](../NEXT_TASK.md). Ordered by priority.

**As of:** 2026-06-07

## P0 — Gating

1. ~~**Stabilize + commit the in-flight working tree.**~~ ✅ Complete (commit landed).
2. ~~**First foreign-provider validation.**~~ ✅ **Kokoro G5 passed** (real audio generated
   E2E through the Runtime). Cloud readiness gate is **OPEN**.
3. **Runtime-Service migration — Phase 2** (Runtime Manager skeleton + `DockerRuntimeDriver`).
   See [ADR-0016](../DECISIONS/adr-0016-models-as-runtime-services.md) and
   [`../SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/).
   Phase 1 (ADR + design) is complete; Phase 2 implementation is gated on a Phase 2
   implementation ADR (deferred open questions: runtime endpoint discovery, GPU
   allocation, runtime health contract, backend-to-runtime auth).
4. **Runtime-Service migration — Phases 3–7** (Kokoro, F5-TTS, Fish, OmniVoice migrations,
   in-process path removal). Sequenced behind Phase 2.

## P1 — CE hardening (can proceed in parallel with Phase 2)

5. **Phase 9 — Public API harden:** freeze `/v1`, consistent error model (402/409/410/422),
   `pv_` key transition, publish OpenAPI, ship SDK, deprecation policy.
6. **OmniVoice end-to-end audio test** (gated/optional CI lane with weights) to move OmniVoice
   from PARTIAL to VALIDATED on the provider axis.
7. **Fish S2 Pro server deployment** (subject to existing hardware blocker — 24GB+ VRAM
   required; see
   [`../VALIDATION/PROVIDER_VALIDATIONS/`](../VALIDATION/PROVIDER_VALIDATIONS/)).
8. **Kokoro G7 (performance) and G8 (error recovery)** measurement — low priority.

## P2 — Provisioning decisions (write the reserved ADRs when decided)

9. ADR-0012 Variant Provisioning Policies (per Creation Source).
10. ADR-0013 Model Categories (cloning vs preset vs training).
11. **Phase 2 implementation ADR** for the Runtime-Service migration (deferred open
    questions from ADR-0016; see
    [`../OPEN_DECISIONS.md`](../OPEN_DECISIONS.md) Decision 10).
12. **Future driver ADRs:** `KubernetesRuntimeDriver` (Cloud), `PodmanRuntimeDriver`,
    `LocalProcessDriver` (one ADR per driver when its edition begins; see
    [`../OPEN_DECISIONS.md`](../OPEN_DECISIONS.md) Decision 11).

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
[`../SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/)
