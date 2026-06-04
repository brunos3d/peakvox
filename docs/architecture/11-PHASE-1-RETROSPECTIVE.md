# 11 — Phase 1 Retrospective

**Status:** Validation snapshot · **Date:** 2026-06-04 · **Branch:** `feat/peakvox-phase-1`
**Test baseline at writing:** 237 backend tests passing across 55 test files.

> **Purpose.** Phase 1 designed and built the PeakVox Universal Voice Runtime foundations
> (ADR-0001 → ADR-0009). This document is an honest accounting of **what is actually proven**
> before any SaaS / billing / auth / marketplace work begins. It deliberately separates two
> claims that are easy to conflate:
>
> - **Architecture validated** — the abstractions, contracts, and data model are implemented
>   and covered by automated tests.
> - **Provider validated** — a *real model* installs, loads, builds a variant, resolves, and
>   *actually generates audio* through the Runtime.
>
> These are different things. The architecture can be fully validated while a provider remains
> theoretical. Conflating them is how a platform claims "supports N models" while only one
> truly runs.

---

## 1. The central distinction

```
ARCHITECTURE VALIDATED                     PROVIDER VALIDATED
──────────────────────                     ──────────────────
Can the platform REPRESENT and             Does a REAL model actually
ORCHESTRATE this concept?                  RUN end-to-end through it?

Proven by: unit/integration tests          Proven by: real install + load +
over the contracts and data model.         build + resolve + GENERATE audio.

Example: "A Voice resolves to a            Example: "Fish Audio S2 Pro encodes
per-provider VoiceVariant through one      a reference clip into a speaker
Runtime" — TRUE, tested across 3           embedding and synthesises speech" —
provider adapters.                         NOT TRUE today (inference unwired).
```

**Phase 1 achieved broad _architecture_ validation and narrow _provider_ validation.** Exactly
one provider family (OmniVoice) has real inference code; every other provider is integrated at
the contract level only.

---

## 2. What was planned

The Phase 0 architecture suite ([`00-VISION`](00-VISION.md) → [`10-RUNTIME`](10-RUNTIME_ARCHITECTURE.md))
plus nine ADRs defined the foundation:

| ADR | Decision | Phase |
|---|---|---|
| [0001](adrs/0001-voice-variant-split.md) | Voice / VoiceVariant split | P3 |
| [0002](adrs/0002-model-as-first-class-entity.md) | Model as a first-class persisted entity | P2 |
| [0003](adrs/0003-model-capability-contract.md) | Declared Model Capability Contract | P3.6 |
| [0004](adrs/0004-voice-variant-model-separation.md) | Voice ≠ VoiceVariant ≠ Model separation | P3.5 |
| [0005](adrs/0005-edition-scoped-model-availability.md) | Edition-scoped model availability | P3.7.5 |
| [0006](adrs/0006-voice-variant-realization-types.md) | Open realization-type taxonomy | P3.6 |
| [0007](adrs/0007-canonical-model-metadata.md) | Canonical model metadata registry | P2 |
| [0008](adrs/0008-voice-variant-build-lifecycle.md) | Voice Variant Build Lifecycle | P3.11 |
| [0009](adrs/0009-artifact-versioning-and-retention.md) | Artifact versioning + retention | P3.11 |

The roadmap ([`09-ROADMAP`](09-ROADMAP.md)) placed these as the CE-side **spine** (P1–P3 +
sub-phases) that gates the Cloud ecosystem (P4–P10).

---

## 3. What was implemented

All nine ADRs are implemented in code. Key surfaces (file pointers are the source of truth):

| Concern | Implementation | Status |
|---|---|---|
| Voice identity (stable `public_voice_id`) | `models/db.py::Voice`; `voice_variant_repository.py` | Implemented |
| VoiceVariant realization | `models/db.py::VoiceVariant`; `variant_resolution.py` | Implemented |
| Model registry / catalog | `model_registry.py`, `model_catalog.py`, `model_providers/` | Implemented |
| Capability contract | `registry_types.py::ModelCapabilities`, `capabilities.py` | Implemented |
| Runtime orchestration | `runtime.py::PeakVoxRuntime` (single entry point) | Implemented |
| ModelAdapter contract | `model_adapter.py`; `model_adapters/{omnivoice,fish}_adapter.py` | Implemented |
| Edition availability | `runtime.ensure_available`, `ModelDescriptor.editions` | Implemented |
| Model lifecycle (state) | `model_lifecycle.py` (activate/deactivate/install/update/remove) | **State real; install mocked** |
| Variant build lifecycle | `variant_lifecycle.py`; `runtime.build/rebuild/ensure_variant` | Implemented (sync) |
| Artifact versioning | `voice_variant_artifacts` table; `voice_variant_artifact_repository.py` | Implemented |
| Real inference | `omnivoice_service.py` (`OmniVoice.from_pretrained` + `generate_async`) | **OmniVoice only** |

