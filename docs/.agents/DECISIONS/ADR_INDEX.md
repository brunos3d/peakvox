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

## Supersession map

```
ADR-0006 (status values) ──superseded by──▶ ADR-0008
ADR-0010 ──generalized/extended by──▶ ADR-0011   (0010 NOT superseded; one origin type among many)
```

---

**Related:** [`../CONSTITUTION.md`](../CONSTITUTION.md) · [`../IMPLEMENTATION_STATUS.md`](../IMPLEMENTATION_STATUS.md) ·
[`../ARCHITECTURE/ARCHITECTURE_MAP.md`](../ARCHITECTURE/architecture-map.md)
