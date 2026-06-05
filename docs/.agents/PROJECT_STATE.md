# PROJECT STATE

> Single source of truth for overall project state. Objective facts only. No emojis, no
> subjective language. Update this file whenever phase, priorities, risks, or blockers change.

**Last update:** 2026-06-05
**Branch:** `feat/peakvox-phase-1`
**Edition target:** Community Edition (CE). Cloud is schema-ready, not implemented.

---

## Current phase

PeakVox Phase 1 (Platform Foundations) through Phase 3.11 are built. The CE spine
(Phases 1–3 plus sub-phases 3.5–3.11) is implemented and covered by automated tests.
Active work is post-Phase-3 CE hardening: Kokoro Preset Voice Adapter (Phase 1 complete),
Voice Library 2.0 UI, variant backfill UX, and Fish Audio provider wiring. Cloud phases
(4–10) are not started.

See [`ROADMAP/CURRENT_PHASE.md`](ROADMAP/CURRENT_PHASE.md) and
[`ROADMAP/ROADMAP.md`](ROADMAP/ROADMAP.md).

## Current priorities

1. Close the provider-validation gap: get at least one non-OmniVoice provider generating real
   audio end-to-end through the Runtime (see [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md)).
2. Hold the readiness gate: do not begin Cloud (auth/billing/marketplace) work until a real
   foreign provider is validated.

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
- **Provider validated:** narrow. Only OmniVoice has a real engine. Fish Audio is integrated
  at the contract level; real inference is blocked on hardware/codec issues. Kokoro is
  architecture-validated (54 presets, mock-kokoro tests); real inference requires `kokoro`
  pip package. See [`VALIDATION/PROVIDER_VALIDATIONS/`](VALIDATION/PROVIDER_VALIDATIONS/).

## Current risks

- **Single-real-provider runtime.** The multi-provider thesis is proven as architecture, not
  as production reality. Kokoro has de-risked the preset-voice, non-cloning provider pattern
  (ProviderVoice, 54 presets, `build_variant`→NotImplementedError) — but still no real audio
  E2E for any non-OmniVoice provider.
- **Kokoro real inference deferred.** Architecture-validated; real inference requires `kokoro`
  pip package (not in local venv).
- **Fish Audio real inference still deferred.** The Fish adapter is now wired as HTTP client
  and unit-tested, but the S2 Pro server (codec.pth / 24GB+ VRAM) remains blocked.
- **Premature Cloud investment.** Beginning SaaS/billing work before provider validation would
  build the ecosystem on an unproven runtime.

## Current blockers

- **Fish Audio real inference** is deferred. Root cause: v1.4/v1.5 codec checkpoint is
  structurally incomplete for an 8GB GPU; full `codec.pth` (s2-pro) needs 24GB+ VRAM. See
  [`VALIDATION/PROVIDER_VALIDATIONS/`](VALIDATION/PROVIDER_VALIDATIONS/) (Fish blocker report).
- **Kokoro real inference** is deferred (not blocked). Requires `kokoro` pip package; no GPU or
  large model download needed — Kokoro is CPU-capable at 82M params.
- No GPU in CI, so end-to-end audio generation cannot be automated in the test suite.
- `test_voices.py` requires `torch` — excluded from local test suite; only runs in Docker.

---

**Related:** [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) ·
[`CURRENT_CONTEXT.md`](CURRENT_CONTEXT.md) · [`ACTIVE_WORK.md`](ACTIVE_WORK.md) ·
[`NEXT_TASK.md`](NEXT_TASK.md) · [`HANDOFF.md`](HANDOFF.md)
