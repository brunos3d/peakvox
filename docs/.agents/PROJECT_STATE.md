# PROJECT STATE

> Single source of truth for overall project state. Objective facts only. No emojis, no
> subjective language. Update this file whenever phase, priorities, risks, or blockers change.

**Last update:** 2026-06-07 (Phase 2 — COMPLETE: 2A delivered 9 modules + 9 test files (76 new tests); 2B delivered `DockerRuntimeDriver` + `lint_no_docker_outside_driver.py` + manager wiring (40 new tests); 2C delivered `HTTPTransport` + `KokoroAdapter` `KOKORO_RUNTIME_URL` integration + env plumbing + E2E scaffold (25 new tests, 1 skipped); 2D delivered `runtime-registry/` with Kokoro descriptor + `RuntimeManager` instance cache + CE operations + 2A bridge activation + CLI skeleton + Kokoro G6 provider-validated report (32 new tests); 0 regressions; 495 pre-existing tests pass; Phase 3 (Kokoro full migration) is the next P0 workstream)
**Branch:** `feat/peakvox-phase-1`
**Edition target:** Community Edition (CE). Cloud is schema-ready, not implemented.
**Cloud readiness gate:** ✅ OPEN — Kokoro validated as first non-OmniVoice provider (G5 in-process + G6 runtime-service architecturally).
**Architecture direction:** ADR-0016 (Models as Runtime Services) Accepted+Implemented
(Phase 1+2A+2B+2C+2D) 2026-06-07; ADR-0017 (Runtime Services Implementation — Phase 2
architecture) Accepted+Implemented (2A+2B+2C+2D) 2026-06-07. **Phase 2 is COMPLETE.**
The Runtime-Service architecture is the agreed target; migration is sequenced across
7 phases. Phase 1 (ADR + design) and Phase 2 (Sub-phases 2A + 2B + 2C + 2D) are
complete. The Runtime Activation Audit (all 7 checks PASS) confirms the canonical
chain (Voice → VoiceVariant → Active Artifact → Adapter) is intact and runtime
infrastructure is strictly downstream. Phase 3 (Kokoro full migration) is the
next P0 workstream.

---

## Current phase

