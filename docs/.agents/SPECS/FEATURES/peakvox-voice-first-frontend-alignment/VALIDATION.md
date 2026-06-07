# VALIDATION — PeakVox Voice-First Frontend Alignment

## Acceptance Criteria

### N1 — Fix "Use Now" (Temporary Preset Selection)

- [ ] "Use in TTS" does NOT create VoiceProfile, VoiceVariant, or VoiceVariantArtifact
- [ ] "Use in TTS" constructs a TemporaryVoice from VoiceResourceResponse data
- [ ] TemporaryVoice satisfies the same interface as VoiceProfile for generation
- [ ] TemporaryVoice has `isTemporary: true` discriminator
- [ ] TTS Voice Selector shows "(Preset)" subtitle for temporary voices
- [ ] "Import to Library" button appears in TTS panel when temporary voice is selected
- [ ] "Import to Library" from TTS panel creates the persisted entities and replaces temporary selection
- [ ] Temporary voice is discarded when user selects a different voice
- [ ] Temporary voice is discarded when user navigates away from TTS page
- [ ] "Import to Library" button in PresetVoicesTab still calls `importVoiceResource()` correctly
- [ ] Preview button on preset card plays `preview_audio_url`
- [ ] Preset card showing `is_in_library === true` shows "In Library" badge (disabled import), "Use in TTS" still available

### N2 — Add `primary_model_id` / `recommended_model_id` Support

- [ ] `VoiceProfile` type has `primaryModelId: string | null`
- [ ] `VoiceProfile` type has `recommendedModelId: string | null`
- [ ] `useModelForVoice` hook returns model ID following priority: primary → recommended → first compatible → null
- [ ] Selecting a voice with `primaryModelId` auto-selects that model
- [ ] Selecting a voice without `primaryModelId` but with `recommendedModelId` auto-selects that model
- [ ] Selecting a voice without either falls back to first compatible model
- [ ] Selecting a voice with no compatible models shows empty state in ModelSelector
- [ ] `ModelSelector` highlights primary model with "Primary" badge
- [ ] `ModelSelector` highlights recommended model with "Recommended" badge
- [ ] Auto-switch effect in GenerationPanel works even when `selectedModelId` is null
- [ ] Model selection does not change when switching to another voice with the same primary model

### N3 — Model-Scoped Generation Settings

- [ ] `GenerationSettings` hardcoded type is removed, replaced by `Record<string, unknown>`
- [ ] `GenerationRequest` has `params?: Record<string, unknown>` instead of individual OmniVoice fields
- [ ] Store has `modelSettings: Record<string, Record<string, unknown>>` keyed by model_id
- [ ] Switching from OmniVoice to Kokoro: OmniVoice settings are saved, Kokoro settings loaded
- [ ] Switching back from Kokoro to OmniVoice: OmniVoice settings are restored (not reset to defaults)
- [ ] First use of a model initializes settings from its `settings_schema` defaults
- [ ] Generation request for Kokoro includes ONLY `speed` (not `num_step`, `guidance_scale`, etc.)
- [ ] Generation request for OmniVoice includes all 6 OmniVoice parameters
- [ ] Generation request for a model without `settings_schema` sends empty `params`
- [ ] Existing user settings are migrated: current flat settings assigned to current model's key on first load

### N4 — Fix VoiceDetailPanel Type Leaks

- [ ] Transcript is hidden for PRESET_VOICE voices even when `profile.transcript` is truthy
- [ ] Transcript is shown for SOURCE_ASSET voices when `profile.transcript` is truthy
- [ ] Provider metadata is hidden for SOURCE_ASSET voices even when `profile.meta.provider` is set
- [ ] Provider metadata is shown for PRESET_VOICE voices when `profile.meta.provider` is set
- [ ] Preview audio for PRESET_VOICE uses provider preview URL, not reference audio
- [ ] Preview audio for SOURCE_ASSET uses `getVoiceAudioUrl()`
- [ ] Usage count, created date, last used are hidden for VoiceResource and TemporaryVoice
- [ ] Export action is present and functional in Actions section
- [ ] "Import to Library" action is present for temporary voices in VoiceDetailPanel
- [ ] All sections collapse correctly when data is unavailable per SPEC §9.2

### N5 — Create PaginationControls Component

- [ ] PaginationControls shows prev/next buttons
- [ ] Page numbers are displayed (limited window around current page)
- [ ] Page size selector shows 25, 50, 100, 200 options
- [ ] Default page size is 50
- [ ] Total count display: "Showing 1-{limit} of {total} voices"
- [ ] Component translates page/pageSize to cursor-based API calls
- [ ] Prev button disabled on first page
- [ ] Next button disabled on last page
- [ ] Empty results shows "No voices found" (not broken pagination)
- [ ] Single page shows no pagination controls (or disabled state)

### N6 — Implement Virtual Scrolling

