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

- **Runtime-Service migration — Phase 3 (Kokoro full migration).**
  TDD tasks in
  [`../SPECS/FEATURES/runtime-services-implementation/TASKS.md`](../SPECS/FEATURES/runtime-services-implementation/TASKS.md) §3.

> ## ⚠ PHASE 2 IMPLEMENTATION GUARDRAIL — RESOLVED (PHASE 2 COMPLETE)
>
> **Sub-phases 2A, 2B, 2C, AND 2D are COMPLETE (2026-06-07).
> Phase 2 is COMPLETE.** Phase 3 (Kokoro full migration)
> is the next P0 workstream.
>
> **Current state (2026-06-07):**
> - ADR-0016 (architecture): **Accepted+Implemented (Phase 1+2A+2B+2C+2D)**
>   (2026-06-07).
> - ADR-0017 (Phase 2 implementation architecture):
>   **Accepted+Implemented (2A+2B+2C+2D)** (2026-06-07). Architecture
>   review: 0 blocking issues; non-blocking suggestions applied
>   (Runtime Persistence → `OPEN_DECISIONS.md` Decision 12).
> - **Runtime Activation Audit (all 7 checks PASS).** Canonical chain
>   (Voice → VoiceVariant → Active Artifact → Adapter) is intact.
>   Runtime infrastructure is strictly downstream.
> - Sub-phase 2A (Foundations): **✅ Complete.** 9 new modules +
>   9 test files; 76 new tests; 401/401 pre-existing tests pass;
>   no Docker integration, no Runtime Service communication, no
>   model framework imports, no HTTP clients. `PeakVoxRuntime`
>   bridge is a transitional pass-through; behavior unchanged in
>   2A.
> - Sub-phase 2B (First Concrete Driver): **✅ Complete.** 1
>   new module (`docker_runtime_driver.py`) + 1 new script
>   (`lint_no_docker_outside_driver.py`) + 2 modified modules +
>   2 new test files; 40 new tests; 441/441 pre-existing tests
>   pass. Docker imports confined to the driver package
>   (enforced by the lint script, exit 0 on the real tree).
> - Sub-phase 2C (`HTTPTransport` + KokoroAdapter migration):
>   **✅ Complete.** 1 new transport module (`HTTPTransport`)
>   + 1 modified adapter (`KokoroAdapter` dispatches on
>   `KOKORO_RUNTIME_URL`) + 1 modified settings
>   (`Settings.KOKORO_RUNTIME_URL`) + 3 new test files (14
>   transport + 8 adapter isolation + 3 settings) + 1 E2E
>   scaffold (gated, skipped in default venv). 25 new tests,
>   1 skipped; 466/466 pre-existing tests pass. Transport
>   Boundary Audit: PASSED.
> - Sub-phase 2D (CE operations + `runtime-registry/` + bridge
>   activation + CLI skeleton + Kokoro G6 report): **✅
>   Complete.** 1 new module (`scripts/runtime_manager.py`)
>   + 1 new directory (`runtime-registry/kokoro-82m/`) +
>   modified `runtime.py` (bridge activation) + modified
>   `runtime_manager.py` (instance cache) + modified
>   `config.py` (`Settings.RUNTIME_REGISTRY_PATH`) + 4 new
>   test files; 32 new tests; 495/495 pre-existing tests
>   pass. Runtime Activation Audit: PASSED. The 2A bridge
>   in `runtime.py` is ACTIVATED: when the manager is wired
>   AND the resolution is non-None, the bridge records a
>   debug log confirming the runtime-service path is
>   reachable. The in-process path is preserved as the CE
>   fallback.
>
> **Phase 2 is COMPLETE.** Phase 3 (Kokoro full migration)
> is the next P0 workstream. TDD-shaped tasks for Phase 3
> (in `TASKS.md` §3):
>
> | # | Component | File | Test |
> |---|---|---|---|
> | 3.1 | E2E test wired into docker-compose CI | `docker-compose.yml` (gated) | `tests/test_kokoro_e2e_runtime.py` passes against a real `peakvox/kokoro-runtime` container |
> | 3.2 | G7 (Performance) validation report | `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-g7-performance-report.md` | RTF, VRAM, load time measured |
> | 3.3 | G8 (Error recovery) validation report | `docs/.agents/VALIDATION/PROVIDER_VALIDATIONS/kokoro-g8-error-recovery-report.md` | Crashed container + network partition recovery |
> | 3.4 | Update `IMPLEMENTATION_STATUS.md` + state files | `docs/.agents/` | cross-link + status update (Phase 3 row IMPLEMENTED) |

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
