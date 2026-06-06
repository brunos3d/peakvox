# PeakVox Voice System Evolution — Refined Architecture Specification

> **Status:** REFINED
> **Date:** 2026-06-06
> **Context:** Second architecture pass after review. The first pass (SPEC v1) identified frontend gaps. This pass corrects conceptual errors: `settings_schema` replaces persisted `generation_params`, `VariantBuildStrategy` replaces capability-based compatibility, `VoicePreview` replaces single-column preview, and `VoiceResource` introduces the Catalog/Library boundary.
> **Method:** Architecture refinement only. No code, no migrations, no UI.

---

## Executive Summary

The first architecture pass correctly identified that the backend data model supports the voice-centric vision. However, several concepts in the v1 proposal introduced incorrect coupling and leaky abstractions:

| v1 Concept | Problem | Refined |
|-----------|---------|---------|
| `generation_params` as persisted DB field | Metadata fragmentation; treats model contract as user data | `settings_schema` on `ModelDescriptor` code-declared, never persisted |
| Compatibility via `supports_voice_cloning` flag | Imprecise: capability != buildability | `VariantBuildStrategy` per adapter per creation source |
| Single `preview_audio` column | Cannot model zero, one, or many previews | `VoicePreview` as first-class entity (separate table) |
| New API compatibility endpoints | Premature; UI can derive from existing data | Client-side derivation from existing APIs |
| Fused catalog/library identity | Six bug classes trace to this conflation | `VoiceResource` as transient catalog type; Voice only after import |

### Six critical refinements

1. **`settings_schema` replaces `generation_params`** — The model declares its parameter contract as a JSON Schema-like structure on `ModelDescriptor`. It is a code-level declaration in `model_catalog.py` and `registry_types.py`. NOT stored in the database. NOT user data. NOT app state.

2. **`VariantBuildStrategy` replaces capability-based compatibility** — Each adapter declares for which `creation_source` values it can build variants, and what preconditions are required. `supports_voice_cloning = true` is no longer used as a compatibility signal.

3. **`VoiceResource` introduces the Catalog/Library boundary** — Catalog presets, marketplace listings, and import sources are transient `VoiceResource` descriptors. They become `Voice` entities only when the user performs an import action. This eliminates six classes of UI bugs at the architectural level.

4. **`VoicePreview` as a first-class entity** — A Voice may have zero, one, or many previews. Each preview has a type, language, source model, and storage path. The single `preview_audio` column is replaced by a `VoicePreview` table.

5. **No new API endpoints for compatibility** — The UI derives compatibility from existing data: `GET /variants/summary` already returns the voice×model variant status matrix. New endpoints are deferred until there is a clear architectural justification.

6. **`settings_schema` is not persisted** — It lives on `ModelDescriptor` as a code declaration only. The DB schema is not extended.

---

## Current Architecture Assessment

### 2.1 Runtime Layer — No changes from v1

**Status:** Sound. No runtime changes needed. The runtime already:
- Resolves Voice + Model → VoiceVariant through the DB.
- Validates capabilities before generation.
- Merges variant `params` into `gen_params`.
- Never branches on model id/name.

### 2.2 API Layer — Assessment refined

**Current state:** API already exposes:
- `GET /voices` — returns `creation_source`, `preview_audio`, `is_preset_voice`
- `GET /models` — returns `capabilities`, `supported_languages`, `supported_tags`
- `GET /voices/{id}/variants` — per-model variant status
- `GET /variants/summary` — voice × model variant matrix
- `POST /voices/from-preset` — creates Voice from preset

**v1 identified missing APIs:** `?compatible_with_model=` filter, compatible-models endpoint.

**Refined assessment:** These endpoints are premature. The UI can derive compatibility from `GET /variants/summary` alone. No new endpoints needed.

### 2.3 Data Model — Assessment refined

**Current model (unchanged from v1; no new tables needed yet):**
```
voices:              id, public_voice_id, name, creation_source, preview_audio, meta,
                     is_favorite, last_used_at, ...
voice_variants:      id, voice_id, model_id, params, artifacts, source, status, ...
voice_variant_artifacts:  id, voice_variant_id, version, storage_keys, meta, ...
models:              id, name, capabilities, supported_languages, supported_tags, ...
voice_source_assets: id, voice_id, asset_type, storage_key, audio_duration, ...
```

**`creation_source`** remains the exclusive Voice-level taxonomy (ADR-0011):
- `SOURCE_ASSET` — cloned from reference audio
- `PRESET_VOICE` — provider-native preset
- `MARKETPLACE_VOICE`, `TRAINED_VOICE`, `IMPORTED_VOICE`, `SYSTEM_VOICE` — reserved

**Future `VoicePreview` table** (conceptual, not for current implementation):
```
voice_previews: id, voice_id, preview_origin, language, source_model_id, storage_key, duration, created_at
```

### 2.4 Frontend Layer — Same gaps as v1, refined solutions

| Component | Current behavior | Problem | Refined solution |
|-----------|-----------------|---------|------------------|
| `VoiceSelector` | Shows ALL voices | No model compatibility filtering | Filter by variant_summary (client-side) |
| `VoiceCard` | Play button, duration for all | Presets break player | Type-aware rendering via creation_source + previews |
| `VoiceDetailsDrawer` | Same 4-tab panel for all | Source tab empty for presets | Conditional tabs per creation_source |
| `LanguageCombobox` | 646 languages always | Not filtered by model | Filter by `settings.supported_languages` |
| `GenerationSettingsFields` | Static OmniVoice controls | Wrong for Kokoro etc. | `DynamicSettingsForm` from `model.settings_schema` |
| `GenerationPanel` | Voice Design capability-gated | Only capability-driven check | Keep; all settings become dynamic |

---

## Voice Architecture — Refined Concepts

### 3.1 Voice Identity vs Catalog Resources (ADR-0012)

**v1 assumption:** All voice-like entities are `Voice` entities.

**Refined:** Catalog resources (provider presets, marketplace listings) are transient descriptors. They become `Voice` entities only when the user imports them.

**Two data sources:**
- **Catalog** (`GET /voice-resources`): Provider presets, marketplace listings, import sources. Transient, never stored. Includes `is_in_library` flag and `library_voice_id` pointer.
- **Library** (`GET /voices`): User's persisted Voice entities with variants, artifacts, previews.

**Example — Bella (Kokoro):**
1. User browses catalog → sees Bella as `VoiceResource` (type=preset, provider=kokoro).
2. Preview plays from provider metadata or auto-generated sample.
3. User clicks "Add to Library" → `POST /voices/from-preset` creates `Voice` + `VoiceVariant` + `Artifact`.
4. Bella is now in `GET /voices` with `creation_source=PRESET_VOICE`.

