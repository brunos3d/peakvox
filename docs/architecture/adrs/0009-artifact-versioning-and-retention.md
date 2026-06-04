# ADR-0009: Artifact Versioning and Retention

- **Status:** Accepted — Implemented (P3.11)
- **Date:** 2026-06-04
- **Deciders:** Bruno Silva (product owner), architecture planning
- **Extended by:** [ADR-0010](0010-voice-source-assets-and-automatic-variant-provisioning.md) —
  every artifact version rebuilds from the **Voice Source Asset** (the canonical source of truth),
  never from a prior artifact or another variant, preserving reproducibility and portability.
- **Implementation:** `voice_variant_artifacts` table + `voice_variants.active_artifact_id`
  (`app/models/db.py`); additive backfill migration (`app/core/migrations.py`);
  `app/services/voice_variant_artifact_repository.py` (append / active pointer / list / rollback /
  prune); `PeakVoxRuntime.get_active_artifact / list_artifact_versions / rollback_artifact /
  prune_artifacts`; `ARTIFACT_RETENTION_COUNT` setting. Default = **pin-by-variant** (no
  `generation_jobs` schema change); pin-by-artifact-version remains the Cloud extension.

## Context

[ADR-0008](0008-voice-variant-build-lifecycle.md) introduced the Voice Variant Build Lifecycle:
a variant transitions through `pending → building → ready | failed | deprecated`, and a
`rebuild_variant()` operation replaces the variant's artifact with a new one.

However, the architecture does not currently define what happens to the **previous** artifact
when a rebuild occurs:

- Is it replaced? Retained? Versioned?
- Can generation jobs that used the old artifact be reproduced?
- Can the system roll back to a prior artifact if a new build fails in production?
- How long are old artifacts kept?
- What happens during automatic model-upgrade-triggered rebuilds?

These questions affect every future layer: marketplace reproducibility, Cloud retention
guarantees, creator rollback support, and production debugging.

The current data model stores artifact references as a JSON blob on `voice_variants.artifacts`
([Data §3.3](../03-DATA_ARCHITECTURE.md)). This single-value approach cannot represent
version histories, cannot support retention policies, and cannot anchor audit/reproducibility
chains.

Three architectural invariants must be preserved ([ADR-0004](0004-voice-variant-model-separation.md),
[ADR-0008](0008-voice-variant-build-lifecycle.md)):

1. **Voice ID** is permanent and model-independent.
2. **VoiceVariant** (`voice_id × model_id`) is the stable realization identity.
3. **Artifact** is the provider-specific runtime asset produced by a build — this is the layer
   that now must be versioned.

## Options considered

### A. Inline versioned JSON on `voice_variants.artifacts`

Keep artifacts as a JSON column on the variant row. Add version tracking inside the JSON
(e.g. `{ "versions": [{ "v": 1, "keys": {...} }, { "v": 2, "keys": {...} }], "active": 2 }`).

- **Pro:** Minimal schema change; no new table; current code paths mostly unchanged.
- **Con:** JSON grows unboundedly with rebuilds; no referential integrity; retention policy
  enforcement requires parsing/rewriting JSON; no foreign-key targets for generation jobs to
  pin; querying "which generation used artifact v1" requires scanning generation_jobs JSON.
  Not suitable for Cloud marketplace requirements.
- **Verdict:** Acceptable for early CE prototyping. Rejected as the long-term architecture.

### B. Separate `voice_variant_artifacts` table with explicit version rows

A new table keyed to `voice_variants`. Each rebuild appends a row. The variant row holds a
reference (FK or version-number pointer) to the currently active artifact version.

- **Pro:** Full audit trail; every artifact version is a queryable row; generation jobs can
  FK-reference an artifact version for reproducibility; retention policies map to SQL
  (`DELETE WHERE version < N AND created_at < cutoff`); Cloud and CE share the same schema;
  rollback is an UPDATE to the variant's active-artifact pointer.
- **Con:** More schema surface; write path must append a row on every build; storage paths
  must include the version number; migration from inline JSON required.
