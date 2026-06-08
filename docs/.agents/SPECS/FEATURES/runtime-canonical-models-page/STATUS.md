# STATUS — Runtime-Canonical Models Page + Runtime Registry Expansion + T13 Functional Lifecycle

> Lifecycle position in the SDD flow:
> `Brainstorm → Specification → Design → Tasks → Implementation → Validation → Review → Merge`

## Current state

- **Stage:** All workstreams VALIDATED.
- **Implementation status:** **VALIDATED**
- **Status:** `VALIDATED`
- **Owner / last update:** 2026-06-08

## What this feature is

Three workstreams, all part of the Phase 3 full-stack
convergence.

**Workstream A — Runtime-Canonical Models Page.** The
Models page is now a strict 3-tier composed view with a
single canonical lifecycle control surface owned by the
Runtime Section.

**Workstream B — Runtime Registry Expansion (TASK 12).**
The Runtime Registry now hosts three independent runtime
implementations under the same architecture.

**Workstream C — T13: Runtime Registry as the Single Source
of Truth + Fully Functional Runtime Lifecycle.** The
browser-driven Install / Start / Stop / Update / Remove
buttons now actually execute against the runtime
registry. The chain is end-to-end working: browser click
→ React Query mutation → backend lifecycle endpoint →
RuntimeManager → DockerRuntimeDriver → docker SDK → host
Docker daemon → driver-managed container.

The canonical relationship (always):
```
Model
  └─→  Runtime Descriptor
        └─→  Runtime State
```

## Phase status

| Phase | Scope | Status | Notes |
|---|---|---|---|
| 1 | SPEC + DESIGN + TASKS + VALIDATION + STATUS | **APPROVED** | Commit `4acea9c` |
| 2 | Models page implementation (T1–T5) | **IMPLEMENTED** | Commit `5e5616f` |
| 3 | Terminal + visual validation (T6, T7) | **VALIDATED** | 0 console errors |
| 4 | Audits + state file updates (T8) | **COMPLETE** | 4 state files updated |
| 5 | Runtime Registry expansion (T12.1–T12.9) | **VALIDATED** | Commit `dd31fc2` |
| 6 | Runtime Registry SOT + functional lifecycle (T13.1–T13.10) | **VALIDATED** | 13 new regression tests; browser E2E validated |
| 7 | STATUS update (T9) | **VALIDATED** | This document |

## Architectural invariants captured

### Workstream A (Models page)

1. The Models page renders from a single query:
   `useModelsWithRuntimes()` (composed view).
2. The Model section is informational only — zero action buttons.
3. The Runtime section owns lifecycle:
   `Install / Start / Stop / Update / Remove`.
4. OperationsRow is rendered at the TOP of the runtime
   section (immediately after the identity header), so the
   action buttons are visible without scrolling.
5. Models without a runtime descriptor render
   `Runtime Not Migrated` (explicit label) instead of a generic
   empty state.

### Workstream B (Runtime Registry expansion)

1. Three runtime entries now exist under the same R8
   reference shape: `kokoro-82m`, `omnivoice-base`,
   `f5-tts-base`.
2. The RuntimeRegistryLoader auto-discovers all three.
3. The capability subset check (ADR-0017 §1.5) passes for all
   three entries.
4. The Models page does not branch on `runtime_id`; the
   data-driven `RuntimeSection` renders any new entry with
   zero code changes.

### Workstream C (T13: functional lifecycle)

1. **Runtime Registry is the single source of truth.** When
   `RUNTIME_SERVICE_ENABLED=true` and a manager is attached,
   the composed view returns only catalog models that have
   at least one runtime in the registry. The catalog is the
   augmentation, not the other way around.
2. **Browser-driven lifecycle is functional end-to-end.**
   Install → docker SDK records image, cache state=installed.
   Start → driver starts container, /health=200, state=active.
   Stop → container Exited, state=stopped. Update → re-pulls
   image, state=active. Remove → container gone, state=notInstalled.
3. **All runtime fields are descriptor-driven.** No
   hardcoded runtime metadata in the frontend. The phase
   enum is lowercase (matching the API contract).
4. **Regression suite has 13 new tests** covering T13.2
   authority, T13.5 lifecycle, and the no-prefix alias chain.

## Test coverage

| Suite | Count | Status |
|---|---|---|
| `backend/tests/test_runtime_registry_three_descriptors.py` | 23 | ✅ |
| `backend/tests/test_runtime_registry_authority_t13.py` | 13 | ✅ new |
| `backend/tests/test_api_runtimes.py` | (updated) | ✅ |
| `backend/tests/test_api_models_with_runtimes.py` | (updated) | ✅ |
| `runtime-registry/omnivoice-base/tests/test_descriptor.py` | 18 | ✅ |
| `runtime-registry/f5-tts-base/tests/test_descriptor.py` | 18 | ✅ |
| **All runtime-related tests** | **75** | ✅ pass |

## Deliverables

| # | Deliverable | Status |
|---|---|---|
| 1 | Runtime Registry entries (`omnivoice-base`, `f5-tts-base`) | ✅ |
| 2 | Descriptor validation tests | ✅ (36 + 13 + 23 = 72 tests) |
| 3 | Runtime Service Contract tests | ✅ |
| 4 | Runtime discovery tests | ✅ |
| 5 | Lifecycle tests (Install/Start/Stop/Update/Remove) | ✅ end-to-end via browser |
| 6 | Generation validation (TTS produces audio) | ✅ 266,444 bytes WAV from runtime |
| 7 | Chrome DevTools screenshots | ✅ 9+ in `audits/screenshots/` |
| 8 | Runtime Registry audit | ✅ `audits/task-12-runtime-registry-expansion.md` |
| 9 | T13 audit (root cause + browser E2E) | ✅ `audits/task-13-runtime-registry-sot-lifecycle.md` |
| 10 | Architectural findings + migration recommendations | ✅ 6-step recipe |

## Known limitations (documented honestly)

1. The frontend's React Query cache invalidation may
   sometimes show a stale state badge for one frame after a
   lifecycle mutation. Mitigated by `staleTime: 30_000` +
   `refetchInterval: 60_000`.
2. `/v1/variants/build` is 501 in all runtimes (per
   Phase 2C/2D design — variant builds happen in-process).
3. OmniVoice and F5-TTS runtime images are not built in
   this validation pass; only Kokoro's image is. Future
   runtimes follow the same 6-step recipe.
4. `KOKORO_RUNTIME_URL` env var still points to the legacy
   compose service name. A future T13.x should either
   remove it (in favor of runtime discovery) or update it to
   the dynamic container name pattern.

## Related

- [`SPEC.md`](./SPEC.md) — what & why
- [`DESIGN.md`](./DESIGN.md) — components, contracts, layout
- [`TASKS.md`](./TASKS.md) — T0–T9 + §12 + §13 execution plan
- [`VALIDATION.md`](./VALIDATION.md) — pre/post-implementation checks
- [`audits/models-page-canonical-control-surface.md`](./audits/models-page-canonical-control-surface.md) — Workstream A audit
- [`audits/task-12-runtime-registry-expansion.md`](./audits/task-12-runtime-registry-expansion.md) — Workstream B audit
- [`audits/task-13-runtime-registry-sot-lifecycle.md`](./audits/task-13-runtime-registry-sot-lifecycle.md) — Workstream C audit
- [`adr-0016-models-as-runtime-services.md`](../../DECISIONS/adr-0016-models-as-runtime-services.md)
- [`adr-0017-runtime-services-implementation.md`](../../DECISIONS/adr-0017-runtime-services-implementation.md)

