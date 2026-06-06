# TASKS — PeakVox Voice System Evolution (Refined v4)

## Key Changes from v3

- **Added:** Voice Library UX scale primitives (Phase J) — search, sort, paginate, filter, virtual scroll
- **Added:** VoiceDetailPanel canonical surface (Phase K) — single component for all voice types
- **Added:** Recently Used tracking (Phase L) — `last_used_at` column, generation hook
- **Added:** Collections named reservation (Phase M) — future, no implementation
- **Added:** Favorites design — `Voice.is_favorite` boolean for CE, `voice_favorites` table for Cloud
- **Added:** `primary_model_id` (persisted) and `recommended_model_id` (derived) to voice contract

## Key Changes from v2

- **Added:** CompatibilityResolver as canonical source of truth (Phase B)
- **Added:** ModelVoiceFeatures derived view (Phase F)
- **Added:** VOICE_DOMAIN_MODEL.md canonical document (Phase G)
- **Renamed:** `preview_type` → `preview_origin` throughout (Phase E)
- **Moved:** VoiceResource catalog to Phase H (P3 — deferred after P0/P1)
- **Removed:** All client-side compatibility algorithms (replaced by CompatibilityResolver)
- **Rephased:** Preview (E) and BuildStrategy (F) now after compatibility resolver (B)

---

## Phase A: Model Settings Contract — Code Declaration (P0)

### A1 — Add `SettingsSchema` types to registry_types.py

- Add `SettingsSchema`, `ParameterSchema`, `SelectOption` Pydantic models
- Add `settings_schema: SettingsSchema | None = None` field to `ModelDescriptor`
- NOT persisted in DB — code-level declaration only

### A2 — Seed `settings_schema` in model_catalog.py

- OmniVoice: num_step, guidance_scale, speed, duration, t_shift, denoise
- Kokoro: speed only
- Future models: their own schemas (Fish Audio, Dia, XTTS, F5-TTS, CosyVoice, SparkTTS)

### A3 — Expose `settings_schema` in GET /models

- Serialize `ModelDescriptor.settings_schema` in the API response
- Backward compat: field is `null`/absent for older model definitions

### A4 — Create `<DynamicSettingsForm>` component

- Generic React component that iterates `model.settings_schema.properties`
- Renders sliders for `type: "number"`, switches for `type: "boolean"`, selects for `type: "select"`
- Falls back to static OmniVoice form when `settings_schema` is null

### A5 — Replace static GenerationSettingsFields

- Swap static fields in `GenerationPanel.tsx` for `<DynamicSettingsForm>`
- Keep hardcoded values as default for legacy models without `settings_schema`
- Keep `use_gpu` as a separate capability-driven toggle

## Phase B: CompatibilityResolver (P0)

### B1 — Create CompatibilityResolver service class

- New service: `CompatibilityResolver(db, adapters)`
- Core method: `get_compatible_models(voice_id) → list[str]`
- Rule: ready variant exists OR adapter has build strategy for creation_source

### B2 — Implement `get_compatible_voices(model_id)` inverse

- Given a model, returns all voice IDs compatible via variant OR build strategy
- Used for future server-side voice filtering

### B3 — Expose `compatible_models` on GET /voices

- Add `compatible_models: list[str]` derived field to each voice in list response
- Computed by CompatibilityResolver at query time

### B4 — Expose `compatible_models` on GET /voices/{id}

- Same derived field for single voice response

### B5 — Expose `compatible_voices` on GET /models/{id} (optional)

- Derived field, available for future server-side filtering
- Absent = frontend falls back to client-side filtering

## Phase C: Frontend Capability Awareness (P0)

### C1 — Filter LanguageCombobox by model

- When `activeModel.supported_languages` is non-empty, filter to those
- When empty (`[]` = auto/all), show all languages
- Keep "Auto" option (language = null) always available

### C2 — Filter VoiceSelector by `compatible_models`

- Read `voice.compatible_models` from API response (from CompatibilityResolver)
- When a model is selected, show only compatible voices
- When no model is selected, show all voices
- Show count badges: "Compatible (3) · Not compatible (5)"

### C3 — Bidirectional filtering in TTS panel

- Voice selection → filter model list to compatible models
- Model selection → filter voice list to compatible voices
- Show compatibility warning: "This voice is not compatible with the selected model"