PeakVox Phase 1 (Platform Foundations) through Phase 3.11 are built. The CE spine
(Phases 1–3 plus sub-phases 3.5–3.11) is implemented and covered by automated tests.
Kokoro provider validation is complete (G5 passed — real audio generated E2E through
the Runtime; see `VALIDATION/PROVIDER_VALIDATIONS/kokoro-validation-report.md`).
Active focus: Phase 3 (Kokoro full migration). **Phase 2
is COMPLETE (2026-06-07).** ADR-0016 (architecture) is
Accepted+Implemented (Phase 1+2A+2B+2C+2D); ADR-0017
(Phase 2 implementation architecture) is Accepted+Implemented
(2A+2B+2C+2D). The Runtime Activation Audit (all 7 checks
PASS) confirms the canonical chain (Voice → VoiceVariant →
Active Artifact → Adapter) is intact and runtime
infrastructure is strictly downstream. Phase 2 Sub-phases
2A (Foundations), 2B (DockerRuntimeDriver + manager wiring
+ lint script), 2C (`HTTPTransport` + `KokoroAdapter`
`KOKORO_RUNTIME_URL` integration + env plumbing + E2E
scaffold), and 2D (CE operations + `runtime-registry/` with
Kokoro descriptor + bridge activation + CLI skeleton +
Kokoro G6 provider-validated report) are **complete**
(2026-06-07). **Phase 3 is the next P0 workstream.** See
[`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md)
and [`ROADMAP/ROADMAP.md`](ROADMAP/ROADMAP.md).

## Current priorities

1. ✅ **Provider-validation gap closed.** Kokoro generates real audio E2E through the Runtime.
   Cloud readiness gate is open.
2. ✅ **Runtime-Service architecture designed (ADR-0016 Accepted).** PeakVox will evolve to
   a Runtime-Service architecture (Runtime Registry + Runtime Manager + Runtime Driver +
   Runtime Service). 7-phase migration plan; Phase 1 (this) is documentation only.
3. ✅ **Phase 2 implementation architecture accepted (ADR-0017).** See
   `docs/.agents/SPECS/FEATURES/runtime-services-implementation/`. Specifies the 10
   deliverables and resolves the 5 deferred open questions from
   `OPEN_DECISIONS.md` Decision 10 (now RESOLVED). Architecture review: 0 blocking
   issues; non-blocking suggestions applied.
4. ✅ **Sub-phase 2A (Foundations) complete.** 9 new modules + 9 test files; 76 new
   tests, 0 regressions, 401 pre-existing tests pass; no Docker integration, no
   Runtime Service communication, no model framework imports, no HTTP clients in
   the new modules; the `PeakVoxRuntime` bridge is a transitional pass-through that
   preserves existing in-process generation behavior.
5. ✅ **Sub-phase 2B (First Concrete Driver) complete.** 1 new module + 1 new
   script + 2 modified modules + 2 new test files; 40 new tests; 0 regressions;
   441 pre-existing tests pass. Docker imports confined to the driver package
   (enforced by `lint_no_docker_outside_driver.py`). The
   `RuntimeManager.resolve()` returns a non-None `RuntimeResolution` when a
   driver is wired; the 2A bridge in `runtime.py` is unchanged (the
   runtime-service branch is still a literal `pass`; activation is in 2C).
6. ✅ **Sub-phase 2C (Runtime-Service Communication Path) complete.** 1 new
   transport module (`HTTPTransport`) + 1 modified adapter
   (`KokoroAdapter` dispatches on `KOKORO_RUNTIME_URL`) + 1
   modified settings (`Settings.KOKORO_RUNTIME_URL`) + 3 new
   test files (14 transport + 8 adapter isolation + 3
   settings) + 1 E2E scaffold (gated, skipped in default
   venv). 25 new tests, 1 skipped; 466 pre-existing tests
   pass. Transport Boundary Audit: PASSED. The `KokoroAdapter`
   gains ONE new dependency (`HTTPTransport`); it does NOT
   gain knowledge of Docker / `RuntimeDescriptor` /
   `RuntimeInstance` / `RuntimeRegistry` / `RuntimeManager`.
   The in-process path is preserved as the CE default.
7. ✅ **Sub-phase 2D (CE Operations + Bridge Activation)
   complete — Phase 2 is COMPLETE.** `runtime-registry/`
   with Kokoro descriptor + `RuntimeManager` instance
   cache + CE operations + 2A bridge activation (log when
   resolution is non-None) + `RuntimeOperator` CLI
   skeleton + Kokoro G6 provider-validated report. 32
   new tests; 495 pre-existing tests pass; 0
   regressions. The Runtime Activation Audit (all 7
   checks PASS) confirms the canonical chain (Voice →
   VoiceVariant → Active Artifact → Adapter) is intact
   and runtime infrastructure is strictly downstream.
8. **Next workstream:** begin **Phase 3 (Kokoro full
   migration)**. The Kokoro provider becomes the FIRST
   provider that runs ONLY through the runtime service in
   CE (in-process path is still available as a fallback,
   but the default CE deployment uses the runtime service).
   The Kokoro descriptor's `image.digest` pins the runtime
   service to a specific image version. The Kokoro adapter
   is updated to communicate with the runtime service by
   default.

## Implemented components (architecture-validated; see IMPLEMENTATION_STATUS for evidence)

- Persisted multi-model registry + canonical metadata (`model_registry.py`, `model_catalog.py`).
- Model Capability Contract (`registry_types.py::ModelCapabilities`, `capabilities.py`).
- Voice / VoiceVariant split with backfill + dual-write (`models/db.py`,
  `voice_variant_repository.py`, `variant_resolution.py`, `voice_onboarding.py`).
- `PeakVoxRuntime` single generation entry point (`runtime.py`); all generation routes through it.
- `ModelAdapter` contract + OmniVoice / OmniVoiceSinging / Fish / Kokoro adapters (`model_adapter.py`,
  `model_adapters/`).
- `ProviderVoice` domain type + `ProviderVoiceCatalog` protocol + `ProviderVoiceRegistry` lifecycle
  (`services/provider_voice.py`).
- Variant build lifecycle (5-state machine) + artifact versioning/retention/rollback
  (`variant_lifecycle.py`, `voice_variant_artifact_repository.py`).
- Edition-scoped model availability (`runtime.ensure_available`, `ModelDescriptor.editions`).
- Voice Library 2.0 + variant dashboard + backfill UX (frontend voice components; variants API).
- Versioned public API surface (`api/v1.py`); hashed keys; identity + rate-limit seams.

## Partially implemented components

- **OmniVoice Base inference:** real `from_pretrained` + `generate_async`; no automated
  end-to-end audio test in CI (no GPU/weights).
- **OmniVoice Singing:** shares the OmniVoice engine; catalog `status="disabled"`;
  singing-specific generation unverified.
- **Model lifecycle install/update:** state transitions real and tested; artifact download
  mocked.
- **HF community install:** `snapshot_download` real, mocked in tests; `_KNOWN_PROVIDERS`
  limited to OmniVoice variants (Fish/Kokoro rejected by the installer).
- **Runtime-Service architecture (ADR-0016):** Phase 1 (ADR + design) **complete**;
  Phases 2–7 (Runtime Manager, Kokoro/F5/Fish/OmniVoice migrations, in-process path
  removal) are planned, not started. Existing in-process model execution continues
  throughout.
- **Phase 2 implementation architecture (ADR-0017):** **Accepted+Implemented (2A+2B+2C+2D)**
  2026-06-07. Specifies the 10 deliverables; resolves the 5 deferred open
  questions from `OPEN_DECISIONS.md` Decision 10. Phases 2A+2B+2C+2D implemented:
  9 modules + 1 driver + 1 transport + 1 settings field + 1 CLI skeleton + 1
  runtime-registry/ directory; 21 new test files. **Phase 2 is COMPLETE.**

## Planned components (schema/seams only; no implementation)

- Authentication (Phase 4, Cloud) — `AuthProvider` seam exists.
- Billing/credits (Phase 5, Cloud) — `BillingProvider`/`PaymentProvider` seams + empty tables.
- Creator system (Phase 6, Cloud).
- Marketplace (Phase 7, Cloud).
- Cloud infrastructure / Postgres / Alembic / worker pool (Phase 8, Cloud).
- Production scaling (Phase 10, Cloud).

## Validation status

- **Architecture validated:** broad. ~237+ backend tests across 57 test files prove the
  contracts, data model, and orchestration. See [`VALIDATION/RETROSPECTIVES/`](VALIDATION/RETROSPECTIVES/).
- **Provider validated:** OmniVoice and Kokoro. Real audio generated end-to-end through the
  PeakVox Runtime for both providers:
  - **OmniVoice:** real `from_pretrained` + `generate_async`; no automated end-to-end
    audio test in CI (no GPU/weights in CI lane), but provider-validated manually.
  - **Kokoro:** G5 passed (2026-06-05). Real audio generated E2E through the Runtime
    using the `kokoro` pip package (82M params, CPU-capable). See
    `VALIDATION/PROVIDER_VALIDATIONS/kokoro-validation-report.md`.
  - **Fish Audio:** integrated at the contract level (HTTP client wired, unit-tested
    with mocks). Real inference blocked on hardware (24GB+ VRAM required for the full
    S2 Pro `codec.pth`; see Fish blocker report). Architecture-validated only.
  - **F5-TTS / XTTS / others:** future providers; will integrate through the
    Runtime-Service architecture (ADR-0016).

## Current risks

- **Fish Audio real inference still deferred.** The Fish adapter is wired as HTTP client
  and unit-tested, but the S2 Pro server (codec.pth / 24GB+ VRAM) remains blocked.
- **Cloud readiness gate is open.** Provider validation (Kokoro G5) unblocks Cloud
  architecture planning, but Cloud implementation should be deliberate — premature
  investment in auth/billing/marketplace before the Runtime-Service architecture lands
  would re-couple backend to model execution. Phase 2 of the Runtime-Service migration
  is the deliberate precursor.
- **Kokoro performance not measured.** G7 (RTF, VRAM, load time) and G8 (error recovery)
  are not systematically tested. Low priority; not a provider-validation blocker.

## Current blockers

- **Fish Audio real inference** is deferred. Root cause: v1.4/v1.5 codec checkpoint is
  structurally incomplete for an 8GB GPU; full `codec.pth` (s2-pro) needs 24GB+ VRAM. See
  [`VALIDATION/PROVIDER_VALIDATIONS/`](VALIDATION/PROVIDER_VALIDATIONS/) (Fish blocker report).
- No GPU in CI, so end-to-end audio generation cannot be fully automated in the test suite.
- `test_voices.py` requires `torch` — excluded from local test suite; only runs in Docker.
- **No architectural blockers for Phase 3 implementation.** ADR-0017 is
  Accepted+Implemented (2A+2B+2C+2D). **Phase 2 is COMPLETE.** Phase 3
  (Kokoro full migration — E2E docker-compose CI + G7/G8 validation
  reports) is the next P0 workstream. The Runtime Persistence
  follow-up ADR is tracked as [`OPEN_DECISIONS.md` Decision 12](OPEN_DECISIONS.md)
  (non-blocking, future work).

---

**Related:** [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) ·
[`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) · [`ACTIVE_WORK.md`](ACTIVE_WORK.md) ·
[`NEXT_TASK.md`](NEXT_TASK.md) · [`HANDOFF.md`](HANDOFF.md)