- [ ] `react-virtuoso` dependency added
- [ ] `VirtualVoiceGrid` component exists and renders grid items via virtualization
- [ ] Normal `VoiceGrid` used below 100 voices (no virtualization overhead)
- [ ] Virtual scrolling activates at 100+ voices
- [ ] Scroll position is preserved on filter/sort changes
- [ ] No visible jank or layout shift at 200+ voices
- [ ] Voice cards render correctly in virtualized mode (same appearance as non-virtualized)

### N7 — Add Compatible Model and Provider Filters to Library

- [ ] FilterBar has "Compatible with:" dropdown showing active models
- [ ] Selecting a model filters voices to those compatible with that model
- [ ] Filter chip shows "Compatible: {model name}" with remove button
- [ ] FilterBar has "Provider:" dropdown showing providers from current results
- [ ] Provider filter only visible when PRESET_VOICE voices exist in results
- [ ] Selecting a provider filters voices to that provider's presets
- [ ] Multiple filters can be combined (compatible_model + provider + creation_source + language)
- [ ] Client-side fallback works when backend does not support query params

### N8 — Make VariantDashboard Compatibility-Aware

- [ ] Matrix shows three distinct states: Ready (✅), Buildable (○), Incompatible (✗)
- [ ] Ready cells show green checkmark with [Rebuild] action
- [ ] Buildable cells show blue circle with [Build] action
- [ ] Incompatible cells show gray X with no action
- [ ] Tooltip on incompatible: "No build strategy for {creation_source} voices"
- [ ] Tooltip on buildable: "No variant yet. Click Build to create one."
- [ ] Backfill button only processes Buildable cells, skips Incompatible
- [ ] Compatibility data comes from `voice.compatibleModels` (not just variant_summary)
- [ ] OmniVoice/Larissa × Kokoro = ✗ Incompatible
- [ ] Kokoro/Bella × Kokoro = ✅ Ready (or ○ if not yet built)

### N9 — Per-Model Settings Persistence

- [ ] `modelSettings` survives page reload (persisted to localStorage)
- [ ] Storage key is scoped to avoid collisions
- [ ] Settings for models that no longer exist are cleaned up
- [ ] Serialization handles all valid parameter types (number, boolean, string, null)
- [ ] No serialization errors for edge cases

### Phase O — Validation & Status Cleanup

- [ ] `peakvox-voice-system-evolution/STATUS.md` corrected: J8, J9, K9 marked as not implemented
- [ ] `peakvox-voice-system-evolution/VALIDATION.md` corrected: transcript leak, provider metadata leak validated
- [ ] All SPEC §13 user journey scenarios pass manual verification

## Scenario Walkthroughs

### Scenario 1: New user exploring presets
- [ ] No VoiceProfile created
- [ ] No VoiceVariant created
- [ ] No VoiceVariantArtifact created
- [ ] Navigated to TTS page with temporary voice
- [ ] Model auto-selected to primary_model_id
- [ ] Only model's settings_schema parameters visible
- [ ] Only model's supported_languages visible
- [ ] "(Preset)" subtitle shown
- [ ] "Import to Library" button visible

### Scenario 2: User imports a preset
- [ ] VoiceProfile created
- [ ] VoiceVariant created
- [ ] Toast notification shown
- [ ] Voice appears in My Voices tab
- [ ] Badge shows "Preset" in purple

### Scenario 3: User selects voice with incompatible model hidden
- [ ] Model selector shows only compatible models
- [ ] Primary model highlighted

### Scenario 4: User selects model first
- [ ] Voice selector shows only compatible voices
- [ ] Count badge shows correct numbers

### Scenario 5: User changes model, settings preserved per model
- [ ] OmniVoice settings restored when switching back (including custom values)
- [ ] Kokoro settings preserved when switching back

### Scenario 6: User views variant dashboard
- [ ] Cells show Ready/Buildable/Incompatible distinctly
- [ ] Backfill only processes buildable cells

### Scenario 7: User opens voice details for imported preset
- [ ] "Preset" badge shown
- [ ] Provider metadata shown
- [ ] Transcript hidden
- [ ] Compatible Models section correct

### Scenario 8: User generates speech with Kokoro
- [ ] GenerationRequest contains only Kokoro params
- [ ] Generation succeeds

### Scenario 9: Voice Library pagination
- [ ] Pagination controls visible at all times
- [ ] Page size selector functional
- [ ] Total count display correct

### Scenario 10: Library filter by compatible model
- [ ] Filter shows only compatible voices
- [ ] Filter chip removable

## Commands

```bash
# Frontend build verification
cd frontend && npm run build

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend lint
cd frontend && npm run lint

# Backend tests (backend must not regress)
docker compose run --rm backend python -m pytest tests/ -q
```

## Non-Goals

- Backend changes to add page-based pagination (`?page=` support)
- Backend changes to add `?compatible_model=` or `?provider=` (assumed to exist from Phase J)
- Collections implementation (Phase M — P3, future)
- Compact mode for TTS Panel (K9 — not implemented, left for future)
- Voice marketplace listing
- Cloud-specific features

---

Related: `TASKS.md` · `../../VALIDATION/audits/frontend-architecture-compliance-report.md`