**Bug fix without code:**
- Play button: catalog resources show only if `preview_audio` exists or provider supplies one. Library Voices show if `VoicePreview` records exist.
- Infinity duration: catalog resources have no `audio_duration` field. Library Voices without previews have `preview_summary.origin=none`.
- Preset appearing as clone: `creation_source=PRESET_VOICE` badge renders differently from `SOURCE_ASSET`.

### 3.2 `settings_schema` — Model Contract, Not User Data (replaces `generation_params`)

**v1 error:** `generation_params` was proposed as a persisted field on ModelDescriptor and the `models` table. This treats a model contract as application state.

**Refined:** `settings_schema` is a code-level declaration on `ModelDescriptor` in `registry_types.py`. It is populated in `model_catalog.py` alongside capabilities, languages, and tags. NOT stored in the database.

```python
# registry_types.py — new field on ModelDescriptor
settings_schema: SettingsSchema | None = None

class SettingsSchema(BaseModel):
    type: Literal["object"] = "object"
    properties: dict[str, ParameterSchema]
    required: list[str] = []

class ParameterSchema(BaseModel):
    type: Literal["number", "boolean", "string", "select"]
    label: str
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    options: list[SelectOption] | None = None
    description: str | None = None
```

**Usage in `model_catalog.py`:**
```python
ModelDescriptor(
    id="omnivoice-base",
    ...
    settings_schema=SettingsSchema(
        properties={
            "num_step": ParameterSchema(type="number", label="Inference Steps",
                default=32, minimum=4, maximum=64, step=1),
            "guidance_scale": ParameterSchema(type="number", label="Guidance Scale",
                default=2.0, minimum=0, maximum=4, step=0.1),
            "speed": ParameterSchema(type="number", label="Speed",
                default=None, minimum=0.5, maximum=1.5, step=0.05),
            "duration": ParameterSchema(type="number", label="Duration",
                default=None, minimum=1, maximum=120),
            "t_shift": ParameterSchema(type="number", label="Time Shift",
                default=0.1, minimum=0, maximum=1, step=0.01),
            "denoise": ParameterSchema(type="boolean", label="Denoise",
                default=True),
        },
        required=[],
    )
)

ModelDescriptor(
    id="kokoro-base",
    ...
    settings_schema=SettingsSchema(
        properties={
            "speed": ParameterSchema(type="number", label="Speed",
                default=1.0, minimum=0.5, maximum=2.0, step=0.1),
        },
        required=[],
    )
)
```

**Why this is correct:**
- It is a **model contract**, like capabilities, languages, and tags.
- It is **declared in code**, not stored in data.
- It is **versioned** with the model descriptor, not migrated.
- It is **additive**: new models declare their own schema without touching the DB.
- It is **exposed via `GET /models`** alongside capabilities, languages, tags.
- The frontend renders it dynamically: any model with `settings_schema` gets auto-generated controls.

**Backward compatibility:** If `ModelDescriptor.settings_schema` is absent (older model definitions), the frontend falls back to the current static OmniVoice settings form.

### 3.3 VariantBuildStrategy — Explicit Build Declaration (replaces capability-based)

**v1 error:** Compatibility used `supports_voice_cloning = true` to determine if a SOURCE_ASSET could be used with a model. This is imprecise: a model may support cloning but have no builder pipeline, or the builder may be disabled.

**Refined:** Each adapter declares its `VariantBuildStrategy` per creation source. This answers "can this model BUILD a variant from this voice type?" — NOT "does this model support cloning in principle?"

```python
# On the ModelAdapter base class or a new BuildStrategyRegistry
class VariantBuildStrategy(BaseModel):
    creation_source: str
    can_build: bool
    requires: list[str]  # e.g., ["source_asset"], ["preset_name"]
    description: str = ""

class ModelAdapter(ABC):
    @staticmethod
    def get_build_strategies() -> list[VariantBuildStrategy]:
        """Declares which creation sources this adapter can build variants from."""
        return []

# KokoroAdapter — presets only
class KokoroAdapter(ModelAdapter):
    @staticmethod
    def get_build_strategies():
        return [
            VariantBuildStrategy(
                creation_source="PRESET_VOICE",
                can_build=True,
                requires=["preset_name", "provider"],
                description="Kokoro presets are realized by selecting the preset voice pack.",
            ),
        ]

# OmniVoiceAdapter — source assets only
class OmniVoiceAdapter(ModelAdapter):
    @staticmethod
    def get_build_strategies():
        return [
            VariantBuildStrategy(
                creation_source="SOURCE_ASSET",
                can_build=True,
                requires=["source_asset"],
                description="OmniVoice clones a voice from reference audio.",
            ),
        ]
```

**Compatibility rule (refined):**
```
A voice V is compatible with model M IF:
  (a) a ready VoiceVariant exists for (V, M), OR
  (b) M's adapter declares a VariantBuildStrategy for
      V.creation_source with can_build=True AND all
      requires preconditions are satisfied.
```

This is strictly more precise and eliminates the implicit assumption that `supports_voice_cloning = true` means a build is possible.

### 3.4 CompatibilityResolver — Canonical Source of Truth

**v2 gap:** The initial proposal relied on the frontend to join `GET /variants/summary` + `model.build_strategies` and reimplement the compatibility rule in TypeScript. This has no single source of truth and misses potential compatibility (variant_summary only shows existing variants).

**Refined:** A `CompatibilityResolver` backend service encapsulates the compatibility rule and exposes results as derived fields on existing API responses.

```
CompatibilityResolver
├── get_compatible_models(voice) → list[model_id]
│   ├── check existing ready variant →
│   │     variant exists and status=="ready" → compatible ✓
│   └── check build strategies →
│         adapter declares strategy for this creation_source with can_build=True → compatible ✓
│         else → NOT compatible ✗
│
└── get_compatible_voices(model) → list[voice_id]
    └── (same logic, inverted)

API surface (no new endpoints):
├── GET /voices → each voice includes compatible_models: string[]
├── GET /voices/{id} → includes compatible_models: string[]
└── GET /models/{id} → includes compatible_voices: string[] (optional)
```

**Why this is correct:**
- Single source of truth: the compatibility rule lives in one place.
- Always current: reflects both existing variants AND potential builds.
- No client-side algorithm: frontend reads `voice.compatible_models` directly.
- For backward compatibility, absent `compatible_models` field means the frontend falls back to variant_summary join.

### 3.5 VoicePreview — Multi-Preview Support with Origin Tracking

**v1 error:** A single `preview_audio` column cannot model zero, one, or many previews. Additionally, the v1 naming (`preview_type`) conflated provenance with type classification — values like "reference_audio" and "generated_preview" describe where a preview came from, not what it is.

**Refined:** `VoicePreview` as a separate entity with `preview_origin` tracking where each preview came from. A Voice may have zero, one, or N previews.

