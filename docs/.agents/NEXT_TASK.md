# NEXT TASK

> Exactly one highest-priority task — the execution queue head. When this task is done, move
> it to the execution ledger and promote the next item from [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

**As of:** 2026-06-08

> ## Phase 3 — IN PROGRESS (Kokoro full migration + Runtime Service Container)
>
> **Sub-phases 2A, 2B, 2C, AND 2D of the Runtime-Service
> migration are COMPLETE (2026-06-07).** ADR-0016 + ADR-0017
> are Accepted+Implemented+Refined (2A+2B+2C+2D + 8 post-audit
> refinements R1–R8). **Phase 2 is COMPLETE.** The Runtime
> Activation Audit (all 7 checks PASS) confirms the canonical
> chain is intact and runtime infrastructure is strictly
> downstream.
>
> **Phase 3 is in flight.** The Runtime Service Readiness
> Audit identified the missing concrete runtime service.
> Eight refinements (R1–R8) were applied to the spec/design
> before implementation:
>
>   R1 — Self-contained registry entries
>   R2 — `spec.build` block (CE-only build metadata)
>   R3 — `RUNTIME_SERVICE_ENABLED` settings flag
>   R4 — Runtime-first lifecycle
>   R5 — Phase 3 DoD (backend without Kokoro)
>   R6 — Lazy startup (no runtimes at boot)
>   R7 — Idle timeout (CE 15m, Cloud never)
>   R8 — Reference implementation pattern (kokoro-82m canonical)
>
> `runtime-registry/kokoro-82m/` is now self-contained and is
> the canonical reference shape for every future runtime
> (F5-TTS, XTTS, OpenVoice, Fish, OmniVoice). The backend
> wires the runtime subsystem at startup (gated on
> `RUNTIME_SERVICE_ENABLED`). The Models page delegates
> install/activate/deactivate/update/remove to the
> `RuntimeManager`. The R5 DoD is proven at the import-graph
> level: `kokoro` is no longer a hard backend dependency.

## Task: Phase 3 — Runtime-Canonical Models Page + Runtime Registry Expansion

- **Priority:** P0. Phase 2 is complete; Phase 3 is the
  next sub-phase of the Runtime-Service migration.

> ## Phase 3 — IN PROGRESS (Runtime-Canonical Models Page + Runtime Registry expansion)
>
> **Sub-phases 2A, 2B, 2C, AND 2D of the Runtime-Service
> migration are COMPLETE (2026-06-07).** ADR-0016 + ADR-0017
> are Accepted+Implemented+Refined (2A+2B+2C+2D + 8 post-audit
> refinements R1–R8). **Phase 2 is COMPLETE.**
>
> **Phase 3 is in flight.** Two workstreams in sequence:
>
>   **Workstream A — Models Page / Runtime Registry
>   convergence.** ✅ **IMPLEMENTED 2026-06-08.** The Models
>   page is now a strict 3-tier composed view with a
>   single canonical lifecycle control surface owned by the
>   Runtime Section. The legacy `Lifecycle` block (model
>   Activate/Deactivate) is removed. The page depends
>   solely on `useModelsWithRuntimes()`. Extracted
>   components: `RuntimeSection`, `ModelSection`,
>   `OperationsRow`, `NotMigratedEmptyState`, `ModelRow`.
>   See
>   [`docs/.agents/SPECS/FEATURES/runtime-canonical-models-page/audits/models-page-canonical-control-surface.md`](SPECS/FEATURES/runtime-canonical-models-page/audits/models-page-canonical-control-surface.md).
>
>   **Workstream B — TASK 12: Runtime Registry
>   expansion.** Next P0. Goal: prove the Runtime Registry
>   can host multiple independent runtime implementations
>   under the same architecture. First two additional
>   entries: `omnivoice-base`, `f5-tts-base`. End-to-end
>   validation: descriptor discovery, Models-page rendering
>   of all 3 runtimes, container lifecycle (Install /
>   Start / Stop / Update / Remove) for each runtime, real
>   audio E2E generation. See
>   [`docs/.agents/SPECS/FEATURES/runtime-canonical-models-page/TASKS.md`](SPECS/FEATURES/runtime-canonical-models-page/TASKS.md) §12.
- **Status:** **P1–P9 done; P7 (G7+G8) deferred. Task 19 (compatibility) VALIDATED 2026-06-09.**
  - P1 ✅ peakvox/kokoro-runtime: self-contained
  - P2 ✅ RuntimeRegistry + RuntimeManager wired at startup
  - P3 ✅ Idle reaper background task
  - P4 ✅ Models page delegates to RuntimeManager
  - P5 ✅ docker-compose: runtime removed (user-installed, not platform infra)
  - P6 ✅ Real E2E generation through runtime service (browser-validated 2026-06-09)
  - P7 🟡 Provider validation G6 + G9 + G10 reports written; G7 + G8 to follow
  - P8 ✅ Backend without Kokoro (R5 DoD test)
  - P9 🟡 State file updates (this file)
- **Architecture review guardrail (still in force):**
  - DockerRuntimeDriver is the only component allowed to
    import Docker libraries — preserved by the lint script.
  - RuntimeManager must not gain Docker knowledge —
    preserved; the manager's `resolve()` reads the
    descriptor's service config and does not import any
    substrate library.
  - RuntimeManager must continue to communicate
    exclusively through RuntimeDriver — preserved.
  - RuntimeRegistry must remain declarative — preserved.
  - **No adapter may communicate directly with Docker** —
    preserved; the adapter communicates with the Runtime
    Service via `HTTPTransport`, not with Docker.
  - **No runtime service may bypass Adapter → RuntimeManager
    → RuntimeDriver** — preserved; `KOKORO_RUNTIME_URL` and
    all other hardcoded runtime URLs have been removed. Endpoint
    injection is exclusively via `RuntimeManager.resolve()` →
    `RuntimeResolution.endpoint` → `runtime_endpoint` kwarg.
    The legacy in-process kokoro path remains only as a fallback
    when `runtime_endpoint is None` (no manager wired).
  - **The canonical chain (Voice → VoiceVariant → Active
    Artifact → Adapter) must remain intact** — Phase 3
    does not change variant resolution, artifact
    resolution, or voice compatibility derivation.
- **Phase 3 plan** (TDD per task; P1–P5 + P8 complete):

  | Task | Component | Status |
  |---|---|---|
  | P1 | `peakvox/kokoro-runtime` self-contained entry | ✅ |
  | P2 | Wire `RuntimeRegistry` + `RuntimeManager` at startup | ✅ |
  | P3 | Wire idle reaper (R7) | ✅ |
  | P4 | Connect Models page to `RuntimeManager` (R4) | ✅ |
  | P5 | Remove `peakvox-kokoro-runtime` from `docker-compose.yml` (user-installed, not platform infra) | ✅ |
  | P6 | Real E2E generation through runtime service | ✅ (browser-validated 2026-06-09) |
  | P7 | G6 (contract) + G9 (reaper) + G10 (no-Kokoro) reports | ✅ (3/5) |
  | P7 | G7 (performance) + G8 (error recovery) reports | 🟡 (deferred) |
  | P8 | Backend without Kokoro (R5 DoD) | ✅ |
  | P9 | State file updates | 🟡 (in progress) |

- **Definition of done — Phase 3:**
  - `peakvox/kokoro-runtime:0.1.0` image builds and serves
    the 5-endpoint contract (✅ G6 architecture-validated).
  - `RUNTIME_SERVICE_ENABLED=true` wires the runtime
    subsystem at backend startup (✅ P2 architecture-validated).
  - The Models page Install/Activate/Deactivate/Update/Remove
    delegate to `RuntimeManager` (✅ P4 architecture-validated).
  - The R5 DoD is proven at the import-graph level (✅ P8).
  - G6 + G9 + G10 provider-validation reports exist.
  - G7 (Performance) and G8 (Error recovery) provider-
    validation reports exist (🟡 deferred; test surface
    in place; measurements require real Docker host).
  - **Phase 4** is unblocked: F5-TTS as a runtime service
    mirrors the Kokoro reference shape (R8).

- **Phase 4** (sequenced behind Phase 3, not in flight):
  - **Phase 4** — F5-TTS reference. The F5-TTS adapter
    becomes the SECOND provider that runs through the
    runtime service.

- **Provider-validation status:**
  - Kokoro G5 (in-process) ✅ (2026-06-05)
  - Kokoro G6 (runtime-service contract) ✅
    (architecture-validated; CI-gated E2E in docker-compose)
  - Kokoro G9 (idle reaper) ✅ (architecture-validated)
  - Kokoro G10 (backend without Kokoro, R5 DoD) ✅
    (architecture-validated; CI-gated docker build)
  - Kokoro G7 (Performance) 🟡 (deferred to a future phase)
  - Kokoro G8 (Error recovery) 🟡 (deferred to a future phase)
  - Fish Audio S2 Pro still blocked on hardware.
  - OmniVoice Base E2E audio test would be nice; no GPU in CI.

- **Cloud readiness gate:** OPEN. 2A → 2B → 2C → 2D
  unblocks both CE hardening and Cloud architecture
  planning (the `KubernetesRuntimeDriver` lands as
  Decision 11's separate ADR).
- **Next:** complete P7 (G7 + G8 reports) and P9 (state
  file updates); then close Phase 3 and unblock Phase 4.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md) ·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/`](SPECS/FEATURES/runtime-services-implementation/) ·
[`docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md`](DECISIONS/adr-0017-runtime-services-implementation.md) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md) ·
[`runtime-registry/kokoro-82m/`](../../runtime-registry/kokoro-82m/) (R8 reference shape) ·
[`AUDITS/runtime-service-readiness-audit.md`](VALIDATION/AUDITS/runtime-service-readiness-audit.md)