### C4 — Add `creation_source` filter chips to Voice Library

- Filter chips: "All", "Cloned" (SOURCE_ASSET), "Preset" (PRESET_VOICE), "Favorites"
- Map to `?creation_source=` API parameter (already exists)
- Show count of each type

## Phase D: Type-Aware Voice Display (P0)

### D1 — Creation source config map

- Create `creationSourceConfig` mapping: colors, icons, labels per source
- SOURCE_ASSET → `bg-blue-100 text-blue-700`, "Cloned"
- PRESET_VOICE → `bg-purple-100 text-purple-700`, "Preset"
- MARKETPLACE_VOICE → `bg-amber-100 text-amber-700`, "Marketplace" (future)
- TRAINED_VOICE, IMPORTED_VOICE, SYSTEM_VOICE → future values, use generic fallback

### D2 — Conditional VoiceCard rendering

- Show play button only if `preview_summary.origin !== "none"`
- Show duration only if `preview_summary.origin !== "none"`
- Show provider badge for PRESET_VOICE (from `meta.provider`)
- Hide transcript line for PRESET_VOICE
- Show "Cloned" / "Preset" badge from `creation_source`

### D3 — Conditional VoiceDetailsDrawer tabs

- Hide "Source" tab for PRESET_VOICE voices
- Hide waveform for PRESET_VOICE voices (no reference audio)
- Hide transcript for PRESET_VOICE voices

### D4 — Provider metadata section in details drawer

- Add section to Overview tab for PRESET_VOICE
- Show: provider name, preset name, supported languages, compatible models
- Use existing `meta` and variant `params` data

### D5 — Add `preview_summary` to API responses

- Return derived `preview_summary` field in `GET /voices` list
- Return derived `preview_summary` in `GET /voices/{id}`
- Initially derived from `preview_audio` + `creation_source` (Phase E makes it richer)

## Phase E: VoicePreview Multi-Preview System (P1)

### E1 — Create VoicePreview table

- New table: `voice_previews` (id, voice_id, preview_origin, language, source_model_id, storage_key, duration, created_at)
- Add model class in `models/db.py`
- Add relationship on Voice

### E2 — Migration: preview_audio → VoicePreviews

- For each Voice with `preview_audio`, create a VoicePreview record
- SOURCE_ASSET → preview_origin = "reference"
- PRESET_VOICE (with preview) → preview_origin = "provider"
- Keep `preview_audio` column as fallback during transition

### E3 — Add GET /voices/{id}/previews

- Returns list of VoicePreviews for a voice
- Supports filtering by language, preview_origin, source_model_id

### E4 — Add `derive_preview_summary()` helper

- Computes derived preview origin from VoicePreviews collection
- Returns `{origin, count, languages}`
- Not stored — computed at read time

### E5 — Update GET /voices and GET /voices/{id}

- Add `preview_summary` derived field using `derive_preview_summary()`
- Use VoicePreview records if available, fall back to `preview_audio` column

### E6 — Update AudioPlayer for multi-preview

- Show primary preview (prefer reference > generated > provider)
- Handle zero previews: no display
- Handle multiple previews: future language/model selector

### E7 — Update BottomPlayer

- Handle zero audio: no display, no control

## Phase F: VariantBuildStrategy + ModelVoiceFeatures (P1)

### F1 — Add VariantBuildStrategy model

- Add `VariantBuildStrategy` Pydantic model: creation_source, can_build, requires, description
- Add to `registry_types.py`

### F2 — Add `get_build_strategies()` to ModelAdapter base class

- Static method returning `list[VariantBuildStrategy]`
- Default implementation returns empty list

### F3 — Implement strategies for KokoroAdapter

- `PRESET_VOICE` → can_build=True, requires=["preset_name", "provider"]

### F4 — Implement strategies for OmniVoiceAdapter

- `SOURCE_ASSET` → can_build=True, requires=["source_asset"]

### F5 — Implement strategies for future adapters

- Fish Audio, Dia, XTTS, F5-TTS, CosyVoice, SparkTTS
- Each declares its own build strategies as they are implemented
- No strategies = only variants created by external means are compatible

### F6 — Add ModelVoiceFeatures model and derivation

