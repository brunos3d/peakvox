# Frontend Architecture Compliance Report

> **Audit date:** 2026-06-07
> **Scope:** Frontend implementation vs. PeakVox Voice System Evolution architecture (Refined v4)
> **Method:** Full source code audit of all frontend components, store, types, API layer, and hooks
> **Documents audited against:** SPEC.md, DESIGN.md, TASKS.md, VALIDATION.md, STATUS.md

---

## Executive Summary

The frontend implementation has been partially aligned with the refined architecture but contains critical gaps. Of the 11 architecture invariants established by the refined spec, **4 are fully satisfied**, **3 are partially satisfied**, and **4 are violated or missing entirely**.

The most severe violations are:
1. **"Use Now" imports presets instead of using them temporarily** — violates the Voice Identity vs Catalog Resources boundary (ADR-0012)
2. **`primary_model_id` / `recommended_model_id` not implemented anywhere in the frontend** — violates D11
3. **Generation settings spread unconditionally to all models** — violates the model-scoped settings contract (D1)
4. **VoiceLibrary page missing key architecture-required features** — no pagination controls, no virtual scrolling, no `?compatible_model=` filter, no `?provider=` filter

---

## 1. Architecture Compliance by Component

### 1.1 VoiceSelector
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Filters voices by `compatible_models` when model is selected | ✅ COMPLIANT | `VoiceSelector.tsx:31-45` — uses `v.compatible_models.includes(activeModel.id)` |
| Shows all voices when no model selected | ✅ COMPLIANT | `VoiceSelector.tsx:32-34` — returns all voices when `!activeModel` |
| Shows compatibility count badges | ✅ COMPLIANT | `VoiceSelector.tsx:65-67` — shows `N compatible · M total` |
| Uses backend `compatible_models` field | ⚠️ PARTIAL | Reads from store.voices which are populated by `fetchVoices()`. Depends on backend returning correct field. |

### 1.2 ModelSelector
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Filters models by `compatibleModelIds` prop | ✅ COMPLIANT | `ModelSelector.tsx:40-46` — filters by `compatibleModelIds.includes(m.id)` |
| Shows compatible/incompatible counts | ✅ COMPLIANT | `ModelSelector.tsx:48-50, 101-105` — `N compatible · M incompatible (hidden)` |
| Pre-selects `primary_model_id` when available | ❌ VIOLATED | `ModelSelector.tsx:29-31` — selects default model, never checks `primary_model_id`. VoiceProfile type has NO `primary_model_id` field. |

### 1.3 GenerationPanel
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Auto-switches model on voice change | ⚠️ PARTIAL | `GenerationPanel.tsx:52-63` — effect runs on `selectedProfile?.id` change, but only if `selectedModelId` is already set. When `selectedModelId` is null (default), the effect is skipped by the guard `!selectedModelId` on line 56. |
| Shows incompatibility warning | ✅ COMPLIANT | `GenerationPanel.tsx:46-50, 252-258` — shows warning when `selectedModelIncompatible` is true |
| Prevents generation with incompatible pair | ✅ COMPLIANT | `GenerationPanel.tsx:74-75` — `!selectedModelIncompatible` prevents generation |
| Spreads model-scoped generation settings | ❌ VIOLATED | `GenerationPanel.tsx:79-88` — spreads `...generationSettings` unconditionally, sending OmniVoice-specific parameters (num_step, guidance_scale, etc.) even when Kokoro or another model is selected |