---

## 4. What was validated (automated tests)

237 tests prove the **architecture**. Representative coverage:

- **Identity & split:** `test_voice_split_migration`, `test_voice_dual_write`,
  `test_voice_variant_repository`, `test_variant_resolution`, `test_variant_stamp`.
- **Runtime orchestration:** `test_runtime` (resolution, tags, capabilities, ad-hoc generation),
  `test_runtime_readiness`, `test_runtime_editions`, `test_runtime_wiring`.
- **Multi-provider thesis:** `test_multimodel_resolution`, `test_universal_voice_asset`
  (one `public_voice_id` → OmniVoice / Singing / Fish variants through one Runtime).
- **Capability contract:** `test_capabilities_contract`, `test_capabilities_service`,
  `test_catalog_capabilities` (no model-name branching).
- **Edition scoping:** `test_editions`, `test_model_availability`, `test_runtime_editions`.
- **Model registry / metadata:** `test_model_registry`, `test_model_catalog`,
  `test_registry_metadata`, `test_models_api_metadata`, `test_model_lifecycle`,
  `test_model_management`.
- **Build lifecycle + artifacts (ADR-0008/0009):** `test_variant_lifecycle`,
  `test_artifact_versioning_migration`, `test_artifact_repository`,
  `test_runtime_variant_lifecycle`, `test_adapter_realization_surface`.

**What these tests do NOT do:** none of them load real model weights, run a GPU, or synthesise
audio. They validate the *contracts and orchestration*, not the *providers*. This is by design
(CI has no GPU and must not download multi-GB weights), but it is exactly why provider
validation is a separate, still-mostly-open program ([`12-PROVIDER-VALIDATION`](12-PROVIDER-VALIDATION.md)).

---

## 5. The real-vs-mocked boundary (honesty map)

| Path | Real | Mocked / stubbed | Notes |
|---|---|---|---|
| OmniVoice Base inference | ✓ `omnivoice_service` | — | Real `from_pretrained` + `generate_async`; needs weights + device at runtime; **no automated end-to-end audio test** |
| OmniVoice Singing inference | ~ shares OmniVoice path | — | Catalog `status="disabled"`; not exercised against the singing weights |
| Fish Audio inference | — | ✗ `NotImplementedError` | `load()`/`generate()` raise; embedding never computed |
| Fish variant build | partial | embedding stub | Variant row created with `{"embedding": null, "computed": false}` |
| HF community install | ✓ `snapshot_download` | mocked in tests | `_KNOWN_PROVIDERS = {omnivoice, omnivoice-singing}` — **Fish/Kokoro rejected** |
| Model lifecycle install | state only | ✗ download mocked | `install_model` flips status; "real artifact download is intentionally mocked" |
| Variant build queue (async) | — | deferred | ADR-0008 Option 3; CE builds run synchronously |

---

## 6. Validation matrix

### ✅ Architecture validated (implemented + automated tests)

| Capability | Evidence |
|---|---|
| ✓ Voice Identity (stable `public_voice_id`) | `test_voice_split_migration`, `test_universal_voice_asset` |
| ✓ VoiceVariant Resolution | `test_variant_resolution`, `test_runtime` |
| ✓ Runtime Orchestration (single entry point) | `test_runtime`, `runtime.py` exclusivity |
| ✓ Model Registry + canonical metadata | `test_model_registry`, `test_registry_metadata` |
| ✓ Capability Contract (declared, not inferred) | `test_capabilities_contract` |
| ✓ Realization-type taxonomy (open) | `test_realization` |
| ✓ Artifact Versioning + rollback + retention | `test_artifact_repository`, `test_runtime_variant_lifecycle` |
| ✓ Variant Build Lifecycle (5-state machine) | `test_variant_lifecycle` |
| ✓ Edition Availability | `test_runtime_editions`, `test_model_availability` |
| ✓ Runtime-centric architecture (no bypass) | generation routes only through `PeakVoxRuntime` |
| ✓ Multi-provider resolution (3 adapters) | `test_multimodel_resolution`, `test_universal_voice_asset` |

