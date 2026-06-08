# NEXT TASK

> Exactly one highest-priority task — the execution queue head. When this task is done, move
> it to the execution ledger and promote the next item from [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

**As of:** 2026-06-07

> ## ⚠ PHASE 2 GUARDRAIL — RESOLVED (PHASE 2 COMPLETE)
>
> **Sub-phases 2A, 2B, 2C, AND 2D of the Runtime-Service
> migration are COMPLETE (2026-06-07).** ADR-0016 + ADR-0017
> are Accepted+Implemented (2A+2B+2C+2D). **Phase 2 is
> COMPLETE.** The Runtime Activation Audit (all 7 checks
> PASS) confirms the canonical chain (Voice → VoiceVariant →
> Active Artifact → Adapter) is intact and runtime
> infrastructure is strictly downstream.
>
> **Phase 3 is the next active workstream.** Phase 3 is
> the Kokoro full migration: the Kokoro provider becomes the
> FIRST provider that runs ONLY through the runtime service
> in CE (in-process path is still available as a fallback,
> but the default CE deployment uses the runtime service).
> The Kokoro descriptor's `image.digest` pins the runtime
> service to a specific image version. The Kokoro adapter is
> updated to communicate with the runtime service by default
> (the `KOKORO_RUNTIME_URL` env var becomes the canonical
> configuration point).

## Task: Phase 3 — Kokoro full migration

- **Priority:** P0. Phase 2 is complete; Phase 3 is the
  next sub-phase of the Runtime-Service migration.
- **Status:** **Ready to start.** Sub-phases 2A+2B+2C+2D
  are complete (2026-06-07). The `runtime-registry/` is
  published with the Kokoro descriptor; the CE operations
  are wired; the 2A bridge is ACTIVATED; the CLI skeleton
  is in place. Phase 3 makes the runtime-service path the
  DEFAULT for Kokoro in CE.
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
    → RuntimeDriver** — preserved in Phase 3; the in-process
    path is the fallback when `KOKORO_RUNTIME_URL` is unset.
  - **The canonical chain (Voice → VoiceVariant → Active
    Artifact → Adapter) must remain intact** — Phase 3 does
    not change variant resolution, artifact resolution, or
    voice compatibility derivation. The runtime-service
    path is purely a transport change.
- **Phase 3 plan** (TDD per task, from
  [`SPECS/FEATURES/runtime-services-implementation/TASKS.md`](SPECS/FEATURES/runtime-services-implementation/TASKS.md) §3):

  | Task | Component | File | Test |
  |---|---|---|---|
  | 3.1 | Wire the E2E test (`tests/test_kokoro_e2e_runtime.py`) into the docker-compose CI lane | `docker-compose.yml` (gated) | E2E test passes against a real `peakvox/kokoro-runtime` container; real audio generated |
  | 3.2 | G7 (Performance) validation report | `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-g7-performance-report.md` | RTF, VRAM, load time measured |
  | 3.3 | G8 (Error recovery) validation report | `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-g8-error-recovery-report.md` | Crashed container recovery; network partition recovery |
  | 3.4 | Update `IMPLEMENTATION_STATUS.md` + state files | `docs/.agents/` | cross-link + status update (Phase 3 row IMPLEMENTED) |

- **Definition of done — Phase 3:**
  - Real audio generated E2E through the runtime service
    (the gated E2E test passes in the docker-compose CI
    lane).
  - G7 (Performance) and G8 (Error recovery) validation
    reports exist.
  - The Kokoro provider runs ONLY through the runtime
    service in CE (in-process path is still available as
    a fallback, but the default CE deployment uses the
    runtime service).
  - The Kokoro descriptor's `image.digest` pins the
    runtime service to a specific image version.

- **Phase 4** (sequenced behind Phase 3, not in flight):
  - **Phase 4** — F5-TTS reference. The F5-TTS adapter
    becomes the SECOND provider that runs through the
    runtime service.

- **Provider-validation status (unchanged):** Kokoro G5
  (in-process) ✅. Kokoro G6 (runtime-service) ✅
  (architecturally; E2E gated). Fish Audio S2 Pro still
  blocked on hardware. OmniVoice Base E2E audio test would
  be nice; no GPU in CI.
- **Cloud readiness gate:** still OPEN. 2A → 2B → 2C → 2D
  unblocks both CE hardening and Cloud architecture
  planning (the `KubernetesRuntimeDriver` lands as
  Decision 11's separate ADR).
- **Next:** begin Phase 3 with strict TDD.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md) ·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/`](SPECS/FEATURES/runtime-services-implementation/) ·
[`docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md`](DECISIONS/adr-0017-runtime-services-implementation.md) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md)
