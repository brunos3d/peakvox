# DESIGN — PeakVox Voice System Evolution (Refined)

## Architectural Design Decisions

### D1: `settings_schema` as Model Contract (NOT persisted `generation_params`)

`settings_schema` is a code-level declaration on `ModelDescriptor` in `registry_types.py`. It is populated in `model_catalog.py` alongside capabilities, languages, and tags. **It is never persisted to the database.**

**Why NOT a DB column:**
- A model's parameter schema is part of its **contract**, like capabilities and languages.
- It changes with model version, not with user data operations.
- Persisting it creates metadata fragmentation: the code declaration and the stored copy can diverge.
- No migration needed when adding new models or updating schemas.

**Why `settings_schema` and NOT `generation_params`:**
- `generation_params` implies "these ARE the generation parameters" (data). But they are schema — `settings_schema` describes what parameters exist and their constraints.
- `settings_schema` is parallel to JSON Schema: it declares a contract that instances conform to.

**Structure:**
```typescript
interface SettingsSchema {
  properties: Record<string, ParameterSchema>;
}

interface ParameterSchema {
  type: "number" | "boolean" | "string" | "select";
  label: string;
  default: number | boolean | string | null;
  minimum?: number;
  maximum?: number;
  step?: number;
  options?: { label: string; value: string }[];
  description?: string;
}
```

**Backward compatibility:** Absent `settings_schema` = fall back to current static OmniVoice form.

### D2: `VariantBuildStrategy` for Compatibility (NOT capability flags)

Compatibility between a Voice and a Model is determined by explicit `VariantBuildStrategy` declarations on the adapter, NOT by `ModelCapabilities.supports_voice_cloning`.

**Why NOT capabilities:**
- `supports_voice_cloning = true` means "this model supports cloning in principle" — NOT "this model can build a variant for this specific creation source."
- A model may support cloning but lack a builder pipeline, or its builder may be disabled.
- Future creation sources (MARKETPLACE_VOICE, IMPORTED_VOICE) have no corresponding capability flag.

**Compatibility rule:**
```
A voice V is compatible with model M IF:
  (a) a ready VoiceVariant exists for (V, M), OR
  (b) M's adapter declares a VariantBuildStrategy for
      V.creation_source with can_build=True AND all
      required preconditions are satisfied.
```

**Why NOT a new API endpoint:**
Compatibility is exposed as a **derived field on existing responses** (`GET /voices` returns `compatible_models[]` per voice), computed by a backend `CompatibilityResolver`. The frontend reads a single field per voice — no client-side algorithm, no multi-source join.

See D4 for the resolver design.

### D3: Voice Identity vs Catalog Resources (ADR-0012)

Catalog resources (provider presets, marketplace listings, import sources) are **transient descriptors**, not Voice entities. They become Voices only when imported by user action.

**Consequences:**
- `GET /voices` returns only library voices (persisted, owned, with variants).
- `GET /voice-resources` returns catalog items (transient, not persisted) — **future, Phase H**.
- The import boundary is explicit: importing a catalog resource creates a Voice.
- `SOURCE_ASSET` voices are created directly via audio upload, NOT from a catalog resource.
- Play button, duration, and preview logic check entity type before rendering.

**Why NOT a single model:**
- Browsing 10,000 marketplace listings should not create 10,000 Voice DB rows.
- Catalog resources have different metadata than library voices (pricing, creator, etc.).
- The six recent UI bugs (Infinity, AbortError, broken play, presets as clones) all trace to treating catalog items as library voices.

### D4: `CompatibilityResolver` as Canonical Source of Truth

Compatibility between a Voice and a Model is resolved by a **single backend component** (the `CompatibilityResolver`), NOT by client-side logic that joins two independent data sources.

**Why a single resolver:**
- `GET /variants/summary` only reflects **existing** variants — it cannot show potential compatibility via build strategies.
- A voice with `creation_source=SOURCE_ASSET` and no existing variant for omnivoice-base would not appear in variant_summary for omnivoice-base at all.
- The frontend would need to cross-reference variant_summary + build_strategies + creation_source and reimplement the compatibility rule in TypeScript — three sources, one algorithm, no authority.
- Every future change to the compatibility rule would require a frontend update.