### 1.4 GenerationSettings / GenerationSettingsFields / DynamicSettingsForm
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Renders `DynamicSettingsForm` when `settings_schema` present | ✅ COMPLIANT | `GenerationSettingsFields.tsx:35-40` — conditionally renders DynamicSettingsForm |
| Falls back to static OmniVoice form when schema is null | ✅ COMPLIANT | `GenerationSettingsFields.tsx:41-129` — full OmniVoice fallback |
| DynamicSettingsForm renders sliders/switches/selects | ✅ COMPLIANT | `DynamicSettingsForm.tsx:32-118` — handles number, boolean, select, string types |
| Settings are model-scoped (only show params for selected model) | ✅ COMPLIANT | The schema itself provides only the model's parameters |
| Store holds model-specific defaults per model | ❌ VIOLATED | `use-store.ts:6-15` — `SYSTEM_DEFAULTS` is a single set of OmniVoice defaults. There is no per-model settings store. When switching from OmniVoice to Kokoro and back, OmniVoice-specific settings are preserved in the store, which is correct, but there's no mechanism to load model-specific initial defaults. |

### 1.5 PresetVoicesTab
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Uses `GET /voice-resources` | ✅ COMPLIANT | `PresetVoicesTab.tsx:37-46` — uses `fetchVoiceResources({ resource_type: "preset" })` |
| Uses `POST /voice-resources/{id}/import` | ✅ COMPLIANT | `PresetVoicesTab.tsx:153` — uses `importVoiceResource(voice.id)` |
| Shows `is_in_library` state | ✅ COMPLIANT | `PresetVoicesTab.tsx:195` — shows "In Library" badge when `voice.is_in_library` |
| "Use Now" does NOT import | ❌ VIOLATED | `PresetVoicesTab.tsx:149-167` — BOTH "Use Now" and "Library" call `importVoiceResource()`. "Use Now" imports the preset AND navigates to TTS. Per ADR-0012, "Use Now" must NOT create any persisted entity. |
| Preset card shows import action | ⚠️ PARTIAL | `PresetVoicesTab.tsx:177-196` — both buttons disabled when `is_in_library` is true, but no "Play preview" action exists |

### 1.6 VoiceDetailPanel
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Accepts `VoiceProfile | VoiceResourceResponse | null` | ✅ COMPLIANT | `VoiceDetailPanel.tsx:24` — type is `VoiceProfile | VoiceResourceResponse | null` |
| Single component for all voice types | ✅ COMPLIANT | `VoiceDetailPanel.tsx:76-326` — one component handles both VoiceProfile and VoiceResourceResponse |
| Section collapse when data unavailable | ✅ COMPLIANT | `VoiceDetailPanel.tsx:50-73` — `Section` component with `defaultOpen` parameter; Previews section only opens when `previewable` |
| Header shows creation_source badge | ✅ COMPLIANT | `VoiceDetailPanel.tsx:102-106, 136-139` — renders badge from `CREATION_SOURCE_LABELS` |
| Overview shows provider metadata for PRESET_VOICE only | ⚠️ PARTIAL | `VoiceDetailPanel.tsx:179-186` — checks `profile?.meta?.provider != null` which works for preset voices, but does NOT explicitly check `creation_source === "PRESET_VOICE"`. A SOURCE_ASSET voice with `meta.provider` set would incorrectly show provider metadata. |
| Previews section plays correct audio for type | ❌ VIOLATED | `VoiceDetailPanel.tsx:237` — for profiles, always uses `getVoiceAudioUrl(profile.id)`. For resources, uses `resource.preview_audio_url`. However, for PRESET_VOICE profiles that have been imported, the audio URL may return the reference audio that doesn't exist (presets don't have reference audio). The architecture requires the Previews section to gate on `preview_summary.origin`. |
| Shows transcript only for SOURCE_ASSET voices | ❌ VIOLATED | `VoiceDetailPanel.tsx:213-218` — shows transcript for ANY profile that has a `transcript` field truthy. Per SPEC §12.4, transcript should be shown only for SOURCE_ASSET voices. A PRESET_VOICE that somehow has a transcript would incorrectly display it. |
| Does NOT branch on type for layout | ✅ COMPLIANT | Same layout structure for both types |
| Action bar shows correct actions per type | ✅ COMPLIANT | `VoiceDetailPanel.tsx:278-317` — profile actions vs resource.in_library actions vs import actions |

