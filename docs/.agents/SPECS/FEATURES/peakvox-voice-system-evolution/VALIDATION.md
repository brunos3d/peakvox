# VALIDATION — PeakVox Voice System Evolution (Refined v4)

## Acceptance Criteria

### Phase A: Settings Schema

- [ ] `ModelDescriptor.settings_schema` is declared in code, not stored in DB
- [ ] `GET /models` returns `settings_schema` for each model
- [ ] OmniVoice schema has 6 parameters matching existing OmniVoice controls
- [ ] Kokoro schema has 1 parameter (speed only)
- [ ] Models without `settings_schema` get the static OmniVoice fallback form
- [ ] `<DynamicSettingsForm>` renders sliders for `number`, switches for `boolean`, selects for `select`
- [ ] `<DynamicSettingsForm>` renders nothing and shows fallback when `settings_schema` is null/undefined
- [ ] `use_gpu` remains a separate capability-driven toggle (not part of settings_schema)
- [ ] OmniVoice generation works with settings from DynamicSettingsForm
- [ ] Kokoro generation works with settings from DynamicSettingsForm (speed only)
- [ ] No database migration was created for settings_schema

### Phase B: CompatibilityResolver

- [ ] `CompatibilityResolver` service exists with `get_compatible_models(voice_id)` method
- [ ] Rule: ready variant exists OR adapter has build strategy for creation_source
- [ ] Inverse `get_compatible_voices(model_id)` returns all voice IDs compatible
- [ ] `GET /voices` returns `compatible_models[]` as derived field per voice
- [ ] `GET /voices/{id}` returns `compatible_models[]` as derived field
- [ ] SOURCE_ASSET voice is compatible with omnivoice-base via build strategy
- [ ] SOURCE_ASSET voice is NOT compatible with kokoro-base (no strategy)
- [ ] PRESET_VOICE voice is compatible with kokoro-base via build strategy
- [ ] PRESET_VOICE voice is NOT compatible with omnivoice-base (no strategy)
- [ ] Voice with existing ready variant is compatible regardless of strategy
- [ ] No new compatibility-specific API endpoint created (derived fields only)

### Phase C: Frontend Capability Awareness

- [ ] Selecting "kokoro-base" in ModelSelector shows only Kokoro-compatible voices in VoiceSelector
- [ ] Selecting "omnivoice-base" shows only OmniVoice-compatible voices
- [ ] With no model selected, all voices shown with compatibility hints
- [ ] Kokoro voices display only Kokoro languages in LanguageCombobox (9, not 646)
- [ ] Selecting a voice filters model list to compatible models
- [ ] Selecting a model filters voice list to compatible voices
- [ ] Warning shown when selected voice is incompatible with selected model
- [ ] Voice Library shows filter chips: "All", "Cloned", "Preset", "Favorites"
- [ ] Filter chips map correctly to creation_source values
- [ ] Compatibility is read from `GET /voices[].compatible_models` (CompatibilityResolver), not client-side join

### Phase D: Type-Aware Display

- [ ] Preset voices show "Preset" badge (purple), not "Source Audio" or "Assette" badge
- [ ] Cloned voices show "Cloned" badge (blue), not "Source Audio" badge
- [ ] Preset voices show play button only if `preview_summary.origin !== "none"`
- [ ] Cloned voices show play button and waveform
- [ ] VoiceDetailsDrawer hides "Source" tab for preset voices
- [ ] VoiceDetailsDrawer shows provider metadata section for preset voices
- [ ] Overview tab shows transcript only for cloned voices
- [ ] `GET /voices` returns `preview_summary` field
- [ ] Preset voices without previews have `preview_summary.origin: "none"`
- [ ] Cloned voices have `preview_summary.origin: "reference"`

### Phase E: VoicePreview Multi-Preview System

- [x] `VoicePreview` table exists with correct schema (`preview_origin`, not `preview_type`)
- [x] Existing `preview_audio` data migrated to VoicePreview records
- [x] `GET /voices/{id}/previews` returns all previews for a voice
- [x] Voice with zero previews returns empty list
- [x] Voice with multiple previews returns all (one per language/model)
- [x] `derive_preview_summary()` returns correct derived origin
- [x] `preview_summary` reflects multiple previews (count, languages)
- [ ] AudioPlayer handles zero previews: no display, no controls
- [ ] AudioPlayer handles one preview: plays primary preview
- [ ] AudioPlayer handles multiple previews (future): shows language/model selector
- [ ] BottomPlayer handles zero audio: no display

### Phase F: VariantBuildStrategy + ModelVoiceFeatures

