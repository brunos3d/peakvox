# STATUS — Models as Runtime Services

Lifecycle position in the SDD flow:
`Brainstorm → Specification → Design → Tasks → Implementation → Validation → Review → Merge`

- **Current stage:** Phase 1 (Architecture — ADR + design docs).
- **Implementation status:** **APPROVED** (ADR-0016 accepted; no
  implementation; per Constitution §22, "Accepted" is not "Implemented").
- **Owner / last update:** 2026-06-07.
- **Outcome (on completion):** ADR-0016 is recorded in
  [`ADR_INDEX.md`](../../../DECISIONS/ADR_INDEX.md) and
  [`IMPLEMENTATION_STATUS.md`](../../../IMPLEMENTATION_STATUS.md);
  state files reflect the new feature. No code, no `runtime-registry/`
  directory, no Docker wiring, no F5-TTS implementation — all deferred
  to Phase 2+.

---

## Phase status

| Phase | Scope | Status | Notes |
|---|---|---|---|
| 1 | ADR + design docs | **APPROVED** (this phase) | No code. ADR-0016 accepted. |
| 2 | Runtime Registry + Runtime Manager skeleton | NOT_STARTED | Defer until Phase 1 ADR accepted. |
| 3 | Kokoro migration | NOT_STARTED | First validation target. |
| 4 | F5-TTS as Runtime Service | NOT_STARTED | Reference implementation. |
| 5 | Fish Audio migration | NOT_STARTED | Subject to existing hardware blocker. |
| 6 | OmniVoice migration | NOT_STARTED | The most integrated model. |
| 7 | Remove in-process model execution | NOT_STARTED | Final cutover. |

---

## What this phase produced

- [`SPEC.md`](./SPEC.md) — what & why, with the corrected flow
  `Voice → VoiceVariant → Active Artifact → Adapter → Runtime Manager →
  Runtime Driver → Runtime Service → Inference`.
- [`DESIGN.md`](./DESIGN.md) — components, Runtime Manager boundaries,
  Runtime Driver contract, Runtime Registry future structure, Runtime
  Descriptor schema, adapter evolution, generation flow,
  installation flow, ADR / Constitution alignment, risks.
- [`TASKS.md`](./TASKS.md) — 7-phase migration with TDD per task.
- [`VALIDATION.md`](./VALIDATION.md) — architecture vs provider
  validation distinction preserved.
- [`STATUS.md`](./STATUS.md) — this file.
- [`adr-0016-models-as-runtime-services.md`](../../../DECISIONS/adr-0016-models-as-runtime-services.md) — the ADR.

## What this phase did NOT produce (per the non-goals)

- No `RuntimeManager` class.
- No `RuntimeRegistry` class or `runtime-registry/` directory.
- No `RuntimeDriver` / `DockerRuntimeDriver` code.
- No `KubernetesRuntimeDriver` (informational only).
- No `PodmanRuntimeDriver` (informational only).
- No `LocalProcessDriver` (informational only).
- No adapter migration code.
- No `runtime_binding` column on `models` (Phase 3+).
- No schema changes of any kind.
- No `GET /api/v1/runtimes` endpoint (Phase 2+).
- No F5-TTS implementation, image, or adapter.
- No frontend changes.
- No Docker / Docker Compose files.

## Phase 2 guardrail (mirrored in NEXT_TASK.md and ROADMAP/CURRENT_PHASE.md)

> **Phase 2 of the Runtime-Service migration may not begin until the
> Phase 2 implementation ADR is Accepted.**
>
> The Phase 2 implementation ADR must address the five open questions
> tracked in [`OPEN_DECISIONS.md`](../../../OPEN_DECISIONS.md) Decision 10
> (runtime endpoint discovery, runtime upgrade / rollback, GPU allocation
> ownership, runtime health contract, backend-to-runtime authentication).
> Until that ADR is Accepted, **no code, no `RuntimeManager` class, no
> `RuntimeDriver`, no `runtime-registry/` directory, no Docker
> integration, no `GET /api/v1/runtimes` endpoint may be written.**

---

## Architectural invariants captured

1. Models are catalog entities (ADR-0002).
2. Runtimes are deployment units.
3. **PeakVox installs runtimes, not models.** One Model → many Runtimes.
4. The backend never owns model dependencies.
5. The backend never executes model inference.
6. Runtime Manager orchestrates; it does not execute.
7. Runtime Registry describes; the descriptor is the contract.
8. Adapters communicate with runtime services (HTTP/gRPC) and never
   with Docker / Kubernetes / Podman.
9. Runtime services are replaceable.
10. CE and Cloud share the architecture (RuntimeDriver is the seam).
11. **Runtime infrastructure is not a domain concept.** Forbidden:
    `RuntimeServiceEntity`, `RuntimeServiceRepository`,
    `RuntimeVariant`, `RuntimeArtifact`.
12. Active Artifact resolution is preserved (Voice → VoiceVariant →
    Active Artifact → Adapter → Runtime Manager → Runtime Driver →
    Runtime Service → Inference).

---

## Next step

ADR-0016 has been moved from the design desk to the implementation
backlog. The current state (2026-06-07):

1. ✅ ADR-0016 is **Accepted**; Phase 1 (ADR + design) is **complete**.
2. ✅ Phase 2 has been **promoted** to
   [`NEXT_TASK.md`](../../../NEXT_TASK.md) and
   [`ROADMAP/CURRENT_PHASE.md`](../../../ROADMAP/CURRENT_PHASE.md) — but is
   **gated** on the Phase 2 implementation ADR (see guardrail above).
3. ⏸ Phase 2 implementation ADR is **not yet written**. It must address
   the five open questions in
   [`OPEN_DECISIONS.md`](../../../OPEN_DECISIONS.md) Decision 10
   §"Implementation direction (non-binding)" — which are *direction
   notes*, not accepted decisions.
4. ⏸ Phases 3–7 (Kokoro, F5-TTS, Fish, OmniVoice migrations, in-process
   path removal) are sequenced behind Phase 2.

**Phase 2 implementation does not start until the Phase 2 ADR is
Accepted.** No exceptions.

---

**Related:** [`SPEC.md`](./SPEC.md) · [`DESIGN.md`](./DESIGN.md) ·
[`TASKS.md`](./TASKS.md) · [`VALIDATION.md`](./VALIDATION.md) ·
[`adr-0016-models-as-runtime-services.md`](../../../DECISIONS/adr-0016-models-as-runtime-services.md)
