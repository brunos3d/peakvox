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

- **Runtime-Service migration — Phase 2.** Runtime Manager skeleton +
  `DockerRuntimeDriver`. **Gated on the Phase 2 implementation ADR.**

> ## ⚠ PHASE 2 IMPLEMENTATION GUARDRAIL
>
> **Phase 2 of the Runtime-Service migration may not begin until the Phase 2
> implementation ADR is Accepted.**
>
> Phase 2 implementation requires the Phase 2 implementation ADR to address the
> five open questions tracked in
> [`../OPEN_DECISIONS.md`](../OPEN_DECISIONS.md) Decision 10:
> 1. Runtime endpoint discovery
> 2. Runtime upgrade / rollback
> 3. GPU allocation ownership
> 4. Runtime health contract
> 5. Backend-to-runtime authentication
>
> Until the Phase 2 ADR is Accepted:
> - **No `RuntimeManager` code.**
> - **No `RuntimeDriver` / `DockerRuntimeDriver` code.**
> - **No `runtime-registry/` directory.**
> - **No Docker integration / Docker SDK.**
> - **No `GET /api/v1/runtimes` endpoint.**
> - **No adapter migration code.**
>
> Non-binding implementation direction notes for those five questions are
> recorded in `OPEN_DECISIONS.md` Decision 10 §"Implementation direction
> (non-binding)". They are **not** accepted decisions and **may not** be used
> to justify Phase 2 code.

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
