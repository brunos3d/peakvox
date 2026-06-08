# NEXT TASK

> Exactly one highest-priority task — the execution queue head. When this task is done, move
> it to the execution ledger and promote the next item from [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

**As of:** 2026-06-07

> ## ⚠ PHASE 2 GUARDRAIL — RESOLVED FOR SUB-PHASES 2A, 2B AND 2C
>
> **Sub-phases 2A, 2B AND 2C of the Runtime-Service migration
> are COMPLETE (2026-06-07).** ADR-0016 + ADR-0017 are
> Accepted+Implemented (2A+2B+2C). 2A delivered 9 modules + 9
> test files (76 new tests). 2B delivered 1 module + 1 lint
> script + 2 modified modules + 2 test files (40 new tests).
> 2C delivered 1 transport module + 1 settings field + 1
> adapter integration + 1 E2E scaffold (25 new tests, 1
> skipped). The previous guardrail ("may not begin until
> ADR-0017 is Accepted") is satisfied for all three sub-phases.
>
> **Sub-phase 2D is the next active work item.** 2D is the
> last sub-phase of Phase 2; it lands the CE operations
> (install/activate/update/remove) + the `runtime-registry/`
> directory with the Kokoro descriptor + the activation of the
> 2A bridge's runtime-service branch in `runtime.py`. After
> 2D, Phase 2 is complete and Phase 3 (Kokoro full migration)
> is unblocked.

## Task: Phase 2 Sub-phase 2D — CE operations + runtime-registry + bridge activation

- **Priority:** P0. Phase 2 implementation is in flight; 2A,
  2B, 2C are complete; 2D is the last sub-phase of Phase 2.
- **Status:** **Ready to start.** Sub-phases 2A+2B+2C are
  complete (2026-06-07). The `HTTPTransport` is wired; the
  `KokoroAdapter` dispatches on `KOKORO_RUNTIME_URL`; the
  2A bridge in `runtime.py` is the activation point. 2D
  introduces the CE operations (install/activate/update/
  remove) for the runtime services, the `runtime-registry/`
  directory with the Kokoro descriptor, and activates the
  2A bridge's runtime-service branch.
- **Architecture review guardrail (still in force):**
  - DockerRuntimeDriver is the only component allowed to import
    Docker libraries — preserved by the lint script.
  - RuntimeManager must not gain Docker knowledge — preserved;
    the manager's `resolve()` reads the descriptor's service
    config and does not import any substrate library.
  - RuntimeManager must continue to communicate exclusively
    through RuntimeDriver — preserved.
  - RuntimeRegistry must remain declarative — preserved.
  - **No adapter may communicate directly with Docker** —
    preserved in 2D; the adapter communicates with the
    Runtime Service via `HTTPTransport`, not with Docker.
  - **No runtime service may bypass Adapter → RuntimeManager
    → RuntimeDriver** — the 2D bridge activation in
    `runtime.py` is exactly this chain: PeakVoxRuntime →
    RuntimeManager.resolve → endpoint → adapter.translate_
    generate → HTTP POST to the endpoint. The driver is the
    substrate; the runtime service is the engine; the adapter
    is the protocol translator.
  - **No bridge activation without CE operations in place** —
    the 2D bridge activation in `runtime.py` must not begin
    until the CE operations (install/activate/update/remove)
    are wired and the `runtime-registry/` with Kokoro
    descriptor is in place. The 2A bridge's `if _resolution
    is not None: pass` placeholder becomes a live
    runtime-service branch ONLY when the resolution is
    non-None AND the runtime is activated AND the resolution's
    `endpoint` is reachable.
- **Sub-phase 2D plan** (TDD per task, from
  [`SPECS/FEATURES/runtime-services-implementation/TASKS.md`](SPECS/FEATURES/runtime-services-implementation/TASKS.md) §2D):

  | Task | Component | File | Test |
  |---|---|---|---|
  | 2D.1 | `runtime-registry/` directory with the Kokoro descriptor | `backend/app/services/runtime_registry/kokoro.json` (or `.yaml` if pyyaml is installed) | `tests/test_runtime_registry_loader_kokoro.py` — descriptor file exists, parses, validates against `RuntimeDescriptor` schema; CE default + Cloud variant |
  | 2D.2 | CE operations (install/activate/update/remove) | `backend/app/services/runtime_operations.py` (or wherever the operations live) | `tests/test_runtime_operations.py` — install pulls the image; activate calls `driver.start()`; update pulls the new digest; remove calls `driver.remove()`; idempotent install/remove; `RuntimeNotFound` on missing; `RuntimeAlreadyExists` on duplicate install |
  | 2D.3 | Bridge activation in `runtime.py` | `backend/app/services/runtime.py` (replace the 2A.10 `pass` block) | `tests/test_runtime_routing_phase2d.py` — when resolution is non-None AND the runtime is activated, the adapter routes via `HTTPTransport` to `resolution.endpoint`; when resolution is None, the in-process path is taken (2A behavior preserved); when resolution is non-None AND the runtime is NOT activated, the bridge falls through to the in-process path with a warning log |
  | 2D.4 | Provider-validated report (Kokoro G6: runtime-service E2E) | `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-runtime-validation-report.md` | gated E2E test passes against a real `peakvox/kokoro-runtime` container |
  | 2D.5 | Update `IMPLEMENTATION_STATUS.md` + state files | `docs/.agents/` | cross-link + status update (2D row IMPLEMENTED; ADR-0016 + ADR-0017 rows flip to "IMPLEMENTED (Phase 2 complete)") |

- **Definition of done — Sub-phase 2D:**
  - The `runtime-registry/` directory contains the Kokoro
    descriptor; the `RuntimeRegistryLoader` picks it up at
    app startup; the descriptor validates against the
    `RuntimeDescriptor` schema.
  - CE operations work end-to-end against the
    `DockerRuntimeDriver`: install pulls the image; activate
    starts the container; update pulls the new digest;
    remove stops and removes the container.
  - The 2A bridge in `runtime.py` activates the runtime-service
    branch when (a) the manager is wired, (b) the resolution
    is non-None, AND (c) the runtime is activated. The
    in-process path is preserved as a fallback when the
    runtime is not activated.
  - A provider-validated report exists for the runtime path
    (gated, not in default CI).
  - Phase 2 is complete: 2A + 2B + 2C + 2D all IMPLEMENTED.
    Phase 3 (Kokoro full migration) is unblocked.
  - The Kokoro migration is **additive**; the in-process path
    is not removed (Phase 7 will remove it).

- **Phase 3** (sequenced behind 2D, not in flight):
  - **Phase 3** — Kokoro full migration. The Kokoro provider
    becomes the FIRST provider that runs ONLY through the
    runtime service in CE (in-process path is still
    available as a fallback, but the default CE deployment
    uses the runtime service). The Kokoro descriptor's
    `image.digest` pins the runtime service to a specific
    image version. The Kokoro adapter is updated to
    communicate with the runtime service by default (the
    `KOKORO_RUNTIME_URL` env var becomes the canonical
    configuration point).

- **Provider-validation status (unchanged):** Kokoro G5 ✅. Fish
  Audio S2 Pro still blocked on hardware. OmniVoice Base E2E
  audio test would be nice; no GPU in CI.
- **Cloud readiness gate:** still OPEN. 2A → 2B → 2C → 2D
  unblocks both CE hardening and Cloud architecture planning
  (the `KubernetesRuntimeDriver` lands as Decision 11's
  separate ADR).
- **Next:** begin sub-phase 2D with strict TDD.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md) ·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/`](SPECS/FEATURES/runtime-services-implementation/) ·
[`docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md`](DECISIONS/adr-0017-runtime-services-implementation.md) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md)
