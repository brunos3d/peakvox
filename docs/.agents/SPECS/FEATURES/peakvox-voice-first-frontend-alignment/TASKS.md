# TASKS — PeakVox Voice-First Frontend Alignment

## Phase N: Frontend Architecture Alignment (P0)

### N1 — Fix "Use Now" (Temporary Preset Selection)

- [ ] Add `TemporaryVoice` interface to `types/index.ts`
- [ ] Add discriminated union `selectedVoice: VoiceProfile | TemporaryVoice | null` to store
- [ ] Add `selectVoiceTemporary(resource: VoiceResourceResponse)` action to store
- [ ] Update `PresetVoicesTab.tsx`: "Use Now" calls `selectVoiceTemporary()`, does NOT call `importVoiceResource()`
- [ ] Update `PresetVoicesTab.tsx`: rename button from "Use Now" to "Use in TTS"
- [ ] Add Preview button to preset card (plays `preview_audio_url`)
- [ ] Update `VoiceSelector.tsx`: show "(Preset)" subtitle for temporary voices
- [ ] Add "Import to Library" button in TTS panel when temporary voice selected
- [ ] Ensure temporary voice is discarded when selecting a different voice or leaving TTS page
- [ ] Update API layer: `fetchVoiceResources` type handling

### N2 — Add `primary_model_id` / `recommended_model_id` Support

- [ ] Add `primaryModelId: string | null` and `recommendedModelId: string | null` to `VoiceProfile` type
- [ ] Add `useModelForVoice` hook with selection priority (primary → recommended → first compatible → null)
- [ ] Update `ModelSelector.tsx` to highlight primary model with "Primary" badge
- [ ] Update `GenerationPanel.tsx` auto-switch effect to use `useModelForVoice` (remove guard `!selectedModelId`)
- [ ] Update `VoiceSelector.tsx` subtitle to show primary model name when available
- [ ] Update `VoiceDetailPanel.tsx` Compatible Models section to highlight primary/recommended

### N3 — Model-Scoped Generation Settings

- [ ] Replace `GenerationSettings` hardcoded type with `Record<string, unknown>` reference
- [ ] Replace `GenerationRequest` hardcoded OmniVoice fields with `params?: Record<string, unknown>`
- [ ] Replace `generationSettings` in store with `modelSettings: Record<string, Record<string, unknown>>`
- [ ] Add `initializeSettingsFromSchema(model: Model)` helper
- [ ] Add model switch logic: save current → load new (or initialize from schema)
- [ ] Add `filterSettingsForModel(settings, schema)` helper
- [ ] Update `GenerationPanel.tsx` to filter `generationSettings` by model's `settings_schema` before submission
- [ ] Update `DynamicSettingsForm.tsx` to accept `Record<string, unknown>` values
- [ ] Update `GenerationSettingsFields.tsx` to wire per-model settings
- [ ] Add migration in store init: assign current flat settings to current model's key

### N4 — Fix VoiceDetailPanel Type Leaks

- [ ] Gate transcript display on `creation_source === "SOURCE_ASSET"` (not truthy `profile.transcript`)
- [ ] Gate provider metadata on `creation_source === "PRESET_VOICE"` (not truthy `meta.provider`)
- [ ] Gate preview audio — use provider preview URL for PRESET_VOICE, `getVoiceAudioUrl` for SOURCE_ASSET
- [ ] Gate usage count / created date / last used — hide for VoiceResource and TemporaryVoice
- [ ] Add Export action to Actions section (download variant artifacts)
- [ ] Add "Import to Library" action for temporary voices in VoiceDetailPanel

### N5 — Create PaginationControls Component

- [ ] Create `PaginationControls` component (prev, next, page numbers, page size selector)
- [ ] Page size options: 25, 50, 100, 200
- [ ] Total count display: "Showing 1-{limit} of {total} voices"
- [ ] Wire into `voices/page.tsx` — translate page/pageSize to cursor-based API calls
- [ ] Handle edge cases: empty results, single page, last page

### N6 — Implement Virtual Scrolling

- [ ] Add `react-virtuoso` dependency
- [ ] Create `VirtualVoiceGrid` component wrapping react-virtuoso
- [ ] Threshold: activate at 100+ voices, use normal `VoiceGrid` below 100
- [ ] Preserve scroll position on filter/sort changes
- [ ] Test at 200+ voice threshold for performance

### N7 — Add Compatible Model and Provider Filters to Library

- [ ] Add `?compatible_model=` filter chip in FilterBar (dropdown of active models)
- [ ] Add `?provider=` filter chip in FilterBar (dropdown of providers from current results)
- [ ] Verify backend support for `?compatible_model=` and `?provider=` on `GET /voices`
- [ ] Fall back to client-side filtering if backend does not support query params
- [ ] Update `VoiceQueryFilters` type if needed

### N8 — Make VariantDashboard Compatibility-Aware

- [ ] Add compatibility data to variant matrix cells from `voice.compatibleModels`
- [ ] Three distinct states: Ready (✅), Buildable (○), Incompatible (✗)
- [ ] Update icons and colors per SPEC §10
- [ ] Add tooltips: "No build strategy for {creation_source} voices" for incompatible
- [ ] Add tooltips: "No variant yet. Click to build." for buildable
- [ ] Ensure backfill only processes compatible voice×model pairs

### N9 — Per-Model Settings Persistence (Store Only)

- [ ] Ensure `modelSettings` is persisted to localStorage (or sessionStorage) so per-model settings survive page reloads
- [ ] Add storage key: `peakvox-model-settings-{modelId}`
- [ ] Add cleanup: remove entries for models that no longer exist
- [ ] Handle serialization edge cases (functions, DOM nodes, circular refs)

## Phase O: Validation & Status Cleanup

### O1 — Update peakvox-voice-system-evolution STATUS.md

- [ ] Correct J8 (PaginationControls) from "completed" to "not implemented"
- [ ] Correct J9 (Virtual scrolling) from "completed" to "not implemented"
- [ ] Correct K9 (Compact mode) from "completed" to "not implemented"
- [ ] Update completed list to show: "A, B, C (partial), D (partial), E, F, G, H, J (partial), K (partial), L"

### O2 — Update peakvox-voice-system-evolution VALIDATION.md

- [ ] Mark J8 validation criteria as not met (PaginationControls)
- [ ] Mark J9 validation criteria as not met (Virtual scrolling)
- [ ] Mark K9 validation criteria as not met (Compact mode)
- [ ] Add transcript leak validation for PRESET_VOICE
- [ ] Add provider metadata leak validation for non-PRESET_VOICE

## Verification

- [ ] Full frontend build: `npm run build` (or `next build`) clean
- [ ] Lint: `npm run lint` clean
- [ ] TypeScript: `npx tsc --noEmit` clean
- [ ] Backend tests (if applicable): `docker compose run --rm backend python -m pytest tests/ -q`
- [ ] Manual walkthrough of all 10 user journey scenarios from SPEC §13
- [ ] Update `docs/.agents/IMPLEMENTATION/EXECUTION_HISTORY/EXECUTION_LEDGER.md`
- [ ] Update `docs/.agents/IMPLEMENTATION_STATUS.md`
- [ ] Update `docs/.agents/PROJECT_STATE.md`
- [ ] When complete: update STATUS.md → VALIDATED

---

Related: `SPEC.md` · `DESIGN.md` · `VALIDATION.md`