### ⚠ Partially validated (real code, not fully proven end-to-end)

| Item | Why partial |
|---|---|
| ⚠ OmniVoice Base | Real inference code and the original shipping product, but **no automated end-to-end audio generation test** in the suite (needs weights + device). Treated as working-in-practice, not CI-proven. |
| ⚠ OmniVoice Singing | Shares the OmniVoice engine; catalog `status="disabled"`; singing-specific generation unverified. |
| ⚠ Model lifecycle Install/Update | State transitions, persistence, and registry sync are real and tested; the **artifact download itself is mocked**. |

### ⛔ Not yet validated (theoretical / integration-only)

| Item | State |
|---|---|
| ⛔ Fish Audio S2 Pro generation | Adapter + resolution real; `load`/`generate` raise `NotImplementedError`; speaker-embedding workflow unbuilt. |
| ⛔ Kokoro | No adapter, no catalog entry; research-only ([`12`](12-PROVIDER-VALIDATION.md) §Kokoro). |
| ⛔ Auto Routing (`model="auto"`) | Not implemented; metadata-readiness assessed in [`12`](12-PROVIDER-VALIDATION.md). |
| ⛔ Multi-provider production workloads | Never run; only OmniVoice has a real engine. |
| ⛔ Marketplace / Creator / Billing / Auth / Cloud flows | Schema-ready only (P1 seams); no implementation. |

---

## 7. Does the Universal Voice Runtime thesis survive?

**Architecturally: yes, so far.** Three structurally different providers (OmniVoice =
reference-sample, OmniVoice Singing = reference-sample + tags, Fish = speaker-embedding) plug in
through the same `ModelAdapter` contract with **zero Runtime changes**, and one
`public_voice_id` resolves to all three variants. That is the thesis, and it holds in code.

**Empirically: unproven.** The thesis claims model diversity is absorbed by the adapter seam.
That has only been tested against providers that share an engine family (OmniVoice) plus one
*stubbed* foreign provider (Fish). The real stress test — a provider that **cannot clone a voice
at all** (Kokoro: fixed preset voice packs, no reference audio) — has not been run, and it
challenges a load-bearing assumption of ADR-0008's build pipeline (that a variant is *built from
the Voice's reference audio*). See [`12-PROVIDER-VALIDATION`](12-PROVIDER-VALIDATION.md) §Kokoro.

> **The thesis is validated as an architecture and unvalidated as a production reality.** Proving
> it requires at least one *non-OmniVoice* provider generating real audio end-to-end.

---

## 8. Readiness gate (before SaaS/billing/auth)

Phase 1's stated success criterion is a *usable, stable, multi-provider CE*. Against that bar:

| Question | Answer |
|---|---|
| Which providers actually work? | OmniVoice Base (real engine). |
| Which partially work? | OmniVoice Singing (engine present, disabled/unverified). |
| Which remain theoretical? | Fish Audio S2 Pro, Kokoro. |
| Which Runtime assumptions are validated? | Resolution, capability gating, edition scoping, lifecycle, versioning. |
| Which remain untested? | Real foreign-provider inference; preset-voice (non-cloning) providers; async builds. |
| Is Fish production-viable? | Not yet — inference unwired; license is non-commercial (CE-only). |
| Is Kokoro architecture-compatible? | Format yes (`voice_pack`); build-pipeline semantics need a refinement (preset selection ≠ reference-audio build). |
| Does the thesis survive real provider diversity? | Survives in architecture; **not yet proven** against a non-cloning provider. |

**Recommendation:** Do **not** begin SaaS/billing/auth/marketplace work yet. The platform is a
single-real-provider runtime with an excellent multi-provider *architecture*. Close the gap by
running the provider validation program ([`12`](12-PROVIDER-VALIDATION.md)) on **one** real
foreign provider before investing in the Cloud ecosystem.