- **Verdict:** **Chosen** — the architectural foundation that preserves reproducibility,
  rollback, retention, and marketplace guarantees.

### C. Content-addressed storage (artifact key = content hash)

Artifacts are stored at paths derived from their content hash. Versioning is implicit — each
hash is a unique, immutable artifact. The variant points to the current hash; old hashes remain
accessible as long as the storage backend retains them.

- **Pro:** Self-validating artifacts (tamper detection); deduplication (identical artifacts
  share storage); immutable by construction.
- **Con:** No natural ordering (versions must be tracked separately); GC complexity (which
  hashes are still referenced?); rollback requires remembering the prior hash; adds
  indirection without solving the core tracking problem that Option B solves directly.
- **Verdict:** Rejected for the versioning layer. Content addressing can be added **as a
  storage strategy** within Option B (the `voice_variant_artifacts.storage_hash` column stores
  the content hash; the storage layer is free to deduplicate by it). The versioning architecture
  and the storage strategy are orthogonal.

## Decision

Adopt **Option B**. Artifact versions are first-class rows in a
`voice_variant_artifacts` table. The variant's active artifact is a pointer into that table.

### 1. Conceptual model

```
Voice               (permanent identity)
  └── VoiceVariant  (voice_id × model_id — stable realization identity)
        ├── active artifact version  (the one the Runtime resolves)
        └── artifact versions  (ordered historical rows)
              ├── v1  (created 2026-06-01)
              ├── v2  (created 2026-06-15, active)
              ├── v3  (created 2026-06-20, rolled back)
              └── v4  (created 2026-06-22, active — after rollback + rebuild)
```

The VoiceVariant is the stable public concept. Artifact versions are an internal tracking
detail, never exposed on the public API surface without being folded into a versioned artifact
reference.

### 2. Active artifact definition

Every VoiceVariant has exactly **one active artifact version** at any time — the one the
Runtime resolves when `ensure_variant()` succeeds.

- `active_artifact_id` (FK → `voice_variant_artifacts.id`) is stored on the variant row.
- The Runtime's generation pipeline resolves `Voice → Variant → active artifact → inference`.
- Previous artifact versions are retained according to policy but are **not** used for
  generation unless explicitly rolled back.

### 3. Rebuild semantics

When `rebuild_variant()` executes:

```
1. Variant status → building
2. Adapter.build_variant() produces a new artifact
3. New row appended to voice_variant_artifacts (version N+1)
4. Variant.active_artifact_id → new artifact row's id
5. Previous artifact (N) is retained (not deleted)
6. Variant status → ready
```

The previous artifact is immediately available for rollback. No data is destroyed on rebuild.

### 4. Rollback strategy

A rollback is conceptually supported without requiring a new build:

```
rollback_artifact(voice_id, model_id, target_version)
  → sets variant.active_artifact_id = target artifact row's id
  → variant remains ready
```

Constraints:
- Target version must exist and belong to the same variant.
- Rollback does **not** change artifact data — it only changes the active pointer.
- Rollback is **not** a rebuild. To get a new artifact based on current inputs (not a prior
  one), use `rebuild_variant()`.
- Rollback across variant deprecation boundaries is allowed (a user may roll back to a prior,
  pre-deprecation artifact while a rebuild is being prepared).

This capability is **declared architecturally but not exposed as a public API** in the initial
implementation. CE exposes it only through direct DB/shell access. Cloud may surface it as a
creator/operator action.

### 5. Generation reproducibility

Two approaches for anchoring generation jobs to artifacts:

**Pin-by-variant** (simpler, default for CE):
- `generation_jobs` references `voice_variant_id` only.
- The artifact version in effect at generation time is resolved historically by joining on
  `voice_variant_artifacts` with `created_at <= generation_jobs.created_at` and ordering by
  version descending.
- Reproducible as long as artifact versions are retained (which they are, per policy).
- No schema change to `generation_jobs`.

