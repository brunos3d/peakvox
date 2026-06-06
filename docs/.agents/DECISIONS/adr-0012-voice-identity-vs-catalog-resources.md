# ADR-0012: Voice Identity vs Catalog Resources

**Status:** Accepted
**Date:** 2026-06-06
**Deciders:** Architecture Team
**Supersedes:** (reserved slot ADR-0012 re-purposed; see Consequences)

---

## Context

The platform now hosts two fundamentally different categories of entities that are currently fused into a single model:

1. **Catalog resources** — voice-like entities that exist in provider registries, marketplace listings, or import sources. They have metadata (name, language, provider) but lack user ownership, a stable public identity, variants, or lifecycle.
2. **Library voices** — persisted `Voice` entities in the user's library with a stable `public_voice_id`, ownership, per-model variants, artifact versioning, and a full lifecycle.

Today, `POST /voices/from-preset` bypasses this distinction entirely: a provider preset descriptor is immediately materialized as a full `Voice` with variants and artifacts. This works for the current small scale but breaks down when:

- Browsing a marketplace with 10,000 listings (each should not create a DB Voice)
- Previewing provider presets without committing them to the library
- Supporting "temporary" or "trial" voices
- Modeling the catalog/library boundary for future resource types (imported, generated, marketplace)

Additionally, six recent bugs — broken play button, preset appearing as cloned voice, Infinity durations, AbortError, missing previews, incorrect filtering — all trace back to the same root cause: **catalog resources and library voices are treated identically**.

---

## Definitions

### CatalogPreset

A **CatalogPreset** is a voice-like descriptor that exists _before_ entering a user's library. It is a pure data object with metadata about a voice resource that _could_ become a Voice.

| Property | Source | Example |
|----------|--------|---------|
| `preset_id` | Provider registry | `"kokoro:pm_alex"` |
| `provider` | Provider metadata | `"kokoro"` |
| `name` | Provider metadata | `"Bella"` |
| `language` | Provider metadata | `"pt"` |
| `gender` | Provider metadata | `"F"` |
| `preview_audio` | Provider provides or null | `null` or URL |
| `is_default` | Provider metadata | `false` |
| `model_id` | Which model realizes this | `"kokoro-base"` |

CatalogPresets live in provider adapter code (`KokoroAdapter.list_provider_voices()`) or in marketplace listing data. They are **never** stored in the Voice table.

### MarketplaceListing

A **MarketplaceListing** is a catalog resource in a marketplace catalog. It has richer metadata including creator info, pricing, ratings, sample previews, and associated pre-built variants.

MarketplaceListings live in the marketplace catalog tables (exist in schema, populated only in Cloud edition). They are **never** stored in the Voice table until purchased/imported.

### Voice

A **Voice** is a first-class, persisted, model-agnostic identity in the user's library. It has:

- `public_voice_id` — a stable, immutable public identifier (ADR-0001)
- `owner_id` — user ownership (ADR-0004)
- `creation_source` — how this Voice came to exist (ADR-0011)
- One or more `VoiceVariant` records — per-model realizations (ADR-0001, ADR-0008)
- Zero or more `VoiceSourceAsset` records — source audio (ADR-0010)
- Zero or more `VoicePreview` records — preview audio (see below)

A Voice is created at the moment a catalog resource crosses into the user's library: "Add to Library," "Purchase," "Import," "Clone."

### VoiceVariant

A **VoiceVariant** is a per-model realization of a Voice (ADR-0001, ADR-0004). Keyed on `(voice_id, model_id)`. Has a lifecycle of `pending → building → ready | failed | deprecated` (ADR-0008).

### VoiceVariantArtifact

A **VoiceVariantArtifact** is a versioned build output of a VoiceVariant (ADR-0009). Each rebuild appends a new version.

### VoiceSourceAsset

A **VoiceSourceAsset** is the canonical source material for a Voice (ADR-0010, creation_source = `SOURCE_ASSET`). The original user-provided audio. Not all Voices have source assets.

### VoicePreview

