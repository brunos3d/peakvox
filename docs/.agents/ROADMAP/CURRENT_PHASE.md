# Current Phase

**As of:** 2026-06-07 · **Branch:** `feat/peakvox-phase-1`

## Phase: CE spine complete → Runtime-Service architecture

Phases 1–3 (including sub-phases 3.5–3.11) are **built and tested**. Kokoro provider
validation passed (G5 — real audio E2E through the Runtime, see
`docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-validation-report.md`).
The platform is a **multi-provider Universal Voice Runtime with a
substrate-implicit deployment model**.

The new direction ([ADR-0016](../DECISIONS/adr-0016-models-as-runtime-services.md),
accepted 2026-06-07) replaces the substrate-implicit model with an explicit
**Runtime-Service architecture**: Runtime Registry + Runtime Manager + Runtime
Driver + Runtime Service. 7-phase migration; Phase 1 (this) is documentation
only.

### Done in this phase

- Platform foundations (flags, vendor seams, schema-ready commercial tables).
- Model registry + canonical metadata + capability contract.
- Voice/Variant split, Runtime exclusivity, ModelAdapter contract, build lifecycle, artifact
  versioning, edition scoping.
- Voice Library 2.0 UI, Variant Dashboard, variant backfill UX.
- Kokoro provider validation (G5 passed — real audio E2E through the Runtime).
- Runtime-Service architecture (Phase 1, ADR + design docs).

### In progress

- **Runtime-Service migration — Phase 2 Sub-phase 2D (CE operations
  + `runtime-registry/` with Kokoro descriptor + bridge activation).**
  TDD tasks in
  [`../SPECS/FEATURES/runtime-services-implementation/TASKS.md`](../SPECS/FEATURES/runtime-services-implementation/TASKS.md) §2D.

> ## ⚠ PHASE 2 IMPLEMENTATION GUARDRAIL — RESOLVED FOR SUB-PHASES 2A, 2B AND 2C
>
> **Sub-phases 2A, 2B AND 2C are COMPLETE (2026-06-07).** Phase 2
> implementation may continue; the next sub-phase is 2D
> (CE operations + `runtime-registry/` + bridge activation —
> the LAST sub-phase of Phase 2).
>
> **Current state (2026-06-07):**
> - ADR-0016 (architecture): **Accepted+Implemented (Phase 1+2A+2B+2C)**
>   (2026-06-07).
> - ADR-0017 (Phase 2 implementation architecture):
>   **Accepted+Implemented (2A+2B+2C)** (2026-06-07). Architecture
>   review: 0 blocking issues; non-blocking suggestions applied
>   (Runtime Persistence → `OPEN_DECISIONS.md` Decision 12).
> - Sub-phase 2A (Foundations): **✅ Complete.** 9 new modules +
>   9 test files; 76 new tests; 401/401 pre-existing tests pass;
>   no Docker integration, no Runtime Service communication, no
>   model framework imports, no HTTP clients. `PeakVoxRuntime`
>   bridge is a transitional pass-through; behavior unchanged in
>   2A. See
>   [`../IMPLEMENTATION_STATUS.md` §"Phase 2A — Runtime Services
>   Foundations"](../IMPLEMENTATION_STATUS.md).
> - Sub-phase 2B (First Concrete Driver): **✅ Complete.** 1
>   new module (`docker_runtime_driver.py`) + 1 new script
>   (`lint_no_docker_outside_driver.py`) + 2 modified modules +
>   2 new test files; 40 new tests; 441/441 pre-existing tests
>   pass. Docker imports confined to the driver package
>   (enforced by the lint script, exit 0 on the real tree).
>   The `RuntimeManager.resolve()` is updated to return a non-None
>   `RuntimeResolution` when a driver is wired; the 2A bridge
>   in `runtime.py` is unchanged (the runtime-service branch is
>   still a literal `pass`; activation is in 2C).
> - Sub-phase 2C (`HTTPTransport` + KokoroAdapter migration):
>   **✅ Complete.** 1 new transport module (`HTTPTransport`)
>   + 1 modified adapter (`KokoroAdapter` dispatches on
>   `KOKORO_RUNTIME_URL`) + 1 modified settings
>   (`Settings.KOKORO_RUNTIME_URL`) + 3 new test files (14
>   transport + 8 adapter isolation + 3 settings) + 1 E2E
>   scaffold (gated, skipped in default venv). 25 new tests,
>   1 skipped; 466/466 pre-existing tests pass. Transport
>   Boundary Audit: PASSED. The 2A bridge in `runtime.py` is
>   unchanged (the runtime-service branch is still a literal
>   `pass`; activation is in 2D).
> - Sub-phase 2D (CE operations + `runtime-registry/` + bridge
>   activation): **ready to start**. TDD tasks in
>   [`../SPECS/FEATURES/runtime-services-implementation/TASKS.md`](../SPECS/FEATURES/runtime-services-implementation/TASKS.md) §2D.
>
> Sub-phases 2A ✅ 2B ✅ 2C ✅ done. Sub-phase 2D may begin. TDD-shaped
> tasks for 2D (in `TASKS.md` §2D):
>
> | # | Component | File | Test |
> |---|---|---|---|
> | 2D.1 | `runtime-registry/` with Kokoro descriptor | `backend/app/services/runtime_registry/kokoro.json` (or `.yaml` if pyyaml is installed) | `tests/test_runtime_registry_loader_kokoro.py` |
> | 2D.2 | CE operations (install/activate/update/remove) | `backend/app/services/runtime_operations.py` (or wherever the operations live) | `tests/test_runtime_operations.py` |
> | 2D.3 | Bridge activation in `runtime.py` | `backend/app/services/runtime.py` (replace the 2A.10 `pass` block) | `tests/test_runtime_routing_phase2d.py` |
> | 2D.4 | Provider-validated report (Kokoro G6: runtime-service E2E) | `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-runtime-validation-report.md` | gated E2E test passes against a real `peakvox/kokoro-runtime` container |
> | 2D.5 | Update `IMPLEMENTATION_STATUS.md` + state files | `docs/.agents/` | cross-link + status update |

### The gate before Cloud work

Cloud phases (4–10) are no longer blocked by the provider-validation gate (Kokoro
G5 passed). However, investing in Cloud before Runtime-Service Phase 2 lands
would re-couple backend to model execution. **Phase 2 first; deliberate Cloud
sequencing afterward.**

### Candidate parallel phases

- **Phase 9 — Public API harden** — can proceed in parallel with Phase 2.
- **Runtime-Service migration Phases 3–7** — sequenced behind Phase 2.

---

**Related:** [`ROADMAP.md`](../ARCHIVE/LEGACY/ROADMAP.md) · [`../NEXT_TASK.md`](../NEXT_TASK.md) ·
[`../VALIDATION/RETROSPECTIVES/`](../VALIDATION/RETROSPECTIVES/) ·
[`../SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/) ·
[`../DECISIONS/adr-0016-models-as-runtime-services.md`](../DECISIONS/adr-0016-models-as-runtime-services.md)