**Pin-by-artifact-version** (stronger guarantees, Cloud / marketplace):
- `generation_jobs` adds an optional `artifact_version_id` FK.
- The generation record **pins exactly which artifact was used**.
- Full reproducibility even after retention pruning (if the row is retained, the artifact
  version is known, even if the storage has been pruned — fallback to "artifact no longer
  available" is a known, graceful state).
- Required for marketplace-grade auditing.

This ADR recommends **pin-by-variant** as the default (no schema change to generation_jobs),
with **pin-by-artifact-version** as an additive Cloud extension. The data model must support
both — the `voice_variant_artifacts` table enables either approach.

### 6. Storage retention

**Community Edition (CE):**

| Policy | Default | Configurable? |
|---|---|---|
| Keep active artifact | Always | — |
| Keep N most recent versions | N=3 | Yes (env `ARTIFACT_RETENTION_COUNT`) |
| Pruning trigger | On rebuild or manual prune | — |
| Pruning behavior | DELETE rows + storage files beyond retention count | — |

CE retains the active artifact plus the last N versions by default, ensuring rollback is
possible for recent changes without unbounded storage growth.

**Cloud:**

| Policy | Default | Configurable? |
|---|---|---|
| Keep active artifact | Always | — |
| Keep all versions | Indefinitely for marketplace-listed voices | Per-creator/listing |
| Pruning trigger | Retention job (scheduled) | — |
| Marketplace-grade retention | All versions kept while voice is listed | Automatic |
| Post-unlisting grace | Versions kept for 90 days after delisting | Configurable |

Cloud retains all artifact versions for marketplace voices to guarantee reproducibility of past
generations (royalty computation, audit, dispute resolution). For non-marketplace voices, a
configurable retention window applies.

**Pruning safety:**
- The active artifact is **never** pruned.
- A version referenced by any `generation_jobs.artifact_version_id` (Cloud, optional) is
  preserved until all referencing jobs reach a configurable age.
- Pruning deletes the DB row **and** the storage files; the operation is irreversible.

### 7. Model upgrade impact

When `model.version` changes (or the model is updated via `update_model()`):

1. Existing variants for that model are marked `deprecated` ([ADR-0008](0008-voice-variant-build-lifecycle.md)).
2. A rebuild is triggered (implicitly or explicitly).
3. The rebuild produces a **new artifact version** (N+1) under the **same variant**.
4. The old artifact version remains accessible (rollback, comparison).
5. The artifact version record stores `model_version` at time of build, enabling queries like
   "which model version produced this artifact?"

The user can:
- Accept the new artifact (automatic — it becomes active on rebuild completion).
- Roll back to the pre-upgrade artifact (old model version's output still available).
- Explicitly rebuild LATER (variant stays deprecated until rebuild).

### 8. Marketplace implications

The minimum auditable chain for marketplace voices:

```
Voice
  └── VoiceVariant
        └── Artifact Version  ←  referenced by GenerationJob
```

This chain guarantees:
- **Reproducibility:** a past generation can be traced to the exact artifact version used.
- **Trust:** a creator cannot silently change a voice's output after a user has generated with
  it (the old artifact version remains; the new one is a separate version).
- **Rollback:** if a rebuild degrades quality, marketplace users can be migrated back to the
  prior artifact version (or offered a choice).
- **Royalty audit:** each generation is pinned to the artifact version that produced it,
  removing ambiguity about which "version" of a voice was used.

Marketplace listing metadata should expose artifact version count and last-build timestamp
as quality signals, without exposing artifact internals.

### 9. Runtime responsibilities (extended)

The Runtime gains artifact version awareness:

```python
# Existing (ADR-0008):
build_variant(voice, model)          → job_id
rebuild_variant(voice, model)        → job_id  (appends artifact vN+1)
get_variant_status(voice, model)     → state
ensure_variant(voice, model)         → ready variant (resolves active artifact)

# New (artifact versioning):
get_active_artifact(voice, model)    → current active artifact version metadata
list_artifact_versions(voice, model) → ordered list of version metadata
rollback_artifact(voice, model, version)  → sets active pointer (no rebuild)
prune_artifacts(voice, model)        → enforce retention policy (CE: prune oldest)
```

The Runtime's resolution flow (ADR-0008 §Runtime resolution flow) gains an explicit artifact
version resolution step:

```
ensure_variant(voice, model)
  └── variant ready → resolve active artifact version
                       └── return variant + active artifact metadata
```

The adapter interface is **not** changed — `adapter.build_variant()` still produces a single
artifact. Versioning is a Runtime + Data concern above the adapter line.

### 10. Data architecture impact

A new table is conceptually required:

```
voice_variant_artifacts
├── id                      str(36) PK
├── voice_variant_id        str(36) FK → voice_variants.id  (non-null)
├── version                 int     (monotonic per variant, starting at 1)
├── storage_keys            JSON    (same shape as current voice_variants.artifacts)
├── storage_hash            str?    (content hash for dedup / integrity — optional)
├── size_bytes              int?    (total artifact size)
├── model_version           str?    (model version at build time — from models table)
├── checksum                str?    (for integrity verification)
├── metadata                JSON?   (build params, adapter-specific info)
├── created_at              datetime
└── retained_until          datetime?  (null = indefinite — active artifact, marketplace voice)
```

The `voice_variants` table gains:

```
voice_variants
├── ...existing columns...
└── active_artifact_id  str(36)?  FK → voice_variant_artifacts.id  (NULL when pending/failed)
```

**Constraint:** `UNIQUE(voice_variant_id, version)` ensures artifact versions are sequential
per variant. Storage paths move to:
`/data/voices/{voice_id}/variants/{model_id}/v{version}/{filename}`.

The `artifacts` column on `voice_variants` is **deprecated** once the migration to the new
table is complete. During transition, both locations may hold data (dual-write).

### 11. Migration approach

Existing variants with inline `voice_variants.artifacts` data (from the pre-ADR-0009 schema)
are migrated as follows:

1. Read the existing `artifacts` JSON from `voice_variants`.
2. Create a `voice_variant_artifacts` row with `version=1`, `storage_keys` = the existing
   JSON content.
3. Set `voice_variants.active_artifact_id` to the new row's id.
4. The existing storage files are already at the correct path (`/data/voices/{id}/variants/{model_id}/…`);
   the version component is added only for future rebuilds.

This is a one-time, additive migration. No data is moved or reformatted.

## Consequences

- **Positive:**
  - Every artifact version is a tracked, queryable row — not a lost mutation.
  - Rollback is a metadata pointer change, not a storage operation.
  - Generation reproducibility is supported at two levels (variant-pin and artifact-pin).
  - CE and Cloud share the same schema; Cloud adds stricter retention + marketplace-grade
    audit.
  - Model upgrades produce new artifact versions without destroying old ones.
  - Marketplace audit chain is structurally complete: Voice → Variant → Artifact Version →
    Generation.
  - The adapter contract is untouched — versioning is entirely above the adapter line.
  - Retention policies are declarative and edition-appropriate.

- **Negative / costs:**
  - New `voice_variant_artifacts` table adds schema surface and a write path on every build.
  - Storage paths must include the version number (backward-compatible — existing artifacts
    use `v1`).
  - The `voice_variants.active_artifact_id` pointer requires migration from existing
    inline artifacts.
  - Pruning requires care: never delete the active version, and in Cloud, never delete
    versions referenced by marketplace-eligible generation jobs.
  - The inline `voice_variants.artifacts` column must be maintained as a deprecated dual-write
    target during migration, then removed after all consumers switch to the new table.

- **Follow-ups:**
  - ADR-0009 builds directly on ADR-0008 (variant build lifecycle). Without rebuilds, there
    are no artifact versions to track.
  - The new table joins the schema-ready commercial tables — created in CE by the migration
    runner, populated by the Runtime on every build.
  - Implementation should add the table + migration as part of the ADR-0008 implementation
    phase (variant build lifecycle + artifact versioning are a single delivery).
  - Future: artifact version retention can be extended with warm/cold storage tiers (Cloud)
    or selective archival (marketplace voice preservation after delisting).
  - Future: the `storage_hash` column enables content-addressed storage deduplication as a
    storage-layer optimization, independent of the versioning architecture.