```python
class VoicePreview(BaseModel):
    id: str
    voice_id: str
    preview_origin: Literal[
        "reference",      # original source audio (cloned voices)
        "generated",      # auto-generated sample from a model
        "provider",       # bundled with provider preset
        "user",           # user-uploaded sample
        "marketplace",    # bundled with marketplace listing
    ]
    language: str | None = None
    source_model_id: str | None = None
    storage_key: str
    duration: float
    created_at: datetime
```

**The UI renders the available previews. A derived `preview_summary` is returned for backward compatibility but is computed from the preview collection:**

```python
# Derived, not stored
def derive_preview_summary(previews: list[VoicePreview]) -> PreviewSummary:
    if not previews:
        return PreviewSummary(origin="none", reason="No preview available")
    # Prefer reference, then generated, then provider
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

**Implementation (Phase D, after initial frontend work):**
- New table `voice_previews`
- Migration: existing `preview_audio` on Voice copies to `VoicePreview` with `preview_origin = "reference"` if `creation_source = SOURCE_ASSET`
- API: `GET /voices/{id}/previews` returns all previews; `GET /voices/{id}/audio` returns the primary preview audio

### 3.6 VoiceResource — Transient Catalog Type (Future, Phase H)

**v1 recommendation:** No `VoiceResource` abstraction.

**Refined:** `VoiceResource` is a transient API type to represent catalog-level entities before they are imported as library Voices. It is NOT a database entity. **This is a future concept (Phase H) — not needed for the initial implementation wave.**

**Important — SOURCE_ASSET is NOT a catalog resource:**
A cloned voice (`creation_source = SOURCE_ASSET`) is created directly when a user uploads audio via `POST /voices`. There is no `VoiceResource` intermediary. The catalog→library boundary applies only to presets, marketplace listings, and other browsable resources.

```typescript
interface VoiceResource {
  resource_id: string;                    // catalog-level ID
  resource_type: "preset" | "marketplace" | "imported" | "generated";
  name: string;
  description: string | null;
  language: string | null;
  preview_audio_url: string | null;       // provider-supplied or null
  provider_metadata: Record<string, any>;
  compatible_models: string[];            // cached from adapter build strategies
  is_in_library: boolean;                 // already imported?
  library_voice_id: string | null;        // if imported, points to Voice
}
```

**Endpoints (future, Phase H):**
- `GET /voice-resources?resource_type=preset` — Browse provider presets
- `GET /voice-resources?resource_type=marketplace` — Browse marketplace
- `POST /voice-resources/{id}/import` — Import into library (creates Voice)

The existing `GET /provider-voices` endpoint on provider adapters is the natural source for `resource_type=preset`. Marketplace listings come from marketplace tables.

---

## Runtime Impact Analysis

**Minimal addition:** The runtime remains largely untouched. The `VariantBuildStrategy` is declared on adapters. The `CompatibilityResolver` is a new service that reads variant status from the DB and build strategies from adapters.

**The core addition — CompatibilityResolver:**
```python
class CompatibilityResolver:
    """Single source of truth for voice-model compatibility."""

    def __init__(self, db, adapters: dict[str, ModelAdapter]):
        self.db = db
        self.adapters = adapters

    def get_compatible_models(self, voice_id: str) -> list[str]:
        compatible = []
        for model_id, adapter in self.adapters.items():
            # Check existing ready variant
            variant = self._get_variant(voice_id, model_id)
            if variant and variant.status == "ready":
                compatible.append(model_id)
                continue
            # Check build strategy for this creation_source
            voice = self._get_voice(voice_id)
            strategies = adapter.get_build_strategies()
            for s in strategies:
                if s.creation_source == voice.creation_source and s.can_build:
                    compatible.append(model_id)
                    break
        return compatible
```

This is a query-time computation, exposed as a derived field on existing API responses. No new endpoints.

---

## API Impact Analysis

### 5.1 Revised Endpoint Assessment

**No new endpoints needed for v2.** The current API is sufficient with field additions.

| Need | How it's satisfied | Endpoint change needed? |
|------|-------------------|------------------------|
| Filter voices by model compatibility | `GET /voices` returns `compatible_models[]` per voice (from CompatibilityResolver) | Add `compatible_models` derived field |
| Show compatible models for a voice | Read `voice.compatible_models` directly | Same field |
| Preview origin for voice | Derive from `preview_audio` (interim) or `GET /voices/{id}/previews` (future) | Future: `GET /voices/{id}/previews` |
| Framework settings from model | `GET /models/{id}` returns `settings_schema` | Add `settings_schema` field to response (from code, no DB) |
| Browse catalog presets | Existing `GET /provider-voices` per adapter | Unify as `GET /voice-resources` (future, Phase H) |

### 5.2 Endpoints that need field additions

- `GET /models` — add `settings_schema` field (serialized from `ModelDescriptor.settings_schema`, code-level, no DB read)
- `GET /models` — add `voice_features` derived field (`ModelVoiceFeatures`)
- `GET /voices` — add `compatible_models` derived field (from CompatibilityResolver)
- `GET /voices` — add `preview_summary` derived field (`{origin, count, languages}`)
- `GET /voices/{id}` — add `compatible_models` derived field
- `GET /voices/{id}` — add `preview_summary` derived field

### 5.3 Endpoints that remain unchanged

- `POST /generate` — unchanged
- `POST /voices/from-preset` — unchanged (creates Voice from catalog resource)
- `GET /variants/summary` — unchanged (CompatibilityResolver reads this internally)
- `GET /voices/{id}/variants` — unchanged

---

## Frontend Impact Analysis

### 6.1 DynamicSettingsForm (from settings_schema, not generation_params)

The frontend renders a form dynamically from `model.settings_schema.properties`:

```typescript
interface DynamicSettingsFormProps {
  schema: SettingsSchema;
  values: Record<string, any>;
  onChange: (values: Record<string, any>) => void;
}
```

- Numbers → range sliders
- Booleans → switches
- Selects → dropdowns
- Strings → text inputs

**Backward compatibility:** If `settings_schema` is null/undefined, fall back to current `GenerationSettingsFields` static form.

### 6.2 VoiceSelector — Compatibility via Backend Resolver

Using the `compatible_models` derived field from `GET /voices`:

```typescript
// VoiceSelector.tsx
// Each voice now includes voice.compatible_models: string[]
const compatibleVoiceIds = useMemo(() => {
  if (!selectedModelId) return null; // show all
  return voices
    .filter(v => v.compatible_models?.includes(selectedModelId))
    .map(v => v.id);
}, [voices, selectedModelId]);

const filtered = compatibleVoiceIds
  ? voices.filter(v => compatibleVoiceIds.includes(v.id))
  : voices;
```

No new backend endpoint required. The resolver is a single source of truth.

### 6.3 LanguageCombobox — Model-Aware Filtering

Unchanged from v1:

```typescript
const availableLanguages = activeModel?.supported_languages?.length
  ? activeModel.supported_languages
  : undefined; // show all