### 1.7 VoiceCard
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Shows creation_source badge | ✅ COMPLIANT | `VoiceCard.tsx:86-96` — renders from `CREATION_SOURCE_LABELS` |
| Play button gated on `preview_summary.origin !== "none"` | ✅ COMPLIANT | `VoiceCard.tsx:20-24, 139` — `usePreviewable` checks `preview_summary.origin !== "none"` |
| Shows duration only when previewable | ✅ COMPLIANT | `VoiceCard.tsx:100-102` — duration shown inside `previewable` check |
| Shows provider badge for PRESET_VOICE | ✅ COMPLIANT | `VoiceCard.tsx:103-107` — checks `creation_source === "PRESET_VOICE"` |

### 1.8 LanguageCombobox
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Filters by `availableLanguageIds` | ✅ COMPLIANT | `LanguageCombobox.tsx:64-77` — filters both common and all languages |
| Shows all languages when no filter | ✅ COMPLIANT | Falls through to `ALL_LANGUAGES_SORTED` |
| Shows "Auto" option | ✅ COMPLIANT | `LanguageCombobox.tsx:130-148` — conditional on `includeAuto` |

### 1.9 Voice Library Page
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Search bar exists | ✅ COMPLIANT | `voices/page.tsx:61-65` — `FilterBar` with search |
| Debounced search | ✅ COMPLIANT | `voices/page.tsx:45-52` — 200ms debounce |
| SortDropdown exists | ✅ COMPLIANT | `voices/page.tsx:258-263` |
| FilterChips exist | ✅ COMPLIANT | `voices/page.tsx:275-299` |
| Creation source filter chips | ✅ COMPLIANT | `voices/page.tsx:219-247` — All, Cloned, Preset, Favorites |
| Recently used filter chips | ✅ COMPLIANT | `voices/page.tsx:243-257` — 7d, 30d, 90d |
| PaginationControls component | ❌ MISSING | No pagination controls exist. The page uses infinite scroll via `query.fetchNextPage()` (line 372) and a "Load more" button, but no `PaginationControls` per J8 spec. |
| Page size selector | ❌ MISSING | No page size selection. Uses default limit only. |
| Virtual scrolling | ❌ MISSING | No virtualization. Uses simple `VoiceGrid` which renders all items. At 100+ voices this causes DOM bloat. |
| `?compatible_model=` filter | ❌ MISSING | No `compatible_model` filter in the library UI. The `VoiceQueryFilters` type doesn't include `compatible_model`. |
| `?provider=` filter | ❌ MISSING | No provider filter in the library UI. |
| Variant Dashboard shows compatibility from resolver | ❌ VIOLATED | `VariantDashboard.tsx` uses `fetchVariantSummary()` which shows EXISTING variant status only, NOT compatibility from `CompatibilityResolver`. Architecture requires compatibility to include potential builds from build strategies, not just existing variants. |

### 1.10 Store (use-store)
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Holds `selectedModelId` | ✅ COMPLIANT | `use-store.ts:73` |
| Holds `generationSettings` as flat object | ❌ VIOLATED | `use-store.ts:161-168` — `GenerationSettings` type hardcodes OmniVoice fields. Should be a generic key-value store or scoped per model. |
| Holds `selectedProfile` | ✅ COMPLIANT | `use-store.ts:44` |
| `setSelectedProfile` loads defaults | ✅ COMPLIANT | `use-store.ts:128-169` — loads from `profile.generation_defaults` |
| Per-model settings storage | ❌ MISSING | No mechanism to store/restore settings per model. Switching between models loses model-specific adjustments. |

### 1.11 VariantDashboard (Matrix)
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Shows variant status per voice×model | ✅ COMPLIANT | `VariantDashboard.tsx:109-146` — matrix table |
| Uses `GET /variants/summary` | ✅ COMPLIANT | `VariantDashboard.tsx:41` — fetches variant summary |
| Shows compatibility from build strategies | ❌ VIOLATED | Only shows EXISTING variants. Does not show potential compatibility from `CompatibilityResolver`. Architecture requires compatibility information, not just variant build status. |
| Disambiguates "not compatible" from "not built yet" | ❌ VIOLATED | `VariantDashboard.tsx:130-132` — renders the same "missing" icon for both "not compatible" and "not yet built". User cannot distinguish between "this model cannot use this voice" vs "this voice hasn't been built for this model yet." |