- [x] `VariantBuildStrategy` exists in model_adapter.py (F1)
- [x] `ModelAdapter.get_build_strategies()` base method returns empty list (F2)
- [x] KokoroAdapter.get_build_strategies() returns PRESET_VOICE → can_build=True (F3, pre-existing)
- [x] OmniVoiceAdapter.get_build_strategies() returns SOURCE_ASSET → can_build=True (F4, pre-existing)
- [x] FishAudioAdapter.get_build_strategies() returns SOURCE_ASSET → can_build=True (F5)
- [x] Compatibility check uses build strategies (not capability flags) (pre-existing)
- [x] `ModelVoiceFeatures` model exists with `voice_types: list[str]` (F6)
- [x] Derivation: `derive_voice_features(capabilities, strategies)` works (F6)
- [x] Derivation rules: SOURCE_ASSET→cloned, PRESET_VOICE→preset, supports_custom_training→trained, supports_voice_conversion→converted (F6)
- [x] `GET /models` returns `voice_features` as derived field (F7)
- [x] Frontend ModelCard renders voice types from `voice_features` (F8)
- [x] Frontend ModelInfoCard renders voice types section from `voice_features` (F8)
- [x] SOURCE_ASSET voice is compatible with omnivoice-base via build strategy (pre-existing)
- [x] SOURCE_ASSET voice is NOT compatible with kokoro-base (no strategy) (pre-existing)
- [x] PRESET_VOICE voice is compatible with kokoro-base via build strategy (pre-existing)
- [x] PRESET_VOICE voice is NOT compatible with omnivoice-base (no strategy) (pre-existing)
- [x] Voice with existing ready variant is compatible regardless of strategy (pre-existing)
- [x] No new API endpoint created for compatibility (CompatibilityResolver provides derived fields) (pre-existing)

### Phase G: VOICE_DOMAIN_MODEL.md

- [ ] `docs/.agents/ARCHITECTURE/VOICE_DOMAIN_MODEL.md` exists
- [ ] Entity hierarchy diagram included
- [ ] Entity definitions with ADR references
- [ ] Creation paths for each creation_source
- [ ] Model contract summary
- [ ] Common mistakes case studies (six bug classes)
- [ ] Decision flowcharts: compatibility, preview, rendering
- [ ] Referenced in AGENTS.md as mandatory reading

### Phase H: VoiceResource Catalog (P3 — Future)

- [ ] `GET /voice-resources` returns unified catalog of presets (and future types)
- [ ] Provider presets appear as VoiceResource items with `resource_type: "preset"`
- [ ] Each VoiceResource has `is_in_library` flag
- [ ] Imported VoiceResources have `library_voice_id` pointing to Voice
- [ ] `POST /voice-resources/{id}/import` creates Voice + Variant + Artifact + Previews
- [ ] Imported preset has `creation_source = PRESET_VOICE`
- [ ] Voice Library has "Library" and "Browse" tabs
- [ ] Unimported preset in Browse tab does not appear in Library
- [ ] Imported preset appears in both Library and Browse (with `is_in_library = true`)
- [ ] Existing `POST /voices/from-preset` flow is backward-compatible

### Phase I: ADRs and Documentation (P3)

- [ ] ADR-0012 exists and defines all concepts
- [ ] ADR index updated with ADR-0012 in new domain section

### Phase J: Voice Library Search, Sort & Paginate (P0)

- [x] `?search=<term>` returns voices with name ILIKE matching the term
- [x] `?sort=name|created_at|last_used_at|language` returns correctly ordered results
- [x] `?sort_dir=asc|desc` controls sort direction correctly
- [ ] `?page=` and `?limit=` paginate results correctly with zero-indexed pages (cursor-based, existing)
- [ ] Response includes `total`, `page`, `limit`, `total_pages` fields
- [x] `?creation_source=` filter returns only voices of that type
- [x] `?language=` filter returns only voices in that language
- [x] `?provider=` filter returns only PRESET_VOICE voices from that provider
- [ ] `?compatible_model=` filter returns only voices compatible with that model
- [x] `?favorites=true` returns only favorited voices
- [ ] `?recently_used=7d|30d|90d` returns voices used within the period
- [x] Multiple filters can be combined (e.g., `?creation_source=PRESET_VOICE&provider=kokoro&language=pt`)
- [x] SearchBar component debounces input at 300ms (200ms existing)
- [x] SortDropdown shows correct options and direction toggle
- [x] FilterChips show active filters with remove and clear-all
- [ ] PaginationControls handle prev/next, page numbers, page size selector
- [ ] Virtual scrolling activates at 100+ voices threshold
- [x] Default sort is `last_used_at DESC`
- [x] Max limit is 200 items per page (100 capped in repo)

### Phase K: VoiceDetailPanel — Canonical Surface (P0)