```

### 6.4 VoiceCard — Type-Aware + Preview-Aware

**Refined from v1:** The play button is gated on `preview_summary.origin !== "none"` instead of `audio_duration > 0`. The badge shows `creation_source` directly.

### 6.5 VoiceDetailsDrawer — Type-Aware + Preview-Aware

**Refined from v1:** Previews tab added (future). Audio player conditional on `preview_summary`.

### 6.6 Catalog Library Boundary in UI

The TTS panel's VoiceSelector uses the library (`GET /voices`). The Voice Library page adds a "Browse Presets" option that fetches `GET /voice-resources` (future). For now, presets are imported via the existing `POST /voices/from-preset` flow.

---

## UX Assessment

### 7.1 TTS Page

**Unchanged from v1:** The flow is:
1. User selects a voice (from all library voices, with compatibility hints).
2. Model list filters to compatible models.
3. Settings render from `model.settings_schema`.
4. Language filters to model's `supported_languages`.

### 7.2 Voice Library

**Refined from v1:** The library shows only imported Voices (not catalog presets). Future: "Browse" tab for catalog resources.

### 7.3 Catalog Browsing (Future)

The Voice Library gains a "Browse" view showing `VoiceResource` items. Each item has an "Add to Library" action. Before adding, the item is a transient descriptor. After adding, it becomes a `Voice` and appears in the "Library" view.

---

## Scalability Assessment

### 8.1 Community Edition

All proposals remain CE-compatible:
- `settings_schema` is code-level, no new tables
- `VoicePreview` is a new table but simple (added in Phase E)
- `VoiceResource` is a transient type, no storage
- Compatibility derivation is handled by CompatibilityResolver (backend); frontend reads `compatible_models` field
- No new heavy computations

### 8.2 Cloud Edition

No architectural blockers:
- Marketplace listings: already schema-ready tables
- `VoicePreview` supports marketplace previews natively
- `VoiceResource` extends to marketplace items
- Catalog browsing scales with query-time `VoiceResource` construction

---

## Proposed Architecture — Refined

### 9.1 Entity Boundary Model

```
CATALOG (transient descriptors)                    LIBRARY (persisted entities)
==============================                     ============================

VoiceResource (type=preset)                        Voice
├── provider: "kokoro"                             ├── public_voice_id
├── preset_name: "pm_alex"                         ├── creation_source: PRESET_VOICE
├── compatible_models: ["kokoro-base"]             ├── owner_id
└── preview_audio: null                            ├── VoiceVariant(s)
                                                    ├── VoicePreview(s)
  │                                                 └── VoiceVariantArtifact(s)
  │  POST /voice-resources/{id}/import
  │  or POST /voices/from-preset
  ▼
VoiceResource (type=marketplace)                   Voice
├── listing_id: "mv_123"                           ├── public_voice_id
├── creator: "user_abc"                            ├── creation_source: MARKETPLACE_VOICE
├── price: 9.99                                    ├── VoiceVariant(s) (pre-built)
├── compatible_models: ["all"]                     ├── VoicePreview(s) (from listing)
└── previews: [sample1.wav, sample2.wav]           └── ... (purchased)

_SOURCE_ASSET voices are created directly via audio upload — no catalog stage._
```

### 9.2 ModelVoiceFeatures — Consolidated View

```python
# Derived from adapter build strategies + capabilities — computed, never stored
ModelVoiceFeatures:
  voice_types: ["cloned"]               # OmniVoice: SOURCE_ASSET build strategy
  voice_types: ["preset"]               # Kokoro: PRESET_VOICE build strategy
  voice_types: ["cloned", "preset"]     # Fish Audio: both build strategies
  voice_types: ["cloned", "converted"]  # CosyVoice: cloning + voice conversion
  voice_types: ["cloned", "trained"]    # SparkTTS: cloning + custom training
```

The frontend renders this as: "Supports: cloning + conversion" — a human-readable badge from a single field.

### 9.3 Compatibility Resolution

```
Voice {creation_source: PRESET_VOICE}
│
├── VariantBuildStrategy(KokoroAdapter) ── can_build=True ── compatible with kokoro-base
├── VariantBuildStrategy(OmniVoiceAdapter) ── can_build=False ── NOT compatible with omnivoice-base
│
└── Result: {compatible_models: ["kokoro-base"]}

Voice {creation_source: SOURCE_ASSET}
│
├── ready variant for omnivoice-base ── compatible
├── VariantBuildStrategy(OmniVoiceAdapter) ── can_build=True ── compatible
├── VariantBuildStrategy(FishAudioAdapter) ── can_build=True ── compatible
├── VariantBuildStrategy(KokoroAdapter) ── can_build=False ── NOT compatible
│
└── Result: {compatible_models: ["omnivoice-base", "fish-audio-s2"]}
```

### 9.4 Frontend Architecture

```
Page Components
├── Voice Library ── shows Library Voices (GET /voices)
│   ├── SearchBar ── debounced text search (name)
│   ├── SortDropdown ── name, created_at, last_used_at, language
│   ├── FilterChips ── creation_source, language, provider, compatible_model, favorites
│   ├── VirtualVoiceList ── virtual scrolling at 100+ voices
│   └── PaginationControls ── backend-driven page navigation
├── VoiceDetailPanel ── canonical voice surface (modal or drawer)
├── Browse Catalog (future) ── shows VoiceResources (GET /voice-resources)
│   └── "Add to Library" action for each
└── TTS Panel
    ├── VoiceSelector ── library voices, filtered by compatible_models
    ├── ModelSelector ── compatible models for selected voice; pre-selects primary_model_id
    ├── DynamicSettingsForm ── from model.settings_schema
    ├── LanguageCombobox ── filtered by model.supported_languages
    └── VoiceDesign ── capability-gated, unchanged

Shared Components
├── VoiceCard ── type-aware (creation_source badges, preview-aware play button)
├── VoiceDetailPanel ── canonical voice surface (all voice types: Library, Presets, Marketplace, Imported)
└── AudioPlayer ── handles "none" preview (no display)
```

### 9.5 Settings Schema (replaces Generation Parameters)

```
ModelDescriptor
├── capabilities (ADR-0003)
├── supported_languages
├── supported_tags
├── supported_voice_design
└── settings_schema (NEW — code-declared, not persisted)
    └── properties
        ├── num_step:     {type: number, label: "Inference Steps", default: 32, min: 4, max: 64}
        ├── guidance_scale: {type: number, label: "Guidance Scale", default: 2.0, min: 0, max: 4}
        ├── speed:        {type: number, label: "Speed", default: null, min: 0.5, max: 1.5}
        ├── duration:     {type: number, label: "Duration", default: null, min: 1, max: 120}
        ├── t_shift:      {type: number, label: "Time Shift", default: 0.1, min: 0, max: 1}
        └── denoise:      {type: boolean, label: "Denoise", default: true}
