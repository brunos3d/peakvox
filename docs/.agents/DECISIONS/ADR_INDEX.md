# ADR Index

> Index of all Architecture Decision Records, grouped by domain. The ADR files live in this
> directory (`DECISIONS/adr-NNNN-*.md`) — the single source of truth. ADRs are immutable once
> accepted; to change a decision, write a new ADR that supersedes the old one and link both ways.
>
> Status here = the ADR's own status. **Implementation status is tracked separately** in
> [`../IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md) — an Accepted ADR is **not** proof
> the feature is built.

New ADRs follow the naming convention `adr-NNNN-kebab-case.md`. Template:
[`adr-template.md`](adr-template.md).

---

## Domain: Voice & Identity

| ADR | Title | Status | Impl. |
|---|---|---|---|
| [0001](adr-0001-voice-variant-split.md) | Voice / VoiceVariant split as the core domain spine | Accepted | IMPLEMENTED |
| [0004](adr-0004-voice-variant-model-separation.md) | Voice, VoiceVariant, and Model are three separate concepts | Accepted | IMPLEMENTED |
| [0006](adr-0006-voice-variant-realization-types.md) | Voice Variant Realization Types (open taxonomy) | Accepted | IMPLEMENTED (status values superseded by 0008) |
| [0011](adr-0011-voice-creation-sources.md) | Voice Creation Sources (generalizes 0010; Source Asset = one origin type) | Accepted (architecture only) | APPROVED |

- **0001** — split identity (Voice) from realization (VoiceVariant); `public_voice_id` permanent.
- **0004** — the binding three-concept separation; variants never on the public API.
- **0006** — realization is an open type taxonomy; orthogonal to creation source.
- **0011** — a voice's origin is a Creation Source (asset/preset/…), not always a WAV.

## Domain: Provisioning & Build Lifecycle

| ADR | Title | Status | Impl. |
|---|---|---|---|
| [0008](adr-0008-voice-variant-build-lifecycle.md) | Voice Variant Build Lifecycle | Accepted (**supersedes ADR-0006** status values) | IMPLEMENTED (sync builds) |
| [0009](adr-0009-artifact-versioning-and-retention.md) | Artifact Versioning and Retention | Accepted | IMPLEMENTED |
| [0010](adr-0010-voice-source-assets-and-automatic-variant-provisioning.md) | Voice Source Assets + Automatic Variant Provisioning (extends 0006/0008/0009) | Accepted (architecture only) | APPROVED |

- **0008** — the 5-state variant build machine; Runtime owns build/rebuild/ensure_variant.
- **0009** — versioned artifacts with rollback + CE retention.
- **0010** — variants are provisioned from a Source Asset; extended (not superseded) by 0011.

## Domain: Model & Provider

| ADR | Title | Status | Impl. |
|---|---|---|---|
| [0002](adr-0002-model-as-first-class-entity.md) | Model as a first-class persisted entity | Accepted | IMPLEMENTED |
| [0003](adr-0003-model-capability-contract.md) | Model Capability Contract | Accepted | IMPLEMENTED |
| [0007](adr-0007-canonical-model-metadata.md) | Canonical Model Metadata Registry | Accepted | IMPLEMENTED |

- **0002** — Model is a persisted, lifecycle-managed entity.
- **0003** — capabilities are declared (`ModelCapabilities`), never inferred from id/name.
  (`supports_emotion_tags` supersedes legacy `supports_emotions`.)
- **0007** — provider-backed metadata is normalized once into the registry.

## Domain: Editions & Licensing

| ADR | Title | Status | Impl. |
|---|---|---|---|
| [0005](adr-0005-edition-scoped-model-availability.md) | Edition-scoped model availability (licensing-governed) | Accepted | IMPLEMENTED |

- **0005** — a model's editions are a declared property; CE vs Cloud availability is data, not a
  code branch.

## Domain: Voice Identity & Catalog Separation

| ADR | Title | Status | Impl. |
|---|---|---|---|
| [0012](adr-0012-voice-identity-vs-catalog-resources.md) | Voice Identity vs Catalog Resources | Accepted | APPROVED |

- **0012** — Catalog resources (ProviderPreset, MarketplaceListing) are transient descriptors; they become Voices only at user import. Introduces `VoiceResource` (transient API type), `VoicePreview` (first-class preview entity), and `VariantBuildStrategy` (explicit compatibility).

## Domain: Runtime Infrastructure

| ADR | Title | Status | Impl. |
|---|---|---|---|
| [0016](adr-0016-models-as-runtime-services.md) | Models as Runtime Services | Accepted (forbidden-pattern clause **amended by 0018**) | APPROVED |
| [0017](adr-0017-runtime-services-implementation.md) | Runtime Services Implementation (Phase 2 Implementation ADR) | Accepted | APPROVED |
| [0018](adr-0018-runtime-variants-architecture.md) | Runtime Variants Architecture (Runtime + RuntimeVariants, not runtime-per-variant) | Accepted (architecture only) | PARTIAL (Phase 0 primitive IMPLEMENTED) |

- **0016** — Models evolve from "Python package in the backend process" to "Runtime Service reachable over a stable contract." Introduces Runtime Registry (declarative catalog of `runtime.yaml` descriptors), Runtime Manager (orchestration-only; never executes inference), and Runtime Driver (substrate abstraction with `DockerRuntimeDriver` as the first implementation; Kubernetes, Podman, LocalProcess drivers are future). Adapters become protocol translators. **Critical distinction:** PeakVox installs *runtimes*, not models. One Model → many Runtimes (CUDA / CPU / local / cloud). The Active Artifact resolution step (ADR-0009) is preserved and may not be bypassed. Runtime infrastructure is *not* a domain concept; forbidden future patterns include `RuntimeServiceEntity`, `RuntimeServiceRepository`, `RuntimeVariant`, `RuntimeArtifact`. 7-phase migration: ADR + design (this) → Runtime Manager skeleton (P2) → Kokoro (P3) → F5-TTS reference (P4) → Fish (P5) → OmniVoice (P6) → remove in-process path (P7). See [`../SPECS/FEATURES/models-as-runtime-services/`](../SPECS/FEATURES/models-as-runtime-services/).
- **0017** — Phase 2 implementation architecture. Specifies the 10 deliverables that ADR-0016 deferred: `RuntimeDescriptor` (schema, identity, metadata, versioning, capabilities, requirements), `RuntimeRegistry` (file-based discovery + indexes), `RuntimeManager` (orchestration + resolution flows; canonical 4-owns/5-does-NOT from ADR-0016), `RuntimeDriver` (formal `Protocol` with 10 operations + 8 error categories + retry/timeout policy), `DockerRuntimeDriver` (first concrete driver; boundaries on K8s/Podman/remote hosts), the Runtime Service Contract (5 HTTP/JSON endpoints: `/health`, `/ready`, `POST /v1/generate`, `POST /v1/variants/build`, `GET /v1/metadata`; canonical error body), the complete routing flow (12 steps with a failure matrix), the Kokoro migration (4-step additive rollout + declarative rollback via `KOKORO_RUNTIME_URL`), and the CE/Cloud operations (install/activate/update/remove). Resolves the 5 deferred open questions from [`OPEN_DECISIONS.md` Decision 10](../OPEN_DECISIONS.md): endpoint discovery = `RuntimeManager.resolve`; upgrade/rollback = versioned images + `spec.image.digest`; GPU = Runtime Service owns it; health = liveness vs readiness with readiness = "can serve inference"; auth = CE default none, Cloud deferred. Phase 2 implementation is gated on this ADR's accept; sub-phases 2A (foundations) → 2B (Docker driver) → 2C (Kokoro integration) → 2D (CE operations). See [`../SPECS/FEATURES/runtime-services-implementation/`](../SPECS/FEATURES/runtime-services-implementation/).
- **0018** — evolves the Runtime Registry from **runtime-per-variant** to
  **Runtime + RuntimeVariants**. Introduces `RuntimeVariant` as an
  *infrastructure descriptor concept* (Runtime × Checkpoint realization) — a
  `variants/<id>.json` sub-descriptor binding a checkpoint to a runtime,
  **never** a domain entity, **never** on the public API, and rigorously
  distinct from the domain `VoiceVariant` (Voice × Model). One runtime image
  hosts many interchangeable checkpoints (download-only adds), collapsing
  storage from N×image to 1 image + N checkpoints. Enables CE "Add Variant"
  without Docker, Hugging Face checkpoint imports, and a variant marketplace.
  **Amends ADR-0016**'s forbidden-pattern entry for `RuntimeVariant`: narrows
  it to permit the infrastructure-descriptor form while keeping the domain
  entity/repository prohibition (all other ADR-0016 invariants stand). Public
  API unchanged (Model stays the selector; `resolve(model_id)` picks runtime +
  variant). Architecture only; ships a non-wired additive descriptor primitive
  (Phase 0). 6-phase additive migration. See
  [`../SPECS/FEATURES/runtime-variants/`](../SPECS/FEATURES/runtime-variants/),
  [`../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md`](../IMPLEMENTATION/PLANS/2026-06-11-runtime-variants-migration.md),
  [`../VALIDATION/AUDITS/runtime-variants-assumptions-audit.md`](../VALIDATION/AUDITS/runtime-variants-assumptions-audit.md).

## Reserved / future ADRs (write when the decision is actually made)

These are tracked as live questions in [`../OPEN_DECISIONS.md`](../OPEN_DECISIONS.md):

- **ADR-0013** — Model Categories (cloning vs preset vs training) — reserved by 0011.
- **ADR-0014** — Marketplace Voice Publishing — reserved by 0011.
- **ADR-0015** — Imported Voice Ecosystem — reserved by 0011.
- Auth vendor adapter (Clerk) + `AuthProvider` seam.
- Payments/payouts vendor (Stripe + Connect) + provider seams.
- SQLite→Postgres cut-over + Alembic adoption.
- pgvector reconsideration (current verdict: NO).
- Marketplace search backend (Postgres FTS vs external index).
- Runtime endpoint discovery + GPU allocation + runtime health contract + backend-to-runtime auth (deferred open questions from ADR-0016 Phase 1; addressed by the Phase 2 implementation ADR).
- `KubernetesRuntimeDriver` / `PodmanRuntimeDriver` / `LocalProcessDriver` (deferred; will land as separate ADRs when their respective editions begin).

## Supersession map

```
ADR-0006 (status values) ──superseded by──▶ ADR-0008
ADR-0010 ──generalized/extended by──▶ ADR-0011   (0010 NOT superseded; one origin type among many)
ADR-0016 (RuntimeVariant forbidden-pattern entry) ──amended by──▶ ADR-0018
          (0016 NOT superseded; only the one clause is narrowed; invariants 1–12 stand)
```

---

**Related:** [`../CONSTITUTION.md`](../CONSTITUTION.md) · [`../IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md) ·
[`../ARCHITECTURE/ARCHITECTURE_MAP.md`](../ARCHITECTURE/architecture-map.md)