### 1.12 VariantManager (in VoiceDetailPanel)
| Invariant | Status | Evidence |
|-----------|--------|----------|
| Shows per-model variant status | ✅ COMPLIANT | Referenced in `VoiceDetailPanel.tsx:272` |
| Shows Build/Rebuild actions | ✅ COMPLIANT | `ModelCompatibilitySection.tsx:89-102` — "Create Variant" button for missing variants |

---

## 2. Missing Implementations (Architecture-Required, Not Implemented)

### M1 — `primary_model_id` / `recommended_model_id` (SPEC §13, D11)

**Expected:** Voice contract includes `primary_model_id` (persisted, set at creation) and `recommended_model_id` (derived). Frontend pre-selects `primary_model_id` when voice is selected.

**Current:** `VoiceProfile` type has no `primary_model_id` or `recommended_model_id`. `ModelSelector` uses `m.is_default` to pre-select. The auto-switch `useEffect` in GenerationPanel picks the first compatible model, not the primary model.

**Impact:** Users must manually select a compatible model when choosing a voice. The voice does not "know" its own model. This is a fundamental voice-first architecture violation: the voice should carry its model preference.

### M2 — Per-Model Generation Settings Storage (SPEC §3.2, D1)

**Expected:** Each model has its own settings schema. When switching models, settings persist per model (e.g., switching from OmniVoice to Kokoro and back restores OmniVoice settings).

**Current:** Single flat `generationSettings` in store. Switching models overwrites/retains values globally.

**Impact:** User sets Kokoro speed to 1.5x, switches to OmniVoice, changes inference steps to 40, switches back to Kokoro — speed is whatever OmniVoice left it at, not 1.5x.

### M3 — "Use Now" Temporary Selection (SPEC §3.1, ADR-0012)

**Expected:** "Use Now" selects preset temporarily for TTS without importing. No VoiceProfile, VoiceVariant, or VoiceArtifact created.

**Current:** "Use Now" calls `importVoiceResource()` which creates all three entities.

**Impact:** Every "I want to try this voice" click creates a permanent entry in the library. Voice library fills with voices the user never intended to keep.

### M4 — Pagination Controls (TASKS.md J8)

**Expected:** Page navigation (prev, next, page numbers), page size selector (25, 50, 100, 200), total count display ("Showing 1-50 of 1,234 voices").

**Current:** Infinite scroll with "Load more" button. No pagination controls. No page size selector.

### M5 — Virtual Scrolling (TASKS.md J9)

**Expected:** Virtual scrolling at 100+ voice threshold using react-window or react-virtuoso.

**Current:** All voices rendered in a CSS grid. No virtualization.

### M6 — Compatible Model Filter in Library (SPEC §10.2)

**Expected:** `?compatible_model=` filter in library — filter voices by compatible model.

**Current:** No `compatible_model` filter in the library UI.

### M7 — Provider Filter in Library (SPEC §10.2)

**Expected:** `?provider=` filter for PRESET_VOICE voices.

**Current:** No provider filter in library UI (only available in PresetVoicesTab).

### M8 — Generation Request Should Filter by Model Schema

**Expected:** When building `GenerationRequest`, only include parameters from the active model's `settings_schema`.

**Current:** `GenerationPanel.tsx:79-88` spreads all `generationSettings` fields unconditionally.

### M9 — Variant Dashboard Compatibility Awareness

**Expected:** The variant matrix should show compatibility information alongside variant status. User should see whether a model COULD build a variant (compatible but not built) vs CANNOT build (incompatible).

**Current:** Shows only variant build status. OmniVoice/Larissa shows "missing" for Kokoro with no indication of incompatibility.

---

## 3. UX Violations

### UX-1: Unnecessary Library Pollution