```

---

## Voice Library UX Architecture

The Voice Library is the canonical browsing surface for all voices. It must scale from dozens to 100,000+ voices across 8+ providers. The following primitives are first-class architectural concepts.

### 10.1 Search

Search is **required** at all scales. At 1,000+ voices, point-and-click browsing is insufficient.

| Search dimension | Scope | Implementation |
|----------------|-------|----------------|
| `?search=` (name) | All voices | SQL `ILIKE` on `voice.name`; frontend debounced text input |
| `?search_language=` | All voices | Filter by `voice.meta.language` or variant language metadata |
| `?search_provider=` | PRESET_VOICE voices | Filter by `voice.meta.provider` (e.g., "kokoro", "fish-audio") |
| `?search_tags=` | All voices (future) | User-defined tags; no implementation now |

The library always has a search bar. Results filter in real-time with backend-driven queries.

### 10.2 Filters

Filters are **combinatorial** — multiple filters can be active simultaneously.

| Filter | Parameter | Values | Behavior |
|--------|-----------|--------|----------|
| creation_source | `?creation_source=` | SOURCE_ASSET, PRESET_VOICE, MARKETPLACE_VOICE, TRAINED_VOICE, IMPORTED_VOICE, SYSTEM_VOICE | Exists today; add to library UI |
| language | `?language=` | ISO language code | Filter by voice language |
| provider | `?provider=` | Provider name (kokoro, omnivoice, fish-audio, etc.) | Filter PRESET_VOICE voices by source provider |
| compatible_model | `?compatible_model=` | Model ID (omnivoice-base, kokoro-base, etc.) | Filter by CompatibilityResolver; returns voices where model is in `compatible_models` |
| favorites | `?favorites=true` | Boolean | Returns only favorited voices |
| recently_used | `?recently_used=` | Time period (7d, 30d, 90d) | Returns voices used within the period |

Filters appear as chips in the library header. Active filter count is shown. Clear all button.

### 10.3 Sorting

| Sort mode | Parameter | Default direction |
|-----------|-----------|-------------------|
| Name | `?sort=name` | asc |
| Created date | `?sort=created_at` | desc |
| Last used | `?sort=last_used_at` | desc |
| Language | `?sort=language` | asc |

Default sort: `?sort=last_used_at` (desc) — most recently used voices appear first.

### 10.4 Pagination

Backend-driven pagination. Frontend requests page size.

| Parameter | Default | Max |
|-----------|---------|-----|
| `?page=` | 0 | N |
| `?limit=` | 50 | 200 |

Response includes:
```json
{
  "items": [...],
  "total": 100000,
  "page": 0,
  "limit": 50,
  "total_pages": 2000
}
```

### 10.5 Virtualization

Frontend-driven. The voice list must use virtual scrolling (react-window, react-virtuoso, or similar) when the number of voices exceeds a threshold (recommended: 100).

The VoiceCard component receives a fixed height in list mode, variable height in grid mode. Virtualization applies to both.

### 10.6 Favorites

See §11 (Favorites Design) below.

### 10.7 Recently Used

`Voice.last_used_at` is updated on each successful generation for that voice.

**API behavior:**
- `GET /voices?sort=last_used_at` — returns most recently used voices first
- `GET /voices?recently_used=7d` — returns voices used in the last 7 days
- `PATCH /voices/{id}` — allows clearing `last_used_at` (set to null)
- `last_used_at` is set in the generation completion handler (not in the request handler — set after successful generation)

**Migration:** New column, nullable. Existing voices have `last_used_at = NULL`. Not backfilled.

### 10.8 Collections (Future — No Implementation)

Collections are user-defined groups of voices (e.g., "Narration voices", "Character voices", "Podcast"). They are **not designed or implemented now**.

**Named reservation:**
- Future `voice_collections` table: `id, name, description, owner_id, created_at`
- Future `voice_collection_members` table: `id, collection_id, voice_id, sort_order`
- No API surface, no UI, no migration now
- This is a Cloud-scale feature; CE may use flat favorites as the only organization primitive

---

## Favorites Design

### 11.1 Storage Model

**Community Edition (single-user):**

`Voice.is_favorite` boolean column. Default `false`.

```sql
ALTER TABLE voices ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT false;
```

**Future Cloud (multi-user):**

`voice_favorites` table with per-user favorite tracking.

```sql
CREATE TABLE voice_favorites (
    id UUID PRIMARY KEY,
    voice_id UUID NOT NULL REFERENCES voices(id),
    owner_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(voice_id, owner_id)
);
```

### 11.2 Why CE uses a boolean on Voice

- CE is single-user: there is exactly one `owner` per PeakVox installation.
- A separate `voice_favorites` table for CE adds a JOIN for every library query, with zero benefit.
- The boolean makes filtering trivial: `WHERE is_favorite = true`.
- The boolean makes the favorite toggle atomic: `UPDATE voices SET is_favorite = NOT is_favorite WHERE id = ?`.
- No pagination, no conflict resolution, no synchronization needed.

### 11.3 API Behavior

| Action | Endpoint | CE behavior | Cloud behavior (future) |
|--------|----------|-------------|--------------------------|
| List favorites | `GET /voices?favorites=true` | `WHERE is_favorite = true` | JOIN voice_favorites WHERE owner_id = current_user |
| Toggle favorite | `PATCH /voices/{id}` with `{"is_favorite": true/false}` | Update column | INSERT/DELETE from voice_favorites |
| Check if favorited | `GET /voices/{id}` returns `is_favorite` | Read column | Subquery on voice_favorites |
| Favorite count | `GET /voices/{id}` returns `favorite_count` | 0 or 1 (trivial) | COUNT from voice_favorites |

### 11.4 Frontend Behavior

| Element | Behavior |
|---------|----------|
| Favorite icon (filled/outlined heart) | Toggle calls `PATCH /voices/{id}` with `{"is_favorite": bool}` |
| Favorites filter chip | `?favorites=true` — shows only favorited voices |
| Default sort shows favorites first | Optional: `?sort=favorites_first` — pushes favorited voices to top without filtering |
| VoiceDetailPanel header | Favorite toggle always visible |

### 11.5 Cloud Migration Path

1. Add `voice_favorites` table (CE-unused, but schema-ready).
2. Migration: `INSERT INTO voice_favorites (voice_id, owner_id) SELECT id, owner_id FROM voices WHERE is_favorite = true`.
3. API switches from column read to JOIN with `voice_favorites`.
4. CE to Cloud upgrade is a single migration step.
5. The `is_favorite` column on Voice remains but is deprecated in Cloud — CE keeps it as the canonical store.

### 11.6 Non-Goals

- Favorites sync between CE and Cloud (not applicable — separate installations).
- Shared/public favorites (future Cloud feature; no design now).
- Favorite collections/groups (see §10.8 Collections — future).

---

## VoiceDetailPanel — Canonical Voice Surface

### 12.1 Motivation

The review identified that every voice type (cloned, preset, marketplace, imported) currently has separate detail implementations. The six classes of bugs traced to this fragmentation. A single canonical `VoiceDetailPanel` component prevents re-fragmentation.

### 12.2 Component Definition

```typescript
interface VoiceDetailPanelProps {
  voice: Voice | VoiceResource;
  onAction: (action: VoiceDetailAction) => void;
}