- Add `ModelVoiceFeatures` Pydantic model: `voice_types: list[literal]`
- Derivation rules from build strategies + capabilities:
  - `SOURCE_ASSET → can_build=True` → includes "cloned"
  - `PRESET_VOICE → can_build=True` → includes "preset"
  - `supports_custom_training` → includes "trained"
  - `supports_voice_conversion` → includes "converted"

### F7 — Expose `voice_features` on GET /models

- Add `voice_features` derived field to model API response
- Frontend uses this for "Supports: cloning + preset" badges

## Phase G: VOICE_DOMAIN_MODEL.md (P1)

### G1 — Create canonical domain document

- Create `docs/.agents/ARCHITECTURE/VOICE_DOMAIN_MODEL.md`
- Entity hierarchy diagram (Mermaid or ASCII)
- Entity definitions with ADR references for each type
- Creation paths showing how each creation_source produces a Voice
- Model contract summary: capabilities, settings_schema, build_strategies, voice_features
- Common mistakes case studies (the six bug classes from production history)
- Decision flowcharts: compatibility, preview rendering, type-aware display
- Reference in AGENTS.md as mandatory reading for all future feature work

## Phase H: VoiceResource Catalog (P3 — Future)

### H1 — Define VoiceResource transient type

- API-facing type (not DB entity): resource_id, resource_type, name, description, language, previews, provider_metadata, compatible_models, is_in_library, library_voice_id

### H2 — Unify provider presets as GET /voice-resources

- Adapter `list_provider_voices()` becomes the data source for `resource_type=preset`
- Returns unified format: `VoiceResource` type
- Includes `is_in_library` by checking if a Voice with same provider+preset exists

### H3 — Create POST /voice-resources/{id}/import

- Takes a VoiceResource (preset, marketplace listing, etc.)
- Creates: Voice + VoiceVariant + Artifact + VoicePreviews (if previews exist)
- Sets creation_source from resource_type mapping
- Returns the created Voice

### H4 — Update frontend Voice Library with "Browse" tab

- Tab bar: "Library" | "Browse"
- "Library" shows `GET /voices` (current behavior, with new type-aware cards)
- "Browse" shows `GET /voice-resources`, grouped by resource_type
- Each browse item has "Add to Library" action

### H5 — Update existing POST /voices/from-preset

- Refactor to use the import boundary concept
- Preset descriptor is a VoiceResource; import creates the Voice
- Behavior is the same; internal boundary becomes explicit

## Phase I: ADRs and Documentation (P3)

### I1 — Write remaining ADRs as needed

- ADR-0013: Model Categories (reserved)
- ADR-0014: Marketplace Voice Publishing (reserved)
- ADR-0015: Imported Voice Ecosystem (reserved)

### I2 — Update implementation plans

- Reference ADR-0012 in all Phase H tasks
- Reference Settings Schema decision in Phase A tasks
- Reference VariantBuildStrategy in Phase F tasks

## Phase J: Voice Library Search, Sort & Paginate (P0)

### J1 — Add search query param to GET /voices

- `?search=<term>` — ILIKE match on `voice.name`
- Backend: `WHERE name ILIKE '%<term>%'`
- Frontend: debounced SearchBar component (300ms delay)

### J2 — Add sort query param to GET /voices

- `?sort=name` — alphabetical
- `?sort=created_at` — by creation date (default desc)
- `?sort=last_used_at` — by last use date (default desc, default sort)
- `?sort=language` — by language code
- Direction: `?sort_dir=asc|desc` (default varies by field)

### J3 — Add pagination query params to GET /voices

- `?page=0` (zero-indexed, default 0)
- `?limit=50` (default 50, max 200)
- Response: `{items: [], total: int, page: int, limit: int, total_pages: int}`

### J4 — Add filter query params to GET /voices

- `?creation_source=SOURCE_ASSET|PRESET_VOICE|...` — filter by origin
- `?language=pt` — filter by voice language
- `?provider=kokoro` — filter PRESET_VOICE voices by source provider
- `?compatible_model=omnivoice-base` — filter by CompatibilityResolver
- `?favorites=true` — only favorited voices
- `?recently_used=7d|30d|90d` — voices used within the period

### J5 — Create SearchBar component

- Text input with search icon
- Debounced input (300ms) triggers `?search=` API call
- Clear button resets search
- Loading indicator during API call