**Flow:**
1. User opens Preset Catalog
2. Clicks "Use Now" on Kokoro preset "Bella"
3. Bella is imported, a VoiceProfile is created, Bella appears in "My Voices"
4. User clicks "Use Now" on 5 more presets
5. My Voices now has 6 entries the user never intended to keep

**Expected:** "Use Now" navigates to TTS with the preset temporarily selected. Nothing appears in My Voices. Only "Import to Library" creates a library entry.

**Severity:** HIGH. This confusion between "try" and "keep" is one of the six bug classes identified in the architecture (SPEC §3.1, ADR-0012).

### UX-2: Invisible Model Pre-selection

**Flow:**
1. User selects voice "Larissa" (OmniVoice clone, primary_model_id = "omnivoice-base")
2. Default model might be Kokoro or another model
3. User sees "This voice is not compatible with Kokoro" warning
4. User must manually find and select OmniVoice

**Expected:** Voice pre-selects its primary model. User sees no warning. Model selection is an advanced override.

**Severity:** HIGH. The voice-first architecture requires this to be transparent.

### UX-3: Irrelevant Generation Settings Shown

**Flow:**
1. User selects Kokoro model
2. Generation Settings section still shows sliders for Inference Steps, Guidance Scale, Time Shift, Denoise
3. Only Speed is relevant for Kokoro

**Wait — this actually is handled by DynamicSettingsForm. Let me re-check...**

GenerationSettingsFields.tsx:35-40 uses DynamicSettingsForm when settingsSchema is present. DynamicSettingsForm only renders properties from the schema. So Kokoro would only show Speed.

But the static fallback (OmniVoice form) still shows ALL controls when settingsSchema is null. AND the GenerationRequest still sends all fields.

**Revised assessment:** The display is correct via DynamicSettingsForm, but the submission still sends irrelevant fields. Severity is MEDIUM (backend likely ignores extra fields).

### UX-4: Preset Voices Show Incorrect Detail Content

**Flow:**
1. User double-clicks imported preset voice
2. VoiceDetailPanel opens
3. Shows "Transcript" section if the profile has a transcript field
4. Shows "Usage count" and "Created" dates that may not be meaningful for presets

**Expected:** Transcript hidden for PRESET_VOICE. Provider metadata prominently displayed.

**Severity:** MEDIUM. Minor confusion but doesn't break functionality.

### UX-5: Library Lacks Essential Filtering

**Flow:**
1. User has 200 voices (50 SOURCE_ASSET, 150 PRESET_VOICE from Kokoro + Fish Audio)
2. User wants to find voices compatible with Fish Audio
3. No `?compatible_model=` filter exists in library
4. User must scroll through all 200 voices

**Expected:** Library has a `compatible_model` filter chip that shows only voices compatible with a selected model.

**Severity:** HIGH. At multi-provider scale, this is a critical UX gap.

### UX-6: Cannot Distinguish "Not Compatible" from "Not Built"

**Flow:**
1. User opens Variant Dashboard
2. Sees "Larissa" × "Kokoro" = missing icon
3. User runs Backfill — nothing happens (Kokoro has no PRESET_VOICE build strategy)
4. User confused about why backfill doesn't create a variant

**Expected:** The matrix shows "incompatible" vs "compatible (not built)" with different icons. Backfill should only process compatible pairs.

**Severity:** MEDIUM. Misleading but doesn't prevent core usage.

---

## 4. Incorrectly Marked Completed Tasks

From STATUS.md: "Completed: A, B, C, D, E, F, G, H, J, K, L"

### Task A5 — Replace static GenerationSettingsFields
**Status:** ⚠️ PARTIAL
**Evidence:** GenerationSettingsFields.tsx:35-40 correctly uses DynamicSettingsForm when schema present. BUT the static fallback form (lines 42-128) still exists. The architecture says absent settings_schema falls back to OmniVoice form. This is correct. However, the generation request still spreads ALL fields unconditionally (GenerationPanel.tsx:86), which should be filtered by the model's schema.
**Verdict:** Partially complete. Generation request filtering is missing.