A **VoicePreview** is an audio sample associated with a Voice for UI playback. A Voice may have zero, one, or many Previews.

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `voice_id` | FK → Voice | Which Voice this preview belongs to |
| `preview_origin` | enum | `reference`, `generated`, `provider`, `user`, `marketplace` |
| `language` | str or null | Language of this specific preview |
| `source_model_id` | str or null | Which model generated this preview (null for reference/provider) |
| `storage_key` | str | Storage path to audio |
| `duration` | float | Audio duration in seconds |
| `created_at` | datetime | When this preview was created |

Previews are separate from Voice source assets because:
- A preview can be generated (not source audio)
- A preview can exist in multiple languages for the same Voice
- A preview can be regenerated, cached, or replaced without affecting the source asset

---

## The Boundary

**A catalog resource becomes a Voice at the moment of user intent:**

| Catalog Type | User Action | Results In | creation_source |
|-------------|-------------|------------|-----------------|
| ProviderPreset | "Add to Library" | Voice + VoiceVariant + Artifact | `PRESET_VOICE` |
| MarketplaceListing | "Purchase" / "Add" | Voice + VoiceVariants + Artifacts | `MARKETPLACE_VOICE` |
| ImportedResource | "Import" | Voice + VoiceSourceAsset | `IMPORTED_VOICE` |
| _(no catalog resource — created directly)_ | "Clone (upload audio)" | Voice + VoiceSourceAsset + Variants | `SOURCE_ASSET` |

Before the boundary crossing, the entity is a catalog descriptor. After, it is a Voice with all the rights and responsibilities of a library entity:

- **Before:** No `public_voice_id`, no variants, no artifacts, no ownership, no lifecycle, no preview persistence.
- **After:** Has `public_voice_id`, has variants, has artifacts, has ownership, has lifecycle, can have persisted previews.

---

## Architectural Consequences

### VoiceResource Catalog Abstraction

To represent catalog-level entities without prematurely creating Voices, introduce `VoiceResource` as a transient, API-facing type. NOT a database entity.

```typescript
interface VoiceResource {
  id: string;                    // catalog-level ID (provider:preset, marketplace:listing, etc.)
  resource_type: "preset" | "marketplace" | "imported" | "generated";
  name: string;
  description: string | null;
  language: string | null;
  previews: VoicePreviewDescriptor[];
  provider_metadata: Record<string, any>;
  compatible_models: string[];   // which models can realize this
  is_in_library: boolean;        // has this been imported as a Voice?
  library_voice_id: string | null; // if is_in_library, points to the Voice
}
```

`VoiceResource` is never stored in the DB. It is constructed at query time from:
- Provider adapter registries (`list_provider_voices()`)
- Marketplace listing tables
- Import source data

The API returns `GET /voice-resources` for the unified catalog view (browsing presets + marketplace + imports). The user's library is `GET /voices`.

### Preview Architecture

Replace the single `preview_audio` column on `Voice` with a separate `VoicePreview` entity. This enables:

- Zero previews: newly created presets without samples
- One preview: most cloned voices
- Many previews: multi-language samples for a single Voice
- Provider-supplied previews: Kokoro presets with bundled samples
- Generated previews: auto-generated samples from a model
- Cached previews: regenerated on demand, cached for reuse

### Compatibility Resolution via BuildStrategy

Replace capability-based compatibility inference (`supports_voice_cloning = true`) with explicit `VariantBuildStrategy`. Each adapter declares for which creation sources it can build variants:

```python
class VariantBuildStrategy:
    creation_source: str
    can_build: bool
    requires: list[str]  # e.g., ["source_asset"], ["preset_params"]
    build_fn: str | None  # adapter method if can_build
```

Compatibility rule:

```
A voice is compatible with a model IF:
  (a) a ready VoiceVariant exists for (voice, model), OR
  (b) the model's adapter declares a VariantBuildStrategy
      for the voice's creation_source with can_build=True AND
      the required preconditions are met.
```

This is strictly more precise than `supports_voice_cloning` because:
- A model may support cloning but lack a pipeline implementation
- A model may support multiple creation sources with different requirements
- The build preconditions are explicit and checkable

### Preview Origin Derivation

`preview_origin` is derived at read time. Not stored.

