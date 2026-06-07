# NEXT TASK

> Exactly one highest-priority task — the execution queue head. When this task is done, move
> it to the execution ledger and promote the next item from [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

**As of:** 2026-06-07

> ## ⚠ PHASE 2 GUARDRAIL — DO NOT BEGIN IMPLEMENTATION
>
> **Phase 2 of the Runtime-Service migration may not begin until the Phase 2
> implementation ADR is Accepted.**
>
> Current state:
> - ADR-0016 (architecture): **Accepted** (2026-06-07).
> - Phase 1 (ADR + design docs): **Complete** (this phase).
> - Phase 2 (Runtime Manager skeleton + `DockerRuntimeDriver`): **Not started.**
> - Phase 2 implementation ADR: **Not written.**
>
> The Phase 2 implementation ADR must address the five open questions tracked in
> [`OPEN_DECISIONS.md` Decision 10](OPEN_DECISIONS.md) (runtime endpoint
> discovery, runtime upgrade / rollback, GPU allocation ownership, runtime
> health contract, backend-to-runtime authentication). Until that ADR is
> Accepted, **no code, no `RuntimeManager` class, no `RuntimeDriver`, no
> `runtime-registry/` directory, no Docker integration, no `GET
> /api/v1/runtimes` endpoint may be written.**
>
> This guardrail is mirrored in [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md)
> and the Phase 2 entry in [`ROADMAP/BACKLOG.md`](ROADMAP/BACKLOG.md).

## Task: Runtime-Service Migration — Phase 2 (Runtime Manager skeleton + DockerRuntimeDriver)

- **Priority:** P0 (new). Supersedes the prior "Cloud architecture planning" decision item
  now that ADR-0016 is accepted.
- **Status:** **Phase 1 complete (ADR + design, no code).** ADR-0016 is Accepted (2026-06-07).
  Phase 2 implementation is **next** but does not start until the Phase 2 implementation ADR
  is written to address the deferred open questions (runtime endpoint discovery, GPU
  allocation, runtime health contract, backend-to-runtime auth).
- **Decision (new):** PeakVox adopts the Runtime-Service architecture. PeakVox installs
  *runtimes*, not models. One Model → many Runtimes (CUDA / CPU / local / cloud).
  See `docs/.agents/SPECS/FEATURES/models-as-runtime-services/`.
- **Phase 2 plan (deferred, awaiting Phase 2 implementation ADR):**
  1. `RuntimeDescriptor` Pydantic model (`backend/app/services/runtime_types.py`).
  2. `RuntimeRegistryLoader` (`backend/app/services/runtime_registry.py`).
  3. `RuntimeDriver` protocol + `DockerRuntimeDriver` first implementation.
  4. `RuntimeManager` skeleton (orchestrates; never executes inference).
  5. `lint_no_docker_outside_driver.py` AST check (ban `import docker` outside driver pkg).
  6. `GET /api/v1/runtimes` discovery endpoint.
  7. ARCHITECTURE update — new §13 "Runtime Layer".
- **Provider-validation status (unchanged):** Kokoro G5 ✅. Fish Audio S2 Pro still blocked
  on hardware. OmniVoice Base E2E audio test would be nice; no GPU in CI.
- **Cloud readiness gate:** still OPEN. Phase 2 is the new gateway: it unblocks both CE
  hardening and Cloud architecture planning by establishing the substrate-neutral
  runtime layer.
- **Next:** write the Phase 2 implementation ADR; begin Phase 2 implementation.

---

**Related:** [`ACTIVE_WORK.md`](ACTIVE_WORK.md) · [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md) ·
[`docs/.agents/SPECS/FEATURES/models-as-runtime-services/`](SPECS/FEATURES/models-as-runtime-services/) ·
[`docs/.agents/DECISIONS/adr-0016-models-as-runtime-services.md`](DECISIONS/adr-0016-models-as-runtime-services.md)