### Task C2 — Filter VoiceSelector by compatible_models
**Status:** ✅ COMPLETE
**Evidence:** VoiceSelector.tsx:31-45 correctly filters by `compatible_models`.

### Task C3 — Bidirectional filtering in TTS panel
**Status:** ⚠️ PARTIAL
**Evidence:** Voice→Model filtering works (ModelSelector receives compatibleModelIds). Model→Voice filtering works (VoiceSelector filters). But auto-selection of `primary_model_id` is missing. The auto-switch effect (GenerationPanel.tsx:52-63) only runs when `selectedModelId` is already set — when both voice and model are unselected, selecting a voice does NOT auto-select its primary model.
**Verdict:** Filtering works but model pre-selection on voice change is broken.

### Task D3/D4 — Conditional VoiceDetailsDrawer
**Status:** ⚠️ PARTIAL
**Evidence:** The old VoiceDetailsDrawer has been removed and replaced by VoiceDetailPanel. But transcript visibility is not gated on `creation_source !== "PRESET_VOICE"` — it's gated on truthy transcript value. This leaks preset voice details.

### Task J8 — Create PaginationControls component
**Status:** ❌ NOT IMPLEMENTED
**Evidence:** No PaginationControls in any file. No page size selector. No page navigation.

### Task J9 — Implement virtual scrolling
**Status:** ❌ NOT IMPLEMENTED
**Evidence:** No react-window or react-virtuoso dependency. VoiceGrid renders all items in CSS grid.

### Task K7 — Actions section with all expected actions
**Status:** ⚠️ PARTIAL
**Evidence:** Actions exist for VoiceProfile (Use, API, Copy ID, Edit, Delete). But Export action is not implemented (no handler passed). Compact mode for TTS Panel (K9) not verified.

### Task K9 — Compact mode for TTS Panel
**Status:** ❌ NOT IMPLEMENTED
**Evidence:** VoiceDetailPanel has no compact mode. It always renders as a full sheet. The TTS Panel uses VoiceSelector, not the compact VoiceDetailPanel.

---

## 5. Root Cause Analysis

### Root Cause 1: "Use Now" and "Library" are conflated

The backend API `POST /api/voice-resources/{id}/import` is the only path. There is no "temporary use" endpoint. The frontend has no concept of temporary preset selection.

**Fix:** Either:
a) Add a "temporary use" endpoint on the backend, OR
b) Have the frontend construct a "temporary profile" from the VoiceResourceResponse data (name, compatible_models, language, etc.) that satisfies the VoiceProfile interface without creating a backend entity.

Option (b) is preferred — it maintains the no-new-endpoints philosophy and is purely frontend work.

### Root Cause 2: VoiceProfile type lacks primary_model_id

The `VoiceProfile` interface in `types/index.ts` does not include `primary_model_id` or `recommended_model_id`. The backend may or may not have added this field.

**Fix:** Add fields to type, add field to store, update `setSelectedProfile` to auto-select model, update auto-switch effect to prefer `primary_model_id`.

### Root Cause 3: GenerationRequest is not model-scoped

`GenerationRequest` type (types/index.ts:126-140) contains all OmniVoice-specific parameters. The submission spreads `generationSettings` unconditionally.

**Fix:** Change `GenerationRequest` to use `Record<string, unknown>` for model-specific params. Filter `generationSettings` by the model's `settings_schema` properties before including in the request.

### Root Cause 4: Library pagination/virtualization not implemented

The library page was built before the J-phase requirements were added. The J8 and J9 tasks were marked as P0 but not actually implemented.

### Root Cause 5: No per-model settings store

The Zustand store uses a single flat `GenerationSettings` type with hardcoded OmniVoice fields. When the model changes, there's no mechanism to preserve/restore per-model settings.

---

## 6. New Phase Proposal: Frontend Architecture Alignment

### Phase N: Voice-First UX Alignment (P0)