```python
def derive_preview_summary(previews: list[VoicePreview]) -> PreviewSummary:
    if not previews:
        return PreviewSummary(origin="none", reason="No preview available")
    for pref in ["reference", "generated", "provider", "user", "marketplace"]:
        for p in previews:
            if p.preview_origin == pref:
                return PreviewSummary(
                    origin=pref,
                    count=len(previews),
                    languages=[p.language for p in previews if p.language],
                )
    return PreviewSummary(origin="none", reason="No playable preview found")
```

---

## Options Considered

### Option A: Keep the fused model (current state)

Treat all voice-like entities as Voices from their first appearance.

**Pros:** Simple, no new abstractions, minimal code change.
**Cons:** Cannot distinguish "browsing" from "owning"; marketplace browsing creates DB noise; cannot model preview state for catalog items; bugs from treating presets as cloned voices are architectural, not incidental.

### Option B: VoiceResource as first-class DB entity

Create a `voice_resources` table for catalog items, separate from `voices`.

**Pros:** Clean separation, transactional, queryable.
**Cons:** Synchronization problem between catalog and library; two parallel identity systems; marketplace listings already have their own tables; overengineered for current needs.

### Option C: VoiceResource as transient API type (SELECTED)

Keep catalog resources as transient descriptors (not stored). Use `VoicePreview` as a first-class DB entity on Voice. Cross the catalog→library boundary only at user intent.

**Pros:** No synchronization problem; no new identity system; catalog resources are already transient in provider registries; minimal new infrastructure; the boundary is explicit and enforced by the type system.
**Cons:** Requires a mental model shift; catalog browsing needs a different API path than library browsing.

---

## Consequences

**Positive:**
- Six classes of UI bugs (play button, Infinity, presets as clones, etc.) have an architectural fix: the UI must check entity type before assuming behavior.
- Catalog scalability: browsing 10,000 marketplace listings does not create 10,000 Voice rows.
- Preview evolution: multi-preview, per-language previews, cached previews are all supported cleanly.
- The library/catalog boundary is explicit and testable.
- Marketplace integration is natural: browse catalog → acquire → becomes Voice.

**Negative:**
- Existing `POST /voices/from-preset` flow must be revisited: the preset descriptor should remain a `VoiceResource` until the user explicitly adds it to their library.
- The UI needs two data sources: voice resources (catalog) and voices (library) — but only for the "Browse" feature, which is a future addition.
- Preview migration: existing `preview_audio` column on Voice needs to become a VoicePreview record.

**Clarification — SOURCE_ASSET creation path:**
`SOURCE_ASSET` voices (cloned from uploaded audio) are created directly via `POST /voices` with an audio file upload. They do NOT pass through a `VoiceResource` catalog stage. The user's audio file is input, not a catalog item. There is no "import from catalog" step for cloned voices — the Voice is created at the moment of upload.

**Supersession note:**
This ADR re-purposes the previously reserved ADR-0012 slot (which was titled "Variant Provisioning Policies"). The variant provisioning policies that were reserved for ADR-0012 are now captured in the `VariantBuildStrategy` concept within this ADR. If a dedicated ADR is needed later for provisioning policy elaboration, it will be ADR-0016 or higher.

**Reserved ADRs shifted:**
- ADR-0013 (was "Model Categories") — unchanged reservation
- ADR-0014 (was "Marketplace Voice Publishing") — unchanged reservation
- ADR-0015 (was "Imported Voice Ecosystem") — unchanged reservation

**File locations affected:**
- `docs/.agents/DECISIONS/ADR_INDEX.md` — update ADR-0012 entry
- `docs/.agents/DECISIONS/adr-0008.md` — no change needed (build lifecycle is compatible)
- `docs/.agents/DECISIONS/adr-0011.md` — no change needed (creation sources remain the taxonomy)
- `docs/.agents/SPECS/FEATURES/peakvox-voice-system-evolution/` — all documents reference this ADR

**Related ADRs:**
- ADR-0001: Voice/VoiceVariant split (foundation for Voice identity)
- ADR-0004: Three-way separation (Voice ≠ Variant ≠ Model)
- ADR-0008: Variant build lifecycle (compatible with BuildStrategy)
- ADR-0010: Source assets (SOURCE_ASSET specialization)
- ADR-0011: Creation sources (taxonomy for origins)