**Resolver service:**
```python
class CompatibilityResolver:
    def get_compatible_models(self, voice: Voice) -> list[str]:
        """Returns all model IDs compatible with this voice."""
        compatible = []
        for model_id, adapter in self.adapters.items():
            # Check for existing ready variant
            if self._has_ready_variant(voice.id, model_id):
                compatible.append(model_id)
                continue
            # Check build strategy for this creation_source
            strategies = adapter.get_build_strategies()
            for s in strategies:
                if s.creation_source == voice.creation_source and s.can_build:
                    compatible.append(model_id)
                    break
        return compatible

    def get_compatible_voices(self, model_id: str) -> list[str]:
        """Returns all voice IDs compatible with this model."""
        ...
```

**API surface:** The resolver results are surfaced as derived fields on existing responses:
- `GET /voices` — each voice includes `compatible_models: string[]`
- `GET /models/{id}` — includes `compatible_voice_count: int` (full list returned when filter is active)
- No new compatibility-specific endpoints

**Backward compatibility:** `compatible_models` is a new field; absent = frontend falls back to client-side variant_summary join (same as current behavior).

### D5: `VoicePreview` as First-Class Entity (NOT single column)

A Voice may have zero, one, or many preview audio samples. Each preview has an origin, language, source model, and storage path. Previews are stored in a `voice_previews` table, not a single `preview_audio` column.

**Why NOT a single column:**
- A voice can have multiple previews (one per language, per model, or per source).
- Preview origins differ: `reference` (source audio), `generated` (model-generated), `provider` (bundled with preset), `user` (manual upload), `marketplace` (bundled with listing).
- A single column forces all previews into one bucket — no per-language or per-model previews.

**Why `preview_origin` and NOT `preview_type`:**
- The values describe WHERE the preview came from (provenance), not what kind of content it is.
- "Origin" is semantically precise: it determines lifecycle (can this be regenerated? is it user content? does it depend on a model?).
- Future dimensions (format, duration, quality) can be modeled as separate fields without ambiguity.

**Derived `preview_summary`:**
- The API returns a computed `preview_summary` field for backward compatibility: `{origin: "reference" | "generated" | "provider" | "none", count: number, languages: string[]}`.
- This is always derived from the actual preview records, never stored.

### D6: `ModelVoiceFeatures` — Consolidated Voice Feature View

A model's voice-related capabilities are scattered across independent fields: `capabilities.supports_voice_cloning`, `VariantBuildStrategy` per creation source, `supported_languages`, `settings_schema`. The frontend would need to check 4+ fields to answer "what can this model do with voices?"

`ModelVoiceFeatures` provides a single, computed convenience view:

```python
class ModelVoiceFeatures(BaseModel):
    voice_types: list[Literal["cloned", "preset", "trained", "converted"]]
```

**Derivation rules (computed, not stored):**
| `voice_types` entry | Condition |
|---|---|
| `"cloned"` | Adapter declares `SOURCE_ASSET → can_build=True` |
| `"preset"` | Adapter declares `PRESET_VOICE → can_build=True` |
| `"trained"` | `capabilities.supports_custom_training == True` |
| `"converted"` | `capabilities.supports_voice_conversion == True` |

**Why this is needed:**
- Future provider onboarding: implement `get_build_strategies()` + set capability flags → `ModelVoiceFeatures` auto-populates.
- Frontend renders badges: "Supports: cloning + preset" or "Supports: cloning, conversion, training."
- No new flags needed when adding a provider that supports a known voice type.

### D7: Backward Compatible Old Frontend