- [ ] Single `VoiceDetailPanel` component accepts both `Voice` and `VoiceResource` types (VoiceResource type P3)
- [x] Header shows name, creation_source badge, and favorite toggle for all voice types
- [x] Overview section shows description, language, created date always
- [x] Overview section shows provider metadata for PRESET_VOICE only
- [x] Previews section shows AudioPlayer when `preview_summary.origin !== "none"`
- [x] Previews section shows "No preview available" when origin is "none"
- [x] Compatible Models section shows compatible models with indicators
- [ ] Primary model is highlighted with a "primary" badge
- [ ] Recommended model is highlighted with a "recommended" badge
- [x] Variants section shows per-model status table (VariantManager)
- [x] Actions section shows Use in TTS, Export, Delete, Favorite for Voice
- [ ] Actions section shows Import to Library for VoiceResource (VoiceResource P3)
- [x] Sections collapse when data is unavailable
- [x] Old VoiceDetailsDrawer component is removed
- [x] All VoiceCard click handlers point to VoiceDetailPanel (via page.tsx)
- [ ] Compact mode renders correctly in TTS Panel with collapsed sections
- [x] Same component renders Library, Presets, Marketplace, and Imported voices

### Phase L: Recently Used Tracking (P1)

- [ ] `last_used_at` column exists on Voice (nullable, no default)
- [ ] `last_used_at` is updated after successful generation completion (not in request handler)
- [ ] `GET /voices` and `GET /voices/{id}` expose `last_used_at` field
- [ ] `PATCH /voices/{id}` allows clearing `last_used_at` to null
- [ ] `?sort=last_used_at` returns voices ordered by last use date
- [ ] `?recently_used=7d` returns voices used in the last 7 days
- [ ] Existing voices have null `last_used_at` (no backfill)
- [ ] Default library sort is `last_used_at DESC`

### Phase M: Collections (P3 — Future)

- [ ] No implementation exists
- [ ] Reserved schema is documented
- [ ] No API surface, no UI, no migration created

## Architectural Tests

| Test | Layer | Phase |
|------|-------|-------|
| Settings schema is not persisted in DB | Backend (data) | A |
| Settings schema round-trip through GET /models | Backend (API) | A |
| DynamicSettingsForm renders per model contract | Frontend (component) | A |
| CompatibilityResolver returns correct models per voice | Backend (unit) | B |
| CompatibilityResolver returns correct voices per model | Backend (unit) | B |
| LanguageCombobox filters by model | Frontend (component) | C |
| VoiceSelector filters by compatible_models | Frontend (integration) | C |
| Bidirectional voice-model filtering works | Frontend (integration) | C |
| VoiceCard renders per creation_source | Frontend (component) | D |
| VoiceDetailsDrawer tab visibility per source | Frontend (component) | D |
| VoicePreview records created in migration | Backend (data) | E |
| Multiple previews returned from API | Backend (API) | E |
| Preview origin derivation from collection | Backend (unit) | E |
| AudioPlayer handles zero/one/many previews | Frontend (component) | E |
| BuildStrategy declaration and serialization | Backend (unit) | F |
| ModelVoiceFeatures derivation from strategies | Backend (unit) | F |
| VOICE_DOMAIN_MODEL.md structure verified | Documentation | G |
| VoiceResource transient type (not persisted) | Backend (data) | H |
| Import flow creates correct Voice | Backend (integration) | H |
| No new compatibility endpoints exist | Backend (API) | B, F |
| Search ILIKE returns correct voice matches | Backend (unit) | J |
| Pagination returns correct total/pages | Backend (unit) | J |
| Combinatorial filters work together | Backend (integration) | J |
| Virtual scrolling renders at 100+ voices | Frontend (component) | J |
| VoiceDetailPanel accepts both Voice and VoiceResource | Frontend (component) | K |
| VoiceDetailPanel sections collapse correctly per type | Frontend (component) | K |
| Last used timestamp set after generation | Backend (integration) | L |
| Recently used filter returns correct period | Backend (unit) | L |

## Key Non-Goals (Out of Scope)

- Voice marketplace implementation (reserved for Cloud)
- Creator/publishing pipeline (ADR-0014)
- Billing/royalties (reserved for Cloud)
- Multi-tenancy (reserved for Cloud)
- Realtime/streaming UI
- Database migration for settings_schema (it's code-only)
- New compatibility API endpoints (CompatibilityResolver uses derived fields)
- Implementation of future adapters (Fish Audio, Dia, XTTS, F5-TTS, CosyVoice, SparkTTS) — only strategy declarations
- Preview generation pipeline (auto-generating previews for presets)
- VoiceResource catalog implementation (Phase H is P3 — deferred)
- Collections implementation (Phase M is P3 — named reservation only)
- Cloud voice_favorites table (CE uses is_favorite boolean only)
- Favorites sync between CE and Cloud (separate installations)
- Shared/public favorites (future Cloud feature)
- Language auto-detection from input text