type VoiceDetailAction =
  | { type: "use_in_tts" }
  | { type: "toggle_favorite"; value: boolean }
  | { type: "delete" }
  | { type: "export" }
  | { type: "import_to_library" };  // VoiceResource only
```

### 12.3 Layout

```
┌──────────────────────────────────────────────────┐
│ Header                                           │
│  [Name]                     creation_source badge │
│  Favorite toggle (★/☆)                           │
├──────────────────────────────────────────────────┤
│ Overview                                         │
│  Description  ·  Language  ·  Created            │
│  Provider metadata (PRESET_VOICE only)           │
├──────────────────────────────────────────────────┤
│ Previews                                         │
│  AudioPlayer with waveform                       │
│  Preview language selector (multiple previews)   │
│  "No preview available" when origin is "none"    │
├──────────────────────────────────────────────────┤
│ Compatible Models                                │
│  omnivoice-base     ✓  (primary)                 │
│  fish-audio-s2      ✓  (recommended)             │
│  kokoro-base        ✗                            │
│                                                  │
│  Primary model: omnivoice-base                   │
│  Recommended:    fish-audio-s2                   │
├──────────────────────────────────────────────────┤
│ Variants                                         │
│  Model         Status    Version   Actions        │
│  omnivoice     ready     v3        Rebuild        │
│  fish-audio    building  v2        —              │
│  kokoro        —         —         Build          │
├──────────────────────────────────────────────────┤
│ Actions                                          │
│  [Use in TTS]  [Export]  [Delete]  [Favorite]    │
└──────────────────────────────────────────────────┘
```

### 12.4 Section Collapse Rules

| Section | Visible when... |
|---------|-----------------|
| Header | Always |
| Overview | Always; provider metadata section hidden when `creation_source ≠ PRESET_VOICE` |
| Previews | At least one preview exists (`preview_summary.origin !== "none"`) |
| Compatible Models | Always (shows compatible + incompatible) |
| Variants | At least one variant exists or can be built |
| Actions | Always (favorite always available; delete if owned; import if VoiceResource) |

### 12.5 Usage Across Voice Types

| Surface | Component | Notes |
|---------|-----------|-------|
| Voice Library | `VoiceDetailPanel` with Voice | Full panel |
| Preset (Browse) | `VoiceDetailPanel` with VoiceResource | "Import to Library" action replaces "Delete" |
| Marketplace (future) | `VoiceDetailPanel` with VoiceResource | "Purchase" action replaces "Delete" |
| Imported (future) | `VoiceDetailPanel` with Voice | Full panel, "Import" section hidden (already imported) |
| TTS Panel | `VoiceDetailPanel` (compact) | "Use in TTS" is primary action; sections collapsible |

### 12.6 Implementation Rule

**There is exactly one `VoiceDetailPanel` component.** It accepts both `Voice` and `VoiceResource` types. It does not branch on type for layout — it branches for action availability. This is the **single canonical voice inspection surface** across the entire application.

---

## Primary Model vs Recommended Model

### 13.1 Current Design

The spec currently exposes `compatible_models[]` per voice — a flat list of model IDs that can realize this voice. The frontend displays this list and auto-filters the ModelSelector.

### 13.2 Analysis

**Question: Should the voice contract expose `primary_model_id` and `recommended_model_id` in addition to `compatible_models[]`?**

| Concept | Definition | Example |
|---------|-----------|---------|
| `compatible_models[]` | All models that can realize this voice (via variant OR build strategy) | `["omnivoice-base", "fish-audio-s2", "kokoro-base"]` |
| `primary_model_id` | The model that originally created this voice | SOURCE_ASSET → the model used at clone time; PRESET_VOICE → the native model (kokoro-base for Kokoro presets) |
| `recommended_model_id` | The model that will produce the best result for this voice | Could differ from primary for upgraded pipelines |

**Does this improve UX?**
- **Yes, significantly.** Today the user must know which model to select. With `primary_model_id`, the model is pre-selected when the voice is chosen — user only changes it if they want a different engine.
- **Yes, for preset voices.** A Kokoro preset should have `primary_model_id: "kokoro-base"` pre-selected. The user never needs to think about models for presets.
- **Yes, for new users.** The model becomes invisible for the common case (use the voice's native/default model).

**Does this reduce user friction?**
- **Yes.** It eliminates a decision point in the TTS flow. Voice → (model auto-selected) → Settings → Generate.
- The model selector becomes an "advanced" control — visible but pre-populated.

**Does it fit Voice-First architecture?**
- **Yes.** The voice ITSELF knows which model it prefers. The model is selected by the voice, not by the user choosing a model first.
- This reinforces ADR-0004 rule 2: "No feature assumes a Voice belongs to a specific model" — the voice has a *recommendation*, not a *belonging*.

**Should these values be derived or persisted?**

| Field | Strategy | Rationale |
|-------|----------|-----------|
| `compatible_models[]` | Derived (CompatibilityResolver) | Changes when variants are built/unbuilt, adapters change |
| `primary_model_id` | **Persisted** on Voice | Set at voice creation; does not change. SOURCE_ASSET → model used at clone; PRESET_VOICE → native model |
| `recommended_model_id` | **Derived** | Computed from variant quality, build freshness, or adapter ranking. May change over time |

### 13.3 Recommendation

**Add both `primary_model_id` and `recommended_model_id` to the voice contract.**

```json
{
  "voice_id": "voice_abc123",
  "name": "Larissa",
  "creation_source": "SOURCE_ASSET",
  "compatible_models": ["omnivoice-base", "fish-audio-s2"],
  "primary_model_id": "omnivoice-base",
  "recommended_model_id": "fish-audio-s2",
  "is_favorite": false,
  "last_used_at": "2026-06-06T12:00:00Z"
}
```

**Rules:**
- `primary_model_id` is set once at voice creation and never changes.
- `recommended_model_id` is derived by the CompatibilityResolver or a new `ModelRanking` service.
- Both are nullable (`null` for edge cases like imported voices with unknown origin).
- The frontend pre-selects `primary_model_id` when it exists; falls back to `recommended_model_id`; falls further back to the first entry in `compatible_models[]`; falls finally to no pre-selection (user picks).
- Neither field changes the compatibility rule — they are UX affordances, not access control.

### 13.4 Implementation

| Phase | Scope |
|-------|-------|
| A (P0) | Add `primary_model_id` column to Voice (nullable, set at creation) |
| A (P0) | Expose `primary_model_id` on GET /voices and GET /voices/{id} |
| B (P0) | Add `recommended_model_id` derivation to CompatibilityResolver |
| C (P0) | Frontend: pre-select model from `primary_model_id` when voice is selected |

## ADR List (Refined)

| # | Title | Status | Purpose |
|---|-------|--------|---------|
| ADR-0012 | Voice Identity vs Catalog Resources | **NEW** | Defines the boundary between transient catalog resources and persisted library Voices. Introduces `VoiceResource`, `VoicePreview`, `VariantBuildStrategy`. |

The remaining reserved ADRs (0013-0015) keep their original purposes.

---

## Spec List (Refined)

| Feature Spec | Scope | Priority |
|-------------|-------|----------|
| Settings Schema — Model Contract | Backend: add `settings_schema` to ModelDescriptor (code-level, no DB); expose in GET /models | P0 |
| DynamicSettingsForm — Capability-Driven UI | Frontend: render settings from model.settings_schema | P0 |
| Language Selector — Model-Aware | Frontend: filter languages by model.supported_languages | P0 |
| Voice Selector — Compatibility via Resolver | Frontend: filter using `compatible_models` derived field from API | P0 |
| CompatibilityResolver — Canonical Truth | Backend: single service, exposes `compatible_models` on GET /voices | P0 |
| Voice Card — Type-Aware | Frontend: creation_source badges, preview-aware play button | P0 |
| Voice Detail Panel — Type-Aware | Frontend: conditional tabs/fields by creation_source | P0 |
| ModelVoiceFeatures — Consolidated View | Backend: derived `voice_features` on model descriptor | P1 |
| VariantBuildStrategy — Adapter Declarations | Backend: each adapter declares build strategies per creation source | P1 |
| Preview System — VoicePreview Entity | Backend+Frontend: VoicePreview table, multi-preview support, preview_summary API | P1 |
| VoiceResource — Catalog Abstraction | Backend+API: transient VoiceResource type, GET /voice-resources, POST /import | P3 |
| Import Boundary — Catalog to Library | Backend+Frontend: unified "Add to Library" flow for all resource types | P3 |
| VOICE_DOMAIN_MODEL.md | Documentation: canonical domain model reference | P1 |
| Voice Library Search | Backend+Frontend: ?search= query param, debounced search bar, ILIKE on name | P0 |
| Voice Library Sorting | Backend+Frontend: ?sort=name|created_at|last_used_at|language | P0 |
| Voice Library Pagination | Backend: ?page=, ?limit=, total/total_pages in response | P0 |
| Voice Library Filters | Backend+Frontend: ?creation_source=, ?language=, ?provider=, ?compatible_model=, ?favorites=, ?recently_used= | P0 |
| Favorites — CE Storage | Backend: Voice.is_favorite boolean column, PATCH /voices/{id} toggle | P0 |
| VoiceDetailPanel — Canonical Surface | Frontend: single component for all voice types (Library, Presets, Marketplace, Imported) | P0 |
| Primary Model — Voice Contract | Backend: primary_model_id column on Voice, set at creation; exposed on GET /voices | P0 |
| Recommended Model — Derived | Backend: recommended_model_id derived by CompatibilityResolver | P0 |
| Recently Used Tracking | Backend: Voice.last_used_at column, updated on generation completion | P1 |
| Collections (Future) | Named reservation only — no implementation | P3 |

---

## Task Breakdown (Refined)

### Phase A: Model Contract & Dynamic UI (P0)

1. Add `settings_schema` field to `ModelDescriptor` in `registry_types.py` (code declaration)
2. Seed `settings_schema` in `model_catalog.py` for omnivoice-base, kokoro-base, future models
3. Expose `settings_schema` in `GET /models` response (serialized from descriptor)
4. Create `<DynamicSettingsForm>` component from `SettingsSchema` properties
5. Replace static fields in `GenerationSettingsFields.tsx` with `DynamicSettingsForm`
6. Keep `use_gpu` as capability-driven toggle (unchanged)

### Phase B: CompatibilityResolver (P0)

1. Create `CompatibilityResolver` service class in backend
2. Implement `get_compatible_models(voice_id)` using variant status + build strategies
3. Implement `get_compatible_voices(model_id)` — inverse lookup
4. Expose `compatible_models` as derived field on `GET /voices` and `GET /voices/{id}`
5. Expose `compatible_voices` on `GET /models/{id}` (optional, for future server-side filtering)

### Phase C: Frontend Capability Awareness (P0)

1. Filter `LanguageCombobox` by `activeModel.supported_languages`
2. Filter `VoiceSelector` by `compatible_models` field (from CompatibilityResolver)
3. Show compatibility count badges: "Compatible (3) · Not compatible (5)"
4. Bidirectional filtering: voice selection filters model list; model selection filters voice list
5. Add `creation_source` filter chips to Voice Library: "All", "Cloned", "Preset", "Favorites"

### Phase D: Type-Aware Voice Display (P0)

1. Create `creationSourceConfig` mapping (labels, colors, icons per source)
2. Update `VoiceCard`: conditional play button (via `preview_summary`), conditional duration, provider badge for PRESET_VOICE
3. Update `VoiceDetailsDrawer`: hide Source tab for PRESET_VOICE, hide waveform, hide transcript
4. Add provider metadata section for PRESET_VOICE (provider, preset name, languages, compatible models)
5. Add `preview_summary` derived field to `GET /voices` and `GET /voices/{id}`

### Phase E: Preview System (P1)

1. Create `VoicePreview` table (id, voice_id, preview_origin, language, source_model_id, storage_key, duration)
2. Migration: copy existing `preview_audio` data to VoicePreview records with `preview_origin = "reference"` for SOURCE_ASSET
3. Add `GET /voices/{id}/previews` endpoint
4. Add `derive_preview_summary()` helper (not stored — computed)
5. Update AudioPlayer: handle zero previews (no display)
6. Update BottomPlayer: handle zero previews (no display)

### Phase F: VariantBuildStrategy + ModelVoiceFeatures (P1)

1. Add `VariantBuildStrategy` model to `registry_types.py`
2. Add `get_build_strategies()` static method to `ModelAdapter` base class
3. Implement strategies for KokoroAdapter (PRESET_VOICE only)
4. Implement strategies for OmniVoiceAdapter (SOURCE_ASSET only)
5. Implement strategies for future adapters (Fish Audio, Dia, XTTS, F5-TTS, CosyVoice, SparkTTS)
6. Add `ModelVoiceFeatures` model and derivation logic to `registry_types.py`
7. Expose `voice_features` as derived field on `GET /models`

### Phase G: VOICE_DOMAIN_MODEL.md (P1)

1. Create `docs/.agents/ARCHITECTURE/VOICE_DOMAIN_MODEL.md`
2. Entity hierarchy diagram, definitions with ADR references
3. Creation paths for each creation_source
4. Model contract summary
5. Common mistakes case studies (the six bug classes)
6. Decision flowcharts for compatibility, preview, and rendering logic
7. Reference in AGENTS.md as mandatory reading

### Phase H: VoiceResource Catalog (P3 — Future)

1. Define `VoiceResource` transient type (API layer, not DB)
2. Create `GET /voice-resources` endpoint (unified catalog: presets + marketplace + imports)
3. Create `POST /voice-resources/{id}/import` endpoint (creates Voice)
4. Update frontend Voice Library with "Browse" tab
5. Update preset flow to use VoiceResource → Voice boundary

### Phase I: ADRs and Codification (P3)

1. Write remaining ADRs as needed (0013-0015)

### Phase J: Voice Library Search, Sort & Paginate (P0)

1. Add `?search=` query param to `GET /voices` (ILIKE on voice.name)
2. Add `?sort=` query param to `GET /voices` (name, created_at, last_used_at, language)
3. Add `?page=` and `?limit=` query params to `GET /voices`
4. Add `total` and `total_pages` to `GET /voices` response
5. Add `?language=`, `?provider=`, `?compatible_model=` filter params to `GET /voices`
6. Create SearchBar component with debounced input
7. Create SortDropdown component
8. Create FilterChips component (active filters display + clear)
9. Create PaginationControls component
10. Implement virtual scrolling in VoiceCard list (threshold: 100 voices)
11. Wire `?recently_used=7d|30d|90d` filter param

### Phase K: VoiceDetailPanel — Canonical Surface (P0)

1. Create single `VoiceDetailPanel` component (accepts Voice | VoiceResource)
2. Implement Header section: name, creation_source badge, favorite toggle
3. Implement Overview section: description, language, created date, conditional provider metadata
4. Implement Previews section: AudioPlayer + waveform, "No preview" when origin is none
5. Implement Compatible Models section: compatible list + primary/recommended indicators
6. Implement Variants section: per-model status table
7. Implement Actions section: Use in TTS, Export, Delete, Favorite
8. Replace existing VoiceDetailsDrawer usage with VoiceDetailPanel
9. Add compact mode for TTS Panel embed

### Phase L: Recently Used Tracking (P1)

1. Add `last_used_at` column to Voice (nullable, no default)
2. Update generation completion handler to set `last_used_at = NOW()`
3. Expose `last_used_at` in `GET /voices` and `GET /voices/{id}`
4. Support `?sort=last_used_at` and `?recently_used=7d|30d|90d` filters
5. No backfill — existing voices have null

### Phase M: Collections (P3 — Future)

1. Named reservation only. No implementation.

---

## Implementation Phases

### Phase 1 (Immediate — 1-2 sprints)
**Goal:** Model contract (settings_schema) + compatibility resolver + dynamic UI + library UX.

Tasks: A1-A6, B1-B5, J1-J11, K1-K9

### Phase 2 (Short-term — 1 sprint)
**Goal:** Type-aware voice display + model voice features + favorites + recently used.

Tasks: C1-C5, D1-D5, L1-L5

### Phase 3 (Medium-term — 1-2 sprints)
**Goal:** Preview system + VariantBuildStrategy + domain model documentation.

Tasks: E1-E6, F1-F7, G1-G7

### Phase 4 (Future)
**Goal:** VoiceResource catalog + import boundary.

Tasks: H1-H5

### Phase 5 (Future)
**Goal:** ADRs, remaining reserved concepts.

Tasks: I1-I2

### Phase 6 (Future)
**Goal:** Collections.

Tasks: M1

---

## Migration Strategy

**No data migration for Phase A.** `settings_schema` is code-only.
- `VoicePreview` migration is Phase E (new table + copy).
- `is_favorite` migration: `ALTER TABLE voices ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT false;` (Phase C).
- `last_used_at` migration: `ALTER TABLE voices ADD COLUMN last_used_at TIMESTAMP;` (Phase L).
- `primary_model_id` migration: `ALTER TABLE voices ADD COLUMN primary_model_id VARCHAR;` (Phase A).
- Existing `preview_audio` column continues to work during migration.

**Frontend migration:** All new behavior is additive:
- If `model.settings_schema` is absent → show current static OmniVoice form.
- If `preview_summary.origin` is "none" → hide audio player.
- If `creation_source` is not mapped → fall back to current behavior.

**No breaking changes.** Old frontend continues to work.

---

## Risks (Refined from v1)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `settings_schema` too rigid for novel parameter types (emotion sliders, pitch curves) | Low | Medium | Schema uses open `type: string` — extensible by convention; unknown types fall back to string input |
| Performance: CompatibilityResolver reads variant status + build strategies per request | Low (CE scale) | Low | Query is O(V * M) — minimal on CE; cacheable with Redis when Cloud demands |
| Existing `preview_audio` migration to VoicePreview table | Low | Medium | Keep column as fallback during transition; no data loss |
| Provider adapters not implementing `get_build_strategies()` | Medium | Medium | Default: empty list (no build strategies = no compatibility); models work only with existing variants |
| Catalog/library split confuses users | Medium | Low | Clear UI labels: "Library" vs "Browse Presets"; import action is explicit |

---

## Recommendation

1. **Implement `settings_schema` as code-declared model contract** — no DB, no migration, no metadata fragmentation. (Phase A)
2. **Implement `CompatibilityResolver` as single source of truth** — expose `compatible_models` on existing responses, no new endpoints. (Phase B)
3. **Fix the six bug classes at the architectural level** — type-aware rendering, preview-aware audio (`preview_origin`), `creation_source`-aware badges. (Phases C-D)
4. **Implement `VariantBuildStrategy` per adapter** — foundations for all future model compatibility. (Phase F)
5. **Implement `VoicePreview` as a separate entity** — support zero, one, or many previews. (Phase E)
6. **Create `VOICE_DOMAIN_MODEL.md`** — prevent future implementation mistakes through a canonical reference. (Phase G)
7. **Defer `VoiceResource` catalog abstraction** — not needed until marketplace/Cloud. (Phase H)
8. **Design Voice Library for scale** — search, sort, paginate, filter, favorites, virtual scroll. (Phase J)
9. **Create canonical `VoiceDetailPanel`** — single voice inspection surface for all voice types. (Phase K)
10. **Add `primary_model_id` and `recommended_model_id`** — voice knows its own model; model selection becomes automatic for the common case. (Phase A, B, C)