All new behavior is additive. Old frontend code continues to work:
- If `model.settings_schema` is absent → show current static OmniVoice form.
- If `preview_summary` is absent → use existing `preview_audio` + `audio_duration` logic.
- If `compatible_models` is absent → fall back to client-side variant_summary join.
- If `voice_features` is absent → render no feature badges.
- If `creation_source` is not mapped → show current generic badge/behavior.
- If `build_strategies` are absent → fall back to capability-based compatibility inference.
- Existing endpoints (`POST /generate`, `GET /voices`, etc.) change no payloads — only add new fields.

### D8: Voice Library UX — Scale Primitives Are First-Class Architecture

The Voice Library is not merely a list view — it is the primary browsing surface for the entire product. Search, sorting, filtering, pagination, and virtualization are **architectural concerns**, not UI polish.

**Why these belong in the architecture spec:**
- Without search, the product is unusable beyond ~200 voices. At 8+ providers, each with hundreds of presets, 200 voices is reached in week one.
- Without pagination, every `GET /voices` response grows unbounded. Frontend rendering cost grows linearly with voice count.
- Without virtual scrolling, the VoiceCard list causes DOM bloat and jank at 500+ voices.
- Without combinatorial filtering (`?creation_source=PRESET_VOICE&provider=kokoro&language=pt`), users cannot find specific voices.

**Design:**
- All library queries are backend-driven with `?search=`, `?sort=`, `?page=`, `?limit=`, and filter parameters.
- The frontend is a stateless consumer of paginated API responses — it renders what the backend returns.
- Virtual scrolling is a frontend concern only (no API change).
- Default sort is `last_used_at DESC` — the most recently used voice appears first.

### D9: Favorites — CE Boolean, Cloud Table

**CE strategy:** `Voice.is_favorite` boolean column. Single-user means no JOIN, no conflict, no sync.

**Why NOT a separate table for CE:**
- A separate `voice_favorites` table adds a JOIN (or subquery) to every library query.
- For single-user CE, the favorite set is always small (<100 voices typically). The boolean is faster to query and simpler to toggle.
- The toggle is atomic SQL: `UPDATE voices SET is_favorite = NOT is_favorite WHERE id = ?`.

**Cloud strategy:** `voice_favorites(voice_id, owner_id)` table. Multi-user favorites require per-user tracking.

**Migration path:** See SPEC §11.5. A single migration populates the Cloud table from CE booleans.

### D10: VoiceDetailPanel — Canonical Voice Surface

**The rule:** There is exactly one `VoiceDetailPanel` component. It accepts `Voice | VoiceResource`. It renders the same layout for every voice type. Sections collapse when data is unavailable.

**Why a single component:**
- Prevents the fragmentation that caused the six bug classes (presets treated as clones, missing previews, wrong badges, etc.).
- Ensures consistent UX across Library, Presets, Marketplace, and Imported voices.
- A single component has a single test suite, a single maintenance burden, and a single evolution path.
- New voice types (e.g., marketplace, trained) get the correct panel automatically — no new component needed.

**Layout:** Header → Overview → Previews → Compatible Models → Variants → Actions. This order is the same for every voice type.

**Action branching:** The component does not branch on voice type for layout. It branches only for action availability:
- `Voice` → actions: Use in TTS, Export, Delete, Favorite
- `VoiceResource` (not in library) → actions: Import to Library, Preview

### D11: Primary Model and Recommended Model

**primary_model_id** (persisted): The model that originally created this voice. Set at voice creation, never changes.

**recommended_model_id** (derived): The model predicted to produce the best result for this voice. Computed by CompatibilityResolver or a ranking heuristic.

**Why both:**
- `primary_model_id` anchors the voice to its origin — a Kokoro preset always has `primary_model_id = "kokoro-base"`, even when variants exist for other models.
- `recommended_model_id` adapts over time — if a newer model produces better clones of SOURCE_ASSET voices, the recommendation can shift without changing the primary.
- Together they give the frontend a clear model selection strategy: pre-select primary, offer recommended as alternative, show full compatible list for advanced users.

**Voice-First alignment:**
- The voice knows its own model preference. The user doesn't need to know or care.
- Model selection becomes automatic for the common case. The model selector is an advanced override.
- This is strictly additive — `null` values mean the frontend falls back to existing behavior.
