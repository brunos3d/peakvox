# PeakVox Voice-First Frontend Alignment — Specification

> **Status:** DRAFT
> **Date:** 2026-06-07
> **Context:** Real-world product testing revealed that the frontend implementation does not behave according to the Voice-First architecture established by `peakvox-voice-system-evolution`. This spec defines the expected user-facing behavior and the corrections required to bring the frontend into compliance.
> **Method:** Behavior-first specification. Every section defines expected user-facing behavior, then identifies the current deviation, then prescribes the correction. No backend architecture changes.
> **Audience:** Frontend engineers, UX reviewers, QA validators.

---

## Table of Contents

1. [Voice-First Principle](#1-voice-first-principle)
2. [Voice Library](#2-voice-library)
3. [Preset Catalog](#3-preset-catalog)
4. [TTS Generation Flow](#4-tts-generation-flow)
5. [Model Selection Architecture](#5-model-selection-architecture)
6. [Generation Settings](#6-generation-settings)
7. [Compatibility Enforcement](#7-compatibility-enforcement)
8. [Temporary Voice Selection](#8-temporary-voice-selection)
9. [VoiceDetailPanel](#9-voicedetailpanel)
10. [Variant Dashboard (Voice Matrix)](#10-variant-dashboard-voice-matrix)
11. [Store Architecture](#11-store-architecture)
12. [Frontend / Backend Contract Audit](#12-frontend--backend-contract-audit)
13. [User Journey Validation Scenarios](#13-user-journey-validation-scenarios)

---

## 1. Voice-First Principle

### 1.1 Definition

PeakVox is Voice-First. This means:

**Primary navigation axis is Voice.**

```
User thinks:       "I want to use a voice."
User does:         Select Voice → Compatible Models appear → Select Model → Settings appear
User never:        Select Model → Then search for compatible voices
```

**Models are infrastructure, not product.**

```
Voice        → determines compatible models
Model        → determines supported languages
Model        → determines generation settings
Model        → determines available capabilities
```

**Invalid combinations must be impossible, not warned about.**

```
Voice Larissa (OmniVoice clone)
  → compatible models: [omnivoice-base, omnivoice-singing]
  → Kokoro should NEVER appear in the model list
  → User should NEVER see "This voice is not compatible with Kokoro"

Voice Alloy (Kokoro preset)
  → compatible models: [kokoro-base]
  → OmniVoice should NEVER appear in the model list
```

### 1.2 Current Violations

| Violation | Location | Description |
|-----------|----------|-------------|
| Model-first fallback | ModelSelector, useActiveModel | Default model is selected when no model chosen, even if incompatible with selected voice |
| Warning as primary UX | GenerationPanel.tsx:252-258 | Incompatibility warning shown instead of preventing selection |
| No primary_model_id | VoiceProfile type, store, GenerationPanel | Voice does not own its preferred model |
| Bidirectional filter gap | GenerationPanel.tsx:52-63 | Auto-switch effect requires `selectedModelId` to be set; when null, no auto-selection occurs |

### 1.3 Required Corrections

1. Voice MUST always be selected or explicitly absent before model matters.
2. When voice is selected, `primary_model_id` MUST auto-select the model.
3. The model selector MUST only show compatible models.
4. The model selector MUST show a "no compatible models" state (not a list with incompatible entries hidden).
5. Warnings about incompatibility MUST be unreachable in normal flow; they are a crash-safe fallback only.

---

## 2. Voice Library

### 2.1 Expected Contents

The Voice Library (`/voices`) contains only persisted Voices:

| Voice Type | Creation Source | Present in Library? |
|------------|----------------|---------------------|
| Cloned voice | SOURCE_ASSET | Yes — created via audio upload |
| Imported preset | PRESET_VOICE | Yes — imported via "Import to Library" |
| Marketplace voice | MARKETPLACE_VOICE | Yes — purchased and imported (future) |
| Generated voice | GENERATED_VOICE | Yes — created via generation (future) |
| External voice | IMPORTED_VOICE | Yes — imported from external source (future) |
| System voice | SYSTEM_VOICE | Yes — built-in system voices (future) |
| Catalog preset | (not persisted) | **No** — never in library |
| Temporary selection | (not persisted) | **No** — never in library |

### 2.2 Current Violations

1. **"Use Now" imports presets** — Temporary selections become permanent library entries via `importVoiceResource()`.
2. **No `compatible_model` filter** — Library has no way to filter voices by compatible model, making multi-provider scale unmanageable.
3. **No `provider` filter** — PRESET_VOICE voices from different providers cannot be filtered in the library view.
4. **No pagination controls** — "Load more" button instead of proper PaginationControls.
5. **No virtual scrolling** — All voices rendered in CSS grid regardless of count.

### 2.3 Required Corrections

1. Library loads from `GET /voices` — voices persisted via import, clone, or future purchase.
2. Library NEVER receives entries from "Use Now" or temporary selection.
3. Library has `?compatible_model=` filter chip.
4. Library has `?provider=` filter chip (visible when PRESET_VOICE voices exist).
5. PaginationControls component with prev/next, page numbers, page size selector.
6. Virtual scrolling at 100+ voices threshold.
7. Default sort: `last_used_at DESC` (most recently used first).

### 2.4 Voice Card Behaviors per Type

| Element | SOURCE_ASSET | PRESET_VOICE (imported) |
|---------|-------------|------------------------|
| Badge | "Cloned" (blue) | "Preset" (purple) |
| Play button | Shown if `preview_summary.origin !== "none"` | Shown if `preview_summary.origin !== "none"` |
| Duration | Shown if previewable | Shown if previewable |
| Provider badge | Hidden | Shown (from `meta.provider`) |
| Transcript | Shown if available | **Never shown** |
| Reference audio | Shown if available | **Never shown** |
| Edit action | Available | Available |
| Delete action | Available | Available |

---

## 3. Preset Catalog

### 3.1 Expected Behavior

The Preset Catalog (`/voices` tab "Preset Voices") shows transient `VoiceResourceResponse` objects. These are catalog descriptors, NOT library voices.

**Two distinct actions:**
1. **Use in TTS** — temporary selection for immediate generation. Creates NO persisted entities.
2. **Import to Library** — creates VoiceProfile + VoiceVariant + VoiceVariantArtifact. Adds to library.

### 3.2 Current Violations

1. `PresetVoicesTab.tsx:149-167` — Both "Use Now" and "Library" buttons call `importVoiceResource()`. No temporary selection path exists.
2. `PresetVoicesTab.tsx:177-196` — "Use Now" button has a Play icon, implying preview, but actually imports.
3. No visual distinction between "temporary use" and "import" in the UI.
4. After "Use Now", the voice appears in My Voices — polluting the library with test selections.

### 3.3 Required Corrections

1. "Use in TTS" action:
   - Does NOT call `importVoiceResource()`
   - Constructs a **temporary voice profile** from the `VoiceResourceResponse` data
   - Sets this temporary profile as the selected voice in the store
   - Navigates to TTS page
   - Temporary profile is indicated with "(Preset)" subtitle in the TTS Voice Selector
2. "Import to Library" action:
   - Calls `importVoiceResource(voice.id)` as before
   - Invalidates library queries
   - Shows success feedback
   - Optionally navigates to Library tab
3. Preset card showing `is_in_library == true`:
   - "Use in TTS" still available (no import needed)
   - "Import" button becomes "In Library" badge (disabled)
4. New action: "Preview" — plays the preset's `preview_audio_url` if available.

### 3.4 Preset Card Layout

```
┌──────────────────────────────────┐
│ Voice Name                       │
│ Provider · Language · Gender     │
│ Description (truncated)          │
│                                  │
│ [▶ Preview] [🎯 Use in TTS] [+ Import] │
└──────────────────────────────────┘
```

---

## 4. TTS Generation Flow

### 4.1 Expected Flow

```
User arrives at TTS page
  │
  ├── Voice Selector shows ALL library voices (none selected)
  ├── Model Selector shows default model
  ├── Settings render from model's settings_schema
  ├── Languages filtered by model's supported_languages
  └── Generate button disabled (no voice selected)

User selects a voice
  │
  ├── Model selector filters to compatible models
  ├── primary_model_id is pre-selected automatically
  ├── Settings update to match new model's settings_schema
  ├── Languages update to match new model's supported_languages
  └── Generate button enabled (voice + model + text)

User optionally changes model
  │
  ├── Voice selector filters to compatible voices (current voice kept if compatible)
  ├── Settings update to match new model's settings_schema
  ├── Languages update to match new model's supported_languages
  └── If current voice incompatible: user must select a compatible voice

User clicks Generate
  │
  └── GenerationRequest includes ONLY params from model's settings_schema
```

### 4.2 Current Violations

| Step | Expected | Current |
|------|----------|---------|
| Voice selected | Auto-select `primary_model_id` | No auto-selection; user must manually pick model |
| Model changed | Voice selector filters to compatible | Voice selector filters correctly |
| Settings | From `settings_schema` only | DynamicSettingsForm renders correctly, BUT GenerationRequest sends ALL OmniVoice fields unconditionally |
| Languages | From `supported_languages` | Correctly implemented |
| Generate payload | Filtered by model schema | `...generationSettings` spreads all fields |

### 4.3 Required Corrections

1. Voice selection MUST pre-select `primary_model_id` (or `recommended_model_id`, or first compatible).
2. Generate request MUST filter `generationSettings` to only include fields from the active model's `settings_schema`.
3. The auto-switch `useEffect` in GenerationPanel MUST work even when `selectedModelId` is null.
4. When voice is changed and the current model becomes incompatible, the system MUST auto-switch to the voice's `primary_model_id` (not show a warning).

---

## 5. Model Selection Architecture

### 5.1 Expected Behavior

```
VoiceProfile
├── compatible_models: string[]       // from CompatibilityResolver
├── primary_model_id: string | null   // persisted, set at creation
└── recommended_model_id: string | null  // derived, may change over time

Selection rules:
1. If primary_model_id exists and is compatible → select it
2. Else if recommended_model_id exists and is compatible → select it
3. Else if compatible_models has entries → select first
4. Else → no model selected, show "No compatible models for this voice"
```

### 5.2 Current Violations

1. `VoiceProfile` type has NO `primary_model_id` or `recommended_model_id`.
2. `ModelSelector` pre-selects `m.is_default` — NOT the voice's own model.
3. `GenerationPanel` auto-switch picks first compatible model — NOT primary.
4. No `recommended_model_id` in frontend types.

### 5.3 Required Corrections

1. Add `primary_model_id: string | null` to `VoiceProfile` type.
2. Add `recommended_model_id: string | null` to `VoiceProfile` type.
3. Add model selection logic to `useActiveModel` or a new `useModelForVoice` hook.
4. When voice is selected, apply selection rules (1→2→3→4).
5. `ModelSelector` should indicate which model is primary/recommended.

### 5.4 Model Selector States

| State | Behavior |
|-------|----------|
| No voice selected | Show all active models; default model pre-selected |
| Voice selected (has primary_model_id) | Filter to compatible; highlight primary as "Primary (recommended)" |
| Voice selected (no primary, has compatible) | Filter to compatible; pre-select first |
| Voice selected (no compatible models) | Show empty state "No compatible models for this voice" |
| All models compatible | Show all models |

---

## 6. Generation Settings

### 6.1 Expected Behavior

**Every model declares its own settings_schema.** The frontend:
1. Reads `model.settings_schema` from the model descriptor
2. Renders ONLY the parameters declared in `settings_schema`
3. Forwards ONLY the parameters declared in `settings_schema` in the generation request
4. Stores settings per-model (preserving user adjustments when switching models)

### 6.2 Model Settings Schemas

**OmniVoice Base:**
```json
{
  "num_step": { "type": "number", "label": "Inference Steps", "default": 32, "min": 4, "max": 64 },
  "guidance_scale": { "type": "number", "label": "Guidance Scale", "default": 2.0, "min": 0, "max": 4 },
  "speed": { "type": "number", "label": "Speed", "default": null, "min": 0.5, "max": 1.5 },
  "duration": { "type": "number", "label": "Duration", "default": null, "min": 1, "max": 120 },
  "t_shift": { "type": "number", "label": "Time Shift", "default": 0.1, "min": 0, "max": 1 },
  "denoise": { "type": "boolean", "label": "Denoise", "default": true }
}
```

**Kokoro Base:**
```json
{
  "speed": { "type": "number", "label": "Speed", "default": 1.0, "min": 0.5, "max": 2.0 }
}
```

**Fish Audio (future):**
```json
{
  "speed": { "type": "number", "label": "Speed", "default": 1.0, "min": 0.5, "max": 1.5 },
  "similarity": { "type": "number", "label": "Similarity", "default": 0.8, "min": 0, "max": 1 },
  "stability": { "type": "number", "label": "Stability", "default": 0.5, "min": 0, "max": 1 }
}
```

**XTTS (future):**
```json
{
  "speed": { "type": "number", "label": "Speed", "default": 1.0, "min": 0.5, "max": 2.0 },
  "temperature": { "type": "number", "label": "Temperature", "default": 0.75, "min": 0.1, "max": 1.0 },
  "repetition_penalty": { "type": "number", "label": "Repetition Penalty", "default": 2.0, "min": 1.0, "max": 10.0 }
}
```

**F5-TTS (future):**
```json
{
  "speed": { "type": "number", "label": "Speed", "default": 1.0, "min": 0.5, "max": 2.0 },
  "cross_attention": { "type": "select", "label": "Cross-Attention", "default": "semi-implicit", "options": ["semi-implicit", "full"] }
}
```

**CosyVoice (future):**
```json
{
  "speed": { "type": "number", "label": "Speed", "default": 1.0, "min": 0.5, "max": 2.0 },
  "emotion": { "type": "select", "label": "Emotion", "default": "neutral", "options": ["neutral", "happy", "sad", "angry", "surprised"] }
}
```

**Spark-TTS (future):**
```json
{
  "speed": { "type": "number", "label": "Speed", "default": 1.0, "min": 0.5, "max": 2.0 },
  "temperature": { "type": "number", "label": "Temperature", "default": 0.8, "min": 0.1, "max": 1.5 },
  "top_k": { "type": "number", "label": "Top-K", "default": 50, "min": 1, "max": 100 }
}
```

### 6.3 Current Violations

1. **Store has hardcoded OmniVoice fields** — `GenerationSettings` type (types/index.ts:161-168) hardcodes `num_step`, `guidance_scale`, `speed`, `duration`, `t_shift`, `denoise` — all OmniVoice-specific.
2. **GenerationRequest has hardcoded OmniVoice fields** — (types/index.ts:126-140).
3. **No per-model settings persistence** — Single flat `generationSettings` object in store. Switching from Kokoro (speed only) to OmniVoice (6 params) and back loses Kokoro speed setting.
4. **GenerationPanel spreads all settings** — `GenerationPanel.tsx:86` unconditionally spreads `...generationSettings`.

### 6.4 Required Corrections

1. Make `GenerationSettings` store type generic: `Record<string, unknown>` instead of hardcoded fields.
2. Store settings per-model: `Record<string, Record<string, unknown>>` keyed by `model_id`.
3. On model switch: save current settings to `perModelSettings[currentModelId]`, load `perModelSettings[newModelId]` or initialize from new model's `settings_schema` defaults.
4. `GenerationRequest` type: use `model_params?: Record<string, unknown>` instead of individual fields.
5. `DynamicSettingsForm` (already correct) continues to render from `schema.properties`.
6. `GenerationRequest` construction: filter `generationSettings` to only include keys from `activeModel.settings_schema.properties`.

---

## 7. Compatibility Enforcement

### 7.1 Expected Behavior

Compatibility is enforced at every selection point:

```
User selects Voice:
  → ModelSelector filters to compatible_models
  → primary_model_id pre-selected
  → No incompatible model is ever selectable

User selects Model:
  → VoiceSelector filters to voices where voice.compatible_models.includes(modelId)
  → Incompatible voices are not shown (not grayed, not warned — hidden)

User views VoiceDetailPanel:
  → Compatible Models section shows:
    ✓ compatible + variant ready
    ✓ compatible + variant missing (buildable)
    ✗ incompatible (never buildable)

User views Variant Dashboard:
  → Matrix shows three states:
    ✓ ready variant exists
    ○ compatible but not built
    ✗ incompatible
```

### 7.2 Current Violations

1. Incompatibility warning shown instead of filtering (GenerationPanel.tsx:252-258).
2. VariantDashboard cannot distinguish "not built" from "incompatible" (VariantDashboard.tsx:130-132).
3. No `compatible_model` filter in Library.

### 7.3 Required Corrections

1. Remove all "incompatibility warnings" from normal user flow. Warnings are a crash-safe fallback only, never the primary UX.
2. VoiceSelector must filter voices when model is selected (already correct — VoiceSelector.tsx:31-45).
3. ModelSelector must filter models when voice is selected (already correct — ModelSelector.tsx:40-46).
4. Auto-select model on voice change (NEEDS FIX — GenerationPanel.tsx:52-63).
5. VariantDashboard must show 3 states: compatible+ready, compatible+missing, incompatible.
6. Library must have `?compatible_model=` filter chip.
7. Backfill button must only process compatible voice×model pairs.

---

## 8. Temporary Voice Selection

### 8.1 Expected Behavior

Temporary voice selection is the act of choosing a voice for immediate use WITHOUT persisting it. This applies to:

- **Preset "Use in TTS"** — user wants to try a preset without importing
- **Future: Marketplace preview** — user wants to test a voice before purchasing

The temporary selection is:
- Stored in frontend state only (Zustand store)
- Never sent to backend
- Never persisted to database
- Indicated with a visual marker "(Preset)" in the TTS Voice Selector
- Functions identically to a library voice for generation purposes

### 8.2 Temporary Voice Contract

A temporary voice satisfies the same interface as `VoiceProfile` for the TTS panel:

```typescript
interface TemporaryVoice {
  id: string                    // resource.id + "_temporary" suffix
  public_voice_id: string       // resource.id
  name: string                  // from VoiceResourceResponse
  language: string | null       // from VoiceResourceResponse
  compatible_models: string[]   // from VoiceResourceResponse
  preview_summary: PreviewSummary
  creation_source: CreationSource  // mapped from resource_type
  // Consumer-only fields (not persisted):
  is_temporary: true            // discriminator from VoiceProfile
  source_resource_id: string    // reference back to VoiceResourceResponse.id
}
```

### 8.3 Current Violations

No temporary voice concept exists. All voice selections require a `VoiceProfile`.

### 8.4 Required Corrections

1. Add `is_temporary` field to the store's selected voice tracking.
2. When "Use in TTS" is clicked on a preset:
   - Construct a `TemporaryVoice` from the `VoiceResourceResponse`
   - Set it as the selected voice in the store
   - Navigate to TTS
3. TTS Voice Selector shows "(Preset)" subtitle for temporary voices.
4. Below the Voice Selector, show an "Import to Library" button when a temporary voice is selected.
5. Import from TTS panel triggers `importVoiceResource()` and replaces the temporary selection with the persisted `VoiceProfile`.
6. Temporary voice is discarded when user selects a different voice or leaves TTS page.

---

## 9. VoiceDetailPanel

### 9.1 Expected Layout

```
┌──────────────────────────────────────────────────┐
│ Header                                           │
│  [Name]                          creation_source  │
│  [Language]                      ★ Favorite       │
│  [Provider badge (PRESET_VOICE only)]             │
├──────────────────────────────────────────────────┤
│ Overview                                         │
│  Description (if available)                      │
│  Provider metadata (PRESET_VOICE only)           │
│  Language · Created · Last used                  │
│  Usage count                                     │
│  Transcript (SOURCE_ASSET only)                  │
│  Tags (PRESET_VOICE only)                        │
├──────────────────────────────────────────────────┤
│ Previews                                         │
│  AudioPlayer (if preview_summary.origin !== none)│
│  "No preview available" (if origin === none)     │
│  Preview language selector (multiple previews)   │
├──────────────────────────────────────────────────┤
│ Compatible Models                                │
│  Model name          Status       Actions         │
│  omnivoice-base      ✓ Ready      [Rebuild]       │
│  fish-audio-s2       ○ Buildable  [Build]         │
│  kokoro-base         ✗ Incompatible               │
├──────────────────────────────────────────────────┤
│ Variants                                         │
│  (delegated to VariantManager)                   │
├──────────────────────────────────────────────────┤
│ Actions                                          │
│  [Use in TTS] [Export] [★ Favorite] [Delete]     │
│                                                  │
│  (VoiceResource not in library):                 │
│  [Use in TTS] [Import to Library]                │
│                                                  │
│  (Temporary selection):                          │
│  [Use in TTS] [Import to Library] [Discard]      │
└──────────────────────────────────────────────────┘
```

### 9.2 Section Collapse Rules

| Section | Visible when... |
|---------|-----------------|
| Header | Always |
| Overview | Always; provider metadata when `creation_source === "PRESET_VOICE"`; transcript when `creation_source === "SOURCE_ASSET"` AND transcript data exists |
| Previews | `preview_summary.origin !== "none"` |
| Compatible Models | Always |
| Variants | At least one variant exists OR can be built |
| Actions | Always (content varies by voice type and ownership) |

### 9.3 Information Visibility by Voice Type

| Element | SOURCE_ASSET | PRESET_VOICE | VoiceResource | Temporary |
|---------|-------------|-------------|---------------|-----------|
| Transcript | ✅ Show | ❌ Hide | ❌ Hide | ❌ Hide |
| Provider metadata | ❌ Hide | ✅ Show | ✅ Show | ✅ Show |
| Reference audio | ✅ Show if exists | ❌ Hide | ❌ Hide | ❌ Hide |
| Preview audio | ✅ Show if `preview_summary` | ✅ Show from provider | ✅ Show from `preview_audio_url` | ✅ Show from `preview_audio_url` |
| Usage count | ✅ Show | ✅ Show | ❌ Hide | ❌ Hide |
| Created date | ✅ Show | ✅ Show | ❌ Hide | ❌ Hide |
| Last used | ✅ Show | ✅ Show | ❌ Hide | ❌ Hide |
| Variants | ✅ Show | ✅ Show | ❌ Hide | ❌ Hide |
| Favorite toggle | ✅ Show | ✅ Show | ❌ Hide | ❌ Hide |
| Edit action | ✅ Show | ✅ Show | ❌ Hide | ❌ Hide |
| Delete action | ✅ Show | ✅ Show | ❌ Hide | ❌ Hide |
| Import action | ❌ Hide | ❌ Hide (already imported) | ✅ Show | ✅ Show |
| "Use in TTS" | ✅ Show | ✅ Show | ✅ Show | ✅ Show |

### 9.4 Current Violations

1. Transcript shown for PRESET_VOICE (`VoiceDetailPanel.tsx:213-218` — gated on truthy `profile.transcript`, not `creation_source`).
2. Provider metadata shown for non-PRESET_VOICE with `meta.provider` (`VoiceDetailPanel.tsx:179-186`).
3. Previews section uses `getVoiceAudioUrl()` for profiles unconditionally — presets may not have reference audio.
4. No Export action (missing from K7).
5. No compact mode (missing from K9).
6. No "Import to Library" action within TTS panel for temporary voices.

---

## 10. Variant Dashboard (Voice Matrix)

### 10.1 Expected States

The Variant Dashboard must display three distinct states for every voice×model cell:

| State | Icon | Label | Meaning | Action |
|-------|------|-------|---------|--------|
| Ready | ✅ CheckCircle (green) | Ready | Variant exists and is usable | [Rebuild] |
| Compatible + missing | ○ Circle (blue) | Buildable | No variant yet, but can be built | [Build] |
| Incompatible | ✗ XCircle (gray) | Incompatible | This model cannot use this voice | None |
| Building | ⟳ Spinner (blue) | Building… | Variant build in progress | None |
| Failed | ⚠ Warning (red) | Failed | Variant build failed | [Retry] |

### 10.2 Compatibility Rule for Matrix

```
A voice V is compatible with model M IF:
  (a) a ready VoiceVariant exists for (V, M), OR
  (b) M's adapter declares a VariantBuildStrategy for
      V.creation_source with can_build=True
```

The matrix MUST read from CompatibilityResolver, not just variant_summary.

### 10.3 Current Violations

1. VariantDashboard.tsx:130-132 — "missing" and "incompatible" use the same icon.
2. Matrix reads from `GET /variants/summary` only — cannot distinguish buildable from incompatible.
3. Backfill button runs on ALL missing variants, including incompatible ones.
4. No visual indication of WHY a model is incompatible with a voice.

### 10.4 Required Corrections

1. Add CompatibilityResolver data to the matrix (compatible models per voice).
2. Three distinct visual states: ready / buildable / incompatible.
3. Backfill must only process compatible pairs.
4. Hover/tooltip on incompatible cells: "This model has no build strategy for {creation_source} voices."
5. Hover/tooltip on buildable cells: "No variant yet. Click Build to create one."

---

## 11. Store Architecture

### 11.1 Current Store Layout

The Zustand store currently holds:

```typescript
interface AppState {
  selectedProfile: VoiceProfile | null
  generationSettings: GenerationSettings  // Hardcoded OmniVoice fields
  selectedModelId: string | null
  voices: VoiceProfile[]
  ttsLanguage: string | null
  // ... other fields
}
```

### 11.2 Required Store Layout

```typescript
interface PerModelSettings {
  [modelId: string]: Record<string, unknown>
}

interface AppState {
  // Voice
  selectedVoice: VoiceProfile | TemporaryVoice | null
  isTemporaryVoice: boolean
  voices: VoiceProfile[]

  // Model
  selectedModelId: string | null

  // Generation Settings — per-model, generic key-value
  modelSettings: PerModelSettings
  currentModelSettings: Record<string, unknown>  // derived, for current model

  // Language
  ttsLanguage: string | null

  // ... other fields (ttsText, outputFormat, etc.)
}
```

### 11.3 Required Actions

1. Replace `selectedProfile` with `selectedVoice` that accepts `VoiceProfile | TemporaryVoice | null`.
2. Add `isTemporaryVoice` boolean discriminator.
3. Replace hardcoded `GenerationSettings` with `PerModelSettings` (generic per-model key-value).
4. Add `currentModelSettings` derived from `modelSettings[selectedModelId]`.
5. On model switch: save `currentModelSettings` to `modelSettings[oldModelId]`, load `modelSettings[newModelId]` or initialize from `settings_schema` defaults.

---

## 12. Frontend / Backend Contract Audit

### 12.1 Fields Added by Backend Architecture (Phases A-L)

| Field | Added In | Present in Frontend Types? | Used in Frontend? |
|-------|----------|---------------------------|-------------------|
| `settings_schema` on Model | Phase A | ✅ `Model.settings_schema` | ✅ DynamicSettingsForm |
| `compatible_models` on Voice | Phase B | ✅ `VoiceProfile.compatible_models` | ✅ VoiceSelector, ModelSelector |
| `creation_source` on Voice | Phase D | ✅ `VoiceProfile.creation_source` | ✅ VoiceCard badges |
| `preview_summary` on Voice | Phase D/E | ✅ `VoiceProfile.preview_summary` | ✅ VoiceCard, VoiceDetailPanel |
| `voice_features` on Model | Phase F | ✅ `Model.voice_features` | ✅ ModelCard |
| `VoiceResourceResponse` | Phase H | ✅ `VoiceResourceResponse` | ✅ PresetVoicesTab |
| `is_in_library` on VoiceResource | Phase H | ✅ `VoiceResourceResponse.is_in_library` | ✅ PresetVoicesTab |
| `last_used_at` on Voice | Phase L | ✅ `VoiceProfile.last_used_at` | ✅ Sort, filter chips |
| `primary_model_id` on Voice | SPEC §13 | ❌ **MISSING** | ❌ Not used |
| `recommended_model_id` on Voice | SPEC §13 | ❌ **MISSING** | ❌ Not used |
| `resource_type` on VoiceResource | Phase H | ✅ `VoiceResourceResponse.resource_type` | ✅ PresetVoicesTab filter |
| `resource_origin` on VoiceResource | Phase H | ✅ `VoiceResourceResponse.resource_origin` | ✅ PresetVoicesTab filter |

### 12.2 Missing Contract Fields

| Field | Expected In | Action Required |
|-------|------------|-----------------|
| `primary_model_id: string \| null` | `VoiceProfile` | Add to type, assume backend returns it |
| `recommended_model_id: string \| null` | `VoiceProfile` | Add to type, assume backend returns it |

### 12.3 Incorrect Contract Fields

| Field | Current Type | Correct Type | Action Required |
|-------|-------------|--------------|-----------------|
| `GenerationSettings` (161-168) | Hardcoded fields | `Record<string, unknown>` | Replace |
| `GenerationRequest` (126-140) | Individual OmniVoice fields | `model_params?: Record<string, unknown>` | Replace individual params with generic map |

---

## 13. User Journey Validation Scenarios

### Scenario 1: New user exploring presets

**User actions:**
1. Opens Preset Catalog tab
2. Searches for "Bella"
3. Clicks "Use in TTS" on Bella (Kokoro preset)

**Expected:**
- No VoiceProfile created
- No VoiceVariant created
- No VoiceVariantArtifact created
- Navigated to TTS page
- Bella selected as temporary voice
- Model auto-selected to kokoro-base (Bella's primary model)
- Only Kokoro settings visible (speed)
- Only Kokoro languages visible
- TTS Voice Selector shows "Bella (Preset)" with "(Preset)" subtitle
- "Import to Library" button visible below selector

### Scenario 2: User imports a preset

**User actions:**
1. Opens Preset Catalog
2. Clicks "Import to Library" on Bella

**Expected:**
- VoiceProfile created
- VoiceVariant created for kokoro-base
- VoiceVariantArtifact created (v1)
- Toast notification: "Bella added to your library"
- Bella appears in My Voices tab
- Bella's badge shows "Preset" in purple

### Scenario 3: User switches model when voice is selected

**User actions:**
1. Selects voice "Larissa" (OmniVoice clone, primary=omnivoice-base)
2. Tries to select Kokoro in model selector

**Expected:**
- Kokoro does NOT appear in model selector (Larissa incompatible)
- Only omnivoice-base, omnivoice-singing shown
- omnivoice-base highlighted as "Primary"

### Scenario 4: User selects model first

**User actions:**
1. Selects "Kokoro" model
2. Opens Voice Selector

**Expected:**
- Voice Selector shows ONLY Kokoro-compatible voices
- Alloy, Bella, Aoede, Heart shown
- Larissa, Bruno, Jarvis NOT shown
- Count badge: "5 compatible · 0 total"
- No incompatible state warning shown

### Scenario 5: User changes model, settings preserved per model

**User actions:**
1. Selects OmniVoice model
2. Changes Inference Steps to 48
3. Changes Speed to 1.2x
4. Switches to Kokoro model
5. Changes Speed to 1.8x
6. Switches back to OmniVoice

**Expected:**
- OmniVoice settings restored: Inference Steps=48, Speed=1.2x
- Kokoro settings preserved: Speed=1.8x (if switched back again)

### Scenario 6: User views variant dashboard

**User actions:**
1. Opens Variant Dashboard

**Expected:**
- Each cell shows one of: ✅ Ready, ○ Buildable, ✗ Incompatible
- OmniVoice/Larissa × Kokoro = ✗ Incompatible (no Kokoro build strategy for SOURCE_ASSET)
- Kokoro/Bella × Kokoro = ✅ Ready (imported variant exists)
- Kokoro/Bella × OmniVoice = ✗ Incompatible (no OmniVoice build strategy for PRESET_VOICE)
- Backfill only processes Buildable cells, not Incompatible

### Scenario 7: User opens voice details

**User actions:**
1. Double-clicks imported preset voice "Bella"

**Expected:**
- VoiceDetailPanel opens
- Header shows "Preset" badge (purple), language, provider (Kokoro)
- Overview shows: provider metadata, language, created date, tags
- Overview does NOT show: transcript, reference audio
- Previews: shows if provider supplies preview audio
- Compatible Models: kokoro-base shown as compatible+ready
- Omnivoice-base shown as incompatible with explanation
- Actions: Use in TTS, Favorite, Delete

### Scenario 8: User generates speech with Kokoro

**User actions:**
1. Selects Bella (Kokoro preset)
2. Types text
3. Clicks Generate

**Expected:**
- GenerationRequest payload contains ONLY: `{text, model_id: "kokoro-base", voice_profile_id, speed}`
- Does NOT contain: num_step, guidance_scale, duration, t_shift, denoise
- Generation succeeds

### Scenario 9: Voice Library pagination

**User at 200+ voices:**
- Pagination controls visible (prev/next, page numbers, page size)
- Default page size: 50
- Page size options: 25, 50, 100, 200
- Total count: "Showing 1-50 of 1,234 voices"
- Virtual scrolling active at 100+ voices

### Scenario 10: Library filter by compatible model

**User actions:**
1. Has 200 voices (mixed OmniVoice, Kokoro, Fish Audio presets)
2. Selects filter: "Compatible with: Kokoro"

**Expected:**
- Library shows only voices where `compatible_models` includes "kokoro-base"
- 10 voices shown (Alloy, Bella, Aoede, Heart, and 6 other Kokoro presets)
- All OmniVoice clones and Fish Audio presets hidden
- Filter chip shows "Compatible: kokoro-base" with remove button