### J6 — Create SortDropdown component

- Dropdown with sort options: Name, Created Date, Last Used, Language
- Direction toggle (asc/desc)
- Default: Last Used (desc)

### J7 — Create FilterChips component

- Shows active filters as removable chips
- "Clear all" button when filters active
- Count badge per chip type

### J8 — Create PaginationControls component

- Page navigation: prev, next, page numbers
- Page size selector: 25, 50, 100, 200
- Total count display: "Showing 1-50 of 1,234 voices"

### J9 — Implement virtual scrolling in voice list

- Use react-window or react-virtuoso
- Threshold: enable at 100+ voices
- Fixed height in list mode, variable in grid mode
- Intersection observer for infinite scroll (alternative to pagination controls)

### J10 — Wire recently_used filter

- `?recently_used=7d` → `WHERE last_used_at >= NOW() - INTERVAL '7 days'`
- Options: 7d, 30d, 90d
- Frontend: quick filter buttons in library header

## Phase K: VoiceDetailPanel — Canonical Surface (P0)

### K1 — Create single VoiceDetailPanel component

- Accepts `Voice | VoiceResource` via discriminated union
- Single component for all voice types: Library, Preset, Marketplace, Imported
- No branching on type for layout — branches for action availability only

### K2 — Implement Header section

- Voice name (large title)
- `creation_source` badge with color/icon per source type
- Favorite toggle (star/heart icon, calls PATCH /voices/{id})
- Close/dismiss button

### K3 — Implement Overview section

- Description (from voice.meta)
- Language display
- Created date (formatted)
- Provider metadata (PRESET_VOICE only): provider name, preset name
- Collapsed when section has no data

### K4 — Implement Previews section

- AudioPlayer with waveform visualization
- Preview language selector (when multiple previews exist)
- "No preview available" message when `preview_summary.origin === "none"`
- Duration display for available previews

### K5 — Implement Compatible Models section

- List of compatible models with checkmark indicators
- Primary model highlighted with "primary" badge
- Recommended model highlighted with "recommended" badge
- Incompatible models shown with X indicator (why not compatible)

### K6 — Implement Variants section

- Per-model variant status table:
  | Model | Status | Version | Actions |
- Actions: Build, Rebuild, View Artifacts
- Empty state: "No variants yet" with Build button if build strategy exists

### K7 — Implement Actions section

- Use in TTS — opens TTS panel with this voice pre-selected
- Export — downloads variant artifacts (future)
- Delete — confirms then deletes voice
- Favorite — toggle (duplicated from header for accessibility)
- Conditional: if VoiceResource → "Import to Library" replaces Delete

### K8 — Replace existing VoiceDetailsDrawer usage

- Replace all uses of VoiceDetailsDrawer with VoiceDetailPanel
- Remove old VoiceDetailsDrawer component
- All click handlers on VoiceCard point to VoiceDetailPanel

### K9 — Add compact mode for TTS Panel

- VoiceDetailPanel renders in compact mode when embedded in TTS Panel
- Actions section: "Use in TTS" is the primary action
- Sections initially collapsed except Overview and Previews

## Phase L: Recently Used Tracking (P1)

### L1 — Add last_used_at column

- `ALTER TABLE voices ADD COLUMN last_used_at TIMESTAMP;`
- Nullable — existing voices are not backfilled
- No default value

### L2 — Update generation completion handler

- In the generation completion handler (after successful generation), set `voice.last_used_at = NOW()`
- NOT in the request handler — only set after successful output
- No additional latency: UPDATE is a fast single-row operation

### L3 — Expose last_used_at in API

- `GET /voices` and `GET /voices/{id}` include `last_used_at` field
- `PATCH /voices/{id}` — allows clearing `last_used_at` (set to null)

### L4 — Wire sort and filter

- `?sort=last_used_at` — sort by last use date (default sort for library)
- `?recently_used=7d|30d|90d` — filter by recency
- `PATCH /voices/{id}` with `{"last_used_at": null}` — clear tracking

## Phase M: Collections (P3 — Future)

### M1 — Named reservation only

- No implementation
- Document reserved schema:
  - `voice_collections` (id, name, description, owner_id, created_at)
  - `voice_collection_members` (id, collection_id, voice_id, sort_order)
- No API surface, no UI, no migration