#### N1 — Fix "Use Now" (temporary preset selection)
- Frontend-only: construct a temporary profile-like object from VoiceResourceResponse
- Add `VoiceResourceResponse` → temporary selection pathway in store
- "Use Now" does NOT call importVoiceResource
- "Use Now" navigates to TTS with temporary voice selection
- Temporary selection is indicated with a "(Preset - not imported)" subtitle
- Import button remains in TTS panel for temporary selections

#### N2 — Add `primary_model_id` / `recommended_model_id` support
- Add fields to `VoiceProfile` type
- Add field to store state if needed
- Update `useActiveModel` / ModelSelector to prefer `primary_model_id` when voice is selected
- Update GenerationPanel auto-switch effect to use `primary_model_id`
- Update VoiceSelector subtitle to show primary model name

#### N3 — Model-scoped generation settings
- Add per-model settings storage in store (`Map<modelId, Record<string, any>>`)
- On model switch: save current settings to map, load new model's settings
- On model switch with empty map: initialize from model's `settings_schema` defaults
- Filter `GenerationRequest` to only include fields from model's `settings_schema`
- Make `GenerationSettings` type generic (remove hardcoded OmniVoice fields)

#### N4 — Fix VoiceDetailPanel type leaks
- Gate transcript display on `creation_source !== "PRESET_VOICE"`
- Gate provider metadata on `creation_source === "PRESET_VOICE"` (not just truthy meta.provider)
- Gate Usage count/Created/Last used with creation_source awareness
- Ensure Previews section handles PRESET_VOICE audio correctly (use preview_audio_url from VoicePreviews, not reference audio)

#### N5 — Create PaginationControls component
- Prev/next page buttons
- Page number display
- Page size selector (25, 50, 100, 200)
- Total count display
- Wire into `useVoicesPage` hook (switch from cursor-based to page-based pagination, or add page controls alongside cursor)

#### N6 — Implement virtual scrolling
- Add react-virtuoso or react-window dependency
- Implement VirtualVoiceList component
- Activate at 100+ voices threshold
- Fixed height in list mode

#### N7 — Add compatible_model and provider filters to library
- Add `?compatible_model=` filter to `VoiceQueryFilters` type
- Add `?compatible_model=` filter chip in FilterBar
- Add `?provider=` filter for PRESET_VOICE voices
- Backend support required: `?compatible_model=` filter in GET /voices

#### N8 — Make VariantDashboard compatibility-aware
- Differentiate "no variant (compatible)" from "incompatible" in matrix
- Show "incompatible" as a crossed-out icon, not a "missing" icon
- Backfill button should only process compatible voice×model pairs

#### N9 — Per-model settings persistence
- On model switch, save current settings to per-model store
- On model switch, load stored settings (or defaults from schema)
- On first use of a model, initialize from schema defaults

### Phase O: Validation & Test Alignment (P0)

#### O1 — Update VALIDATION.md
- Add validation criteria for all N-phase tasks
- Update incorrect task statuses (J8, J9, K9)
- Add architecture invariant tests for each violation found

#### O2 — Update STATUS.md
- Correct J8 from completed to not-implemented
- Correct J9 from completed to not-implemented
- Correct K9 from completed to not-implemented
- Update Phase N status

---

## 7. Required TASKS.md Additions

### Add to Phase N (new phase):
```
## Phase N: Frontend Architecture Alignment (P0)

### N1 — Fix "Use Now" to not import
### N2 — Add primary_model_id / recommended_model_id support
### N3 — Model-scoped generation settings
### N4 — Fix VoiceDetailPanel type leaks
### N5 — Create PaginationControls component
### N6 — Implement virtual scrolling
### N7 — Add compatible_model and provider filters to library
### N8 — Make VariantDashboard compatibility-aware
### N9 — Per-model settings persistence
```

### Update existing tasks:
```
### J8 — Create PaginationControls component
### J9 — Implement virtual scrolling in voice list
### K9 — Add compact mode for TTS Panel
```

