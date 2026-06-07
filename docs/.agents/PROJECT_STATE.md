# PROJECT STATE

> Single source of truth for overall project state. Objective facts only. No emojis, no
> subjective language. Update this file whenever phase, priorities, risks, or blockers change.

**Last update:** 2026-06-07 (refinement pass: Kokoro validation language normalized; Phase 2 guardrail added to NEXT_TASK / CURRENT_PHASE; OPEN_DECISIONS Decision 10 enriched with implementation direction notes; Runtime Manager responsibilities normalized across ADR-0016 / SPEC / DESIGN)
**Branch:** `feat/peakvox-phase-1`
**Edition target:** Community Edition (CE). Cloud is schema-ready, not implemented.
**Cloud readiness gate:** ✅ OPEN — Kokoro validated as first non-OmniVoice provider (G5 passed).
**Architecture direction (new):** ADR-0016 (Models as Runtime Services) accepted 2026-06-07.
The Runtime-Service architecture is the agreed target; migration is sequenced across
7 phases. Phase 1 (ADR + design) is complete; Phase 2 (Runtime Manager skeleton +
`DockerRuntimeDriver`) is the next workstream.

---

## Current phase

PeakVox Phase 1 (Platform Foundations) through Phase 3.11 are built. The CE spine
(Phases 1–3 plus sub-phases 3.5–3.11) is implemented and covered by automated tests.
Kokoro provider validation is complete (G5 passed — real audio generated E2E through
the Runtime; see `VALIDATION/PROVIDER_VALIDATIONS/kokoro-validation-report.md`).
Active focus: the Runtime-Service architecture (ADR-0016, accepted 2026-06-07);
Phase 1 (ADR + design) is complete, Phase 2 implementation is gated on a Phase 2
implementation ADR. See [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md) and
[`ROADMAP/ROADMAP.md`](ROADMAP/ROADMAP.md).

## Current priorities

1. ✅ **Provider-validation gap closed.** Kokoro generates real audio E2E through the Runtime.
   Cloud readiness gate is open.
2. ✅ **Runtime-Service architecture designed.** ADR-0016 (Models as Runtime Services) is
   accepted. PeakVox will evolve to a Runtime-Service architecture (Runtime Registry +
   Runtime Manager + Runtime Driver + Runtime Service). See
   `docs/.agents/SPECS/FEATURES/models-as-runtime-services/`. 7-phase migration plan; Phase 1
   (this) is documentation only.
3. **Next workstream:** begin **Phase 2** of the Runtime-Service migration — implement
   the Runtime Manager skeleton + `DockerRuntimeDriver` (no model migrated yet). This
   preempts Cloud work; the Runtime-Service target is the same for CE and Cloud
   (Article V §14), so investing in Phase 2 unblocks both editions.

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
- **Phase 2 implementation ADR not yet written.** Phase 2 of the Runtime-Service migration
  (Runtime Manager skeleton + `DockerRuntimeDriver`) is gated on a Phase 2 implementation
  ADR that addresses the five open questions tracked in `OPEN_DECISIONS.md` Decision 10.

---

**Related:** [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) ·
[`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) · [`ACTIVE_WORK.md`](ACTIVE_WORK.md) ·
[`NEXT_TASK.md`](NEXT_TASK.md) · [`HANDOFF.md`](HANDOFF.md)
