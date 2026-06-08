# NEXT TASK

> Exactly one highest-priority task — the execution queue head. When this task is done, move
> it to the execution ledger and promote the next item from [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

**As of:** 2026-06-07

> ## ⚠ PHASE 2 GUARDRAIL — RESOLVED FOR SUB-PHASES 2A AND 2B
>
> **Sub-phase 2B of the Runtime-Service migration is COMPLETE
> (2026-06-07).** ADR-0016 + ADR-0017 are Accepted. 2A delivered 9
> modules + 9 test files (76 new tests). 2B delivered 1 module +
> 1 lint script + 2 modified modules + 2 test files (40 new
> tests, 0 regressions). The previous guardrail ("may not begin
> until ADR-0017 is Accepted") is satisfied for both sub-phases.
>
> **Sub-phase 2C is the next active work item.** 2C is the first
> sub-phase that introduces the **runtime-service communication
> path**: `HTTPTransport` for adapters + the `KokoroAdapter`
> `KOKORO_RUNTIME_URL` path (additive; in-process fallback
> preserved). The 2A bridge's `if _resolution is not None: pass`
> placeholder becomes the live runtime-service branch in 2C.

## Task: Phase 2 Sub-phase 2C — HTTPTransport + KokoroAdapter KOKORO_RUNTIME_URL path

- **Priority:** P0. Phase 2 implementation is in flight; 2A and
  2B are complete; 2C is the next sub-phase.
- **Status:** **Ready to start.** Sub-phases 2A and 2B are
  complete (2026-06-07). The `DockerRuntimeDriver` is wired;
  the `RuntimeManager.resolve()` returns a non-None resolution
  when a driver is wired; the bridge in `runtime.py` is the
  activation point. 2C introduces the HTTP transport and
  activates the runtime-service branch in the bridge.
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
    preserved in 2C; the adapter communicates with the Runtime
    Service via the Runtime Service Contract (HTTP/JSON), not
    with Docker.
  - **No runtime service may bypass Adapter → RuntimeManager
    → RuntimeDriver** — the 2C+ bridge in `runtime.py` is
    exactly this chain: PeakVoxRuntime → RuntimeManager.resolve
    → endpoint → adapter.translate_generate → HTTP POST to the
    endpoint. The driver is the substrate; the runtime service
    is the engine; the adapter is the protocol translator.
- **Sub-phase 2C plan** (TDD per task, from
  [`SPECS/FEATURES/runtime-services-implementation/TASKS.md`](SPECS/FEATURES/runtime-services-implementation/TASKS.md) §2C):

  | Task | Component | File | Test |
  |---|---|---|---|
  | 2C.1 | `HTTPTransport` (generic adapter HTTP client) | `backend/app/services/adapter_transport/http_transport.py` | `tests/test_http_transport.py` — retry policy, timeouts, streaming, error mapping |
  | 2C.2 | Wire `KokoroAdapter` to use `HTTPTransport` when `KOKORO_RUNTIME_URL` is set | `backend/app/services/model_adapters/kokoro_adapter.py` | `tests/test_kokoro_runtime_adapter.py` — in-process fallback (env unset) and runtime path (env set) |
  | 2C.3 | `KOKORO_RUNTIME_URL` plumbing in config | `backend/app/core/config.py` (or wherever settings live) | defaults to empty string (= in-process) |
  | 2C.4 | End-to-end test: peakvox backend + `peakvox/kokoro-runtime` container, generating audio through the runtime service | integration; gated | `tests/test_kokoro_e2e_runtime.py` (integration, gated, not in default CI lane) |
  | 2C.5 | Update `IMPLEMENTATION_STATUS.md`; provider validation report at `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-runtime-validation-report.md` | `docs/.agents/` | cross-link + status update |

- **Definition of done — Sub-phase 2C:**
  - `KokoroAdapter` works both in-process and through the
    runtime service.
  - The in-process path is the default; the runtime path is
    opt-in via `KOKORO_RUNTIME_URL`.
  - A provider-validated report exists for the runtime path
    (gated, not in default CI).
  - The Kokoro migration is **additive**; the in-process path
    is not removed (Phase 7 will remove it).
  - The 2A bridge's `pass` placeholder becomes the live
    runtime-service branch: PeakVoxRuntime calls
    `RuntimeManager.resolve(model_id)`; if the resolution is
    non-None, the adapter translates the request to the
    Runtime Service Contract and POSTs to `resolution.endpoint`.

- **Sub-phase 2D** (sequenced behind 2C, not in flight):
  - **2D** — CE operations (install/activate/update/remove) +
    `runtime-registry/` with Kokoro descriptor.

- **Provider-validation status (unchanged):** Kokoro G5 ✅. Fish
  Audio S2 Pro still blocked on hardware. OmniVoice Base E2E
  audio test would be nice; no GPU in CI.
- **Cloud readiness gate:** still OPEN. 2A → 2B → 2C unblocks
  both CE hardening and Cloud architecture planning (the
  `KubernetesRuntimeDriver` lands as Decision 11's separate ADR).
- **Next:** begin sub-phase 2C with strict TDD.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md) ·
[`docs/.agents/SPECS/FEATURES/runtime-services-implementation/`](SPECS/FEATURES/runtime-services-implementation/) ·
[`docs/.agents/DECISIONS/adr-0017-runtime-services-implementation.md`](DECISIONS/adr-0017-runtime-services-implementation.md) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md)