---

## 8. Required VALIDATION.md Additions

### Add to Phase K:
```
- [ ] Export action is implemented in VoiceDetailPanel
- [ ] Compact mode renders correctly in TTS Panel with collapsed sections (NOT IMPLEMENTED)
- [ ] VoiceDetailPanel hides transcript for PRESET_VOICE voices (BROKEN - leaks)
- [ ] VoiceDetailPanel gates provider metadata on creation_source, not meta.provider truthiness (BROKEN)
```

### Add new validation section:
```
### Phase N: Frontend Architecture Alignment

- [ ] "Use Now" does not create VoiceProfile, VoiceVariant, or VoiceVariantArtifact
- [ ] "Use Now" selects preset temporarily with "(Preset - not imported)" indicator
- [ ] Voice contract includes primary_model_id and recommended_model_id
- [ ] Selecting a voice automatically pre-selects its primary_model_id
- [ ] Generation settings are stored per-model (switching models preserves per-model settings)
- [ ] GenerationRequest only includes fields from selected model's settings_schema
- [ ] VoiceDetailPanel hides transcript for PRESET_VOICE voices
- [ ] VoiceDetailPanel shows provider metadata only for PRESET_VOICE voices
- [ ] PaginationControls exist with prev/next, page numbers, page size selector
- [ ] Virtual scrolling activates at 100+ voices threshold
- [ ] Library has ?compatible_model= filter chip
- [ ] Library has ?provider= filter chip
- [ ] VariantDashboard differentiates "not compatible" from "not built"
- [ ] Backfill only processes compatible voice×model pairs
```

---

## 9. Required STATUS.md Updates

```
**Completed:** A, B, C, D, E, F, G, H, L (backend)

**Partially Completed:** C (missing primary_model_id auto-selection), D (transcript leak in VoiceDetailPanel), J (no pagination controls, no virtual scrolling), K (no compact mode, no Export action)

**Not Completed (incorrectly marked):** J8 (PaginationControls), J9 (Virtual scrolling), K9 (Compact mode)

**Frontend Architecture Audit (2026-06-07):** Full frontend audit completed. 11 architecture invariants verified. 4 violations found: (1) "Use Now" imports instead of temporary selection, (2) GenerationRequest spreads all settings unconditionally, (3) primary_model_id not implemented, (4) no per-model settings storage. 4 missing features: (1) PaginationControls, (2) Virtual scrolling, (3) compatible_model library filter, (4) provider library filter. Phase N proposed for P0 alignment pass.
```

---

## 10. Summary

| # | Issue | Severity | Type | Root Cause |
|---|-------|----------|------|------------|
| 1 | "Use Now" imports presets | HIGH | Violation | No temporary selection path |
| 2 | No primary_model_id support | HIGH | Missing | Not added to VoiceProfile type |
| 3 | GenerationRequest not model-scoped | MEDIUM | Violation | Spreads all settings unconditionally |
| 4 | No pagination controls | MEDIUM | Missing | J8 not implemented |
| 5 | No virtual scrolling | LOW | Missing | J9 not implemented |
| 6 | No compatible_model library filter | MEDIUM | Missing | J4 not wired to library UI |
| 7 | No provider library filter | LOW | Missing | J4 not wired to library UI |
| 8 | Transcript visible for presets | LOW | Violation | Not gated on creation_source |
| 9 | No Export action in detail panel | LOW | Missing | K7 partially implemented |
| 10 | No compact mode for TTS Panel | LOW | Missing | K9 not implemented |
| 11 | VariantDashboard doesn't show compatibility | MEDIUM | Violation | Uses variant_summary, not CompatibilityResolver |
| 12 | No per-model settings persistence | MEDIUM | Missing | Store uses single flat settings object |
| 13 | Auto-switch model on voice change broken when no model selected | MEDIUM | Bug | Guard `!selectedModelId` in useEffect |
| 14 | Provider metadata shown for non-preset voices with meta.provider | LOW | Bug | Not gated on creation_source |
