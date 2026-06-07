# DESIGN — PeakVox Voice-First Frontend Alignment

> How violations are corrected. References SPEC. No backend architecture changes.

## Approach

Correct 10 frontend violations and 4 missing features identified in the architecture compliance audit. All changes are frontend-only unless backend compatibility is required. The backend architecture (ADRs, CompatibilityResolver, ImportResolver, settings_schema) is preserved and correct — the frontend must align to it.

## Key Design Decisions

### D1: Temporary Voice — Frontend-Only Construct

**Problem:** "Use Now" calls `importVoiceResource()`, creating persisted entities per ADR-0012 violation.

**Decision:** Construct a `TemporaryVoice` object from `VoiceResourceResponse` data entirely in the frontend. No new backend endpoint. No backend changes.

```typescript
interface TemporaryVoice {
  id: string                           // `${resource.id}_temporary`
  public_voice_id: string              // resource.id
  name: string
  language: string | null
  compatibleModels: string[]
  previewSummary: PreviewSummary
  creationSource: CreationSource
  isTemporary: true                    // discriminator: always true
  sourceResourceId: string             // backlink to VoiceResourceResponse.id
  meta?: { provider?: string }
}
```

The store's `selectedVoice` field becomes `VoiceProfile | TemporaryVoice | null`. Components that read `selectedVoice` branch on `isTemporary` for display purposes (subtitle "(Preset)", Import button in TTS panel).

**Why not a backend endpoint:** Adding a "temporary use" endpoint requires session state, TTL, or ephemeral storage — complexity that belongs nowhere. The frontend already has all the data it needs from `VoiceResourceResponse` to satisfy the `VoiceProfile` interface for generation.

**Why not promote to VoiceProfile type:** Adding `isTemporary` to `VoiceProfile` would conflate persisted and transient entities at the type level. A discriminated union is cleaner.

### D2: Per-Model Settings Store — Generic Key-Value

**Problem:** `GenerationSettings` type (types/index.ts:161-168) hardcodes OmniVoice-specific fields. No per-model settings persistence.

**Decision:** Replace `generationSettings: GenerationSettings` (hardcoded type) with `modelSettings: Record<string, Record<string, unknown>>` keyed by `model_id`.

```typescript
interface AppState {
  selectedVoice: VoiceProfile | TemporaryVoice | null
  selectedModelId: string | null
  modelSettings: Record<string, Record<string, unknown>>
  ttsLanguage: string | null
  // ...
}
```

Derived state: `currentModelSettings` = `modelSettings[selectedModelId] ?? {}`.

On model switch:
1. Save current settings: `modelSettings[oldModelId] = currentSettings`
2. Load new settings: `current = modelSettings[newModelId] ?? initializeFromSchema(newModel)`
3. Initialize from schema: iterate `settings_schema.properties`, extract `default` values

**Why `Record<string, unknown>` and NOT a discriminated union:**
- Every model has a different parameter set. A discriminated union over all models would need updating for every new model — violating the open-closed principle.
- `Record<string, unknown>` with `settings_schema` as the schema is isomorphic to JSON Schema validation — the schema declares the contract, the store holds instances.
- TypeScript `unknown` forces explicit validation before use, which the `settings_schema` provides at render time.

### D3: GenerationRequest — Model-Scoped Filter

**Problem:** `GenerationPanel.tsx:86` spreads all `generationSettings` unconditionally, sending OmniVoice-specific params (num_step, guidance_scale) even for Kokoro.

**Decision:** Before constructing `GenerationRequest`, filter `currentModelSettings` to only include keys declared in `activeModel.settings_schema.properties`.

```typescript
function filterSettingsForModel(
  settings: Record<string, unknown>,
  schema: SettingsSchema | null
): Record<string, unknown> {
  if (!schema || !schema.properties) return {}
  const allowedKeys = new Set(Object.keys(schema.properties))
  return Object.fromEntries(
    Object.entries(settings).filter(([key]) => allowedKeys.has(key))
  )
}
```

Change `GenerationRequest` type from hardcoded OmniVoice fields to:
```typescript
interface GenerationRequest {
  text: string
  voice_profile_id?: string
  model_id?: string
  language?: string
  params?: Record<string, unknown>  // replaces individual OmniVoice fields
}
```

The `params` field is backend-forwarded to the model adapter, which already validates and uses only the parameters it understands.

### D4: `primary_model_id` — Voice Owns Its Model

**Problem:** `VoiceProfile` type has no `primary_model_id` or `recommended_model_id`. ModelSelector pre-selects `m.is_default` instead of the voice's own model.

**Decision:** Add fields to `VoiceProfile` type, add selection logic to a `useModelForVoice` hook.

Selection priority:
1. `primary_model_id` (persisted, set at creation, never changes)
2. `recommended_model_id` (derived, may adapt over time)
3. First entry in `compatibleModels`
4. null (no compatible model — show empty state)

The auto-switch effect in `GenerationPanel` (line 56) changes from:
```typescript
// Current: guard prevents auto-selection when selectedModelId is null
if (!selectedModelId) return

// New: always run when voice changes, select primary or first compatible
const targetModelId = selectedProfile?.primaryModelId
  ?? selectedProfile?.recommendedModelId
  ?? selectedProfile?.compatibleModels?.[0]
  ?? null
if (targetModelId && targetModelId !== selectedModelId) {
  setSelectedModelId(targetModelId)
}
```

### D5: VoiceDetailPanel — Type-Gated Content

**Problem:** Transcript shown for PRESET_VOICE (gated on truthy `profile.transcript` instead of `creation_source`). Provider metadata shown for non-PRESET_VOICE (gated on truthy `meta.provider` instead of `creation_source`).

**Decision:** Replace truthiness checks with `creation_source` comparisons.

| Element | Current Gate | Correct Gate |
|---------|-------------|--------------|
| Transcript | `profile.transcript` | `profile.creation_source === "SOURCE_ASSET" && profile.transcript` |
| Provider metadata | `profile?.meta?.provider` | `profile.creation_source === "PRESET_VOICE" && profile?.meta?.provider` |
| Preview audio | `getVoiceAudioUrl(profile.id)` | Branch: if PRESET_VOICE → use `voice_previews[0].audio_url` or provider preview; else → `getVoiceAudioUrl` |

### D6: VariantDashboard — Three-State Matrix

**Problem:** "Not built" and "incompatible" share the same icon (VariantDashboard.tsx:130-132).

**Decision:** Add compatibility data to the matrix from `CompatibilityResolver` (already available as `profile.compatibleModels`). Three visual states:

| State | Icon | Color | Cell Action |
|-------|------|-------|-------------|
| Ready | ✅ CheckCircle | green | [Rebuild] |
| Buildable | ○ Circle | blue | [Build] |
| Incompatible | ✗ XCircle | gray | None (tooltip: "No build strategy for X voices") |

**How to get compatibility data:** The matrix already has `GET /variants/summary` for existing variants. Add a second data source: `compatibleModels` from the voice profiles (already in store). Merge them:

```typescript
function getCellState(voiceId: string, modelId: string): CellState {
  const variant = variantsByVoiceModel[voiceId]?.[modelId]
  if (variant?.status === 'ready') return 'ready'
  if (voice?.compatibleModels?.includes(modelId)) return 'buildable'
  return 'incompatible'
}
```

### D7: Pagination — Page-Based (or Cursor + Page Controls)

**Problem:** No PaginationControls component. Infinite scroll only.

**Decision:** Add a `PaginationControls` component that sits above the voice grid. It shows prev/next buttons, page numbers, and a page size selector.

**Design constraint:** The existing backend uses cursor-based pagination (`cursor` + `limit` query params, `has_next` + `next_cursor` in response). Adding page-based pagination is a backend change that is out of scope for this frontend-only alignment.

**Workaround:** Implement PaginationControls that translate page/pageSize into cursor-based calls:
- Page 1: `{limit: pageSize, cursor: null}` → `GET /voices?limit=50`
- Page 2: `{limit: pageSize, cursor: response.next_cursor}` → `GET /voices?limit=50&cursor=<next_cursor>`
- Prev/Next only (no arbitrary page jumping without backend page support)
- Page size selector changes `limit` param

This is a UX affordance over cursor-based pagination — users can navigate forward/backward and change page size, but cannot jump to page 5 directly.

**Future:** When backend adds `?page=` support, wire it directly.

### D8: Virtual Scrolling — react-virtuoso

**Problem:** All voices rendered in CSS grid. DOM bloat at 100+ voices.

**Decision:** Add `react-virtuoso` dependency. Create a `VirtualVoiceGrid` wrapper component.

- **Threshold:** Activate at 100+ voices. Below 100, render normally (no virtualization overhead).
- **Mode:** Variable-height grid mode (voice cards have variable heights due to differing content).
- **Fallback:** When virtualization is not active, use existing `VoiceGrid` component.
- **Scroll position:** Preserve scroll position on filter/sort changes using `scrollTop` ref.

**Why react-virtuoso:** Smaller bundle than react-window, native grid mode support, variable height support, simpler API.

### D9: Compatible Model + Provider Filters in Library

**Problem:** No `?compatible_model=` or `?provider=` filter in the library UI.

**Decision:** Add two filter chips to the library FilterBar:

1. **Compatible Model filter:**
   - Dropdown listing all active models (from store.models)
   - Selecting a model adds `?compatible_model=<model_id>` to the API call
   - Chip shows "Compatible: {model.name}" with remove button
   - Model list filtered to models that have compatible voice count > 0

2. **Provider filter:**
   - Dropdown showing distinct provider values from PRESET_VOICE voices in current results
   - Selecting a provider adds `?provider=<provider>` to the API call
   - Chip shows "Provider: {provider}" with remove button
   - Only visible when PRESET_VOICE voices exist in the current result set

**Backend dependency:** `?compatible_model=` and `?provider=` must be supported by `GET /voices`. The backend Phase J already specifies these filters. Verify they are implemented; if not, the frontend falls back to client-side filtering.

## Components Touched

| Component | Change |
|-----------|--------|
| `types/index.ts` | Add `primary_model_id`, `recommended_model_id` to `VoiceProfile`; add `TemporaryVoice` type; replace `GenerationSettings` with `Record<string, unknown>`; replace `GenerationRequest` fields with `params?: Record<string, unknown>` |
| `store/use-store.ts` | Replace `selectedProfile` + `generationSettings` with `selectedVoice` + `modelSettings`; add per-model switch logic; add temporary voice support |
| `hooks/use-models.ts` | Add `useModelForVoice` hook with selection priority |
| `hooks/use-generation.ts` | Add `filterSettingsForModel` helper |
| `components/voice/PresetVoicesTab.tsx` | Split "Use Now" (temporary) from "Import to Library"; add Preview action |
| `components/voice/VoiceSelector.tsx` | Handle `TemporaryVoice` display; show "(Preset)" subtitle |
| `components/voice/VoiceDetailPanel.tsx` | Fix type gates (transcript, provider metadata, preview); add Export action |
| `components/generation/GenerationPanel.tsx` | Fix auto-switch effect; filter generation request by model schema |
| `components/generation/GenerationSettingsFields.tsx` | Wire per-model settings |
| `components/DynamicSettingsForm.tsx` | Accept `Record<string, unknown>` values instead of typed settings |
| `components/voice/VariantDashboard.tsx` | Three-state matrix; compatibility-aware cells |
| `app/voices/page.tsx` | Add PaginationControls; add compatible_model + provider filter chips; switch to VirtualVoiceGrid at threshold |
| `components/voice/VoiceGrid.tsx` | Add virtual scrolling variant |
| `components/voice/VoiceCard.tsx` | Handle temporary voice card display (no edit/delete) |
| `components/generation/ModelSelector.tsx` | Highlight primary/recommended model; prevent incompatible selection |
| `components/common/PaginationControls.tsx` | **New component** |
| `components/voice/VirtualVoiceGrid.tsx` | **New component** |
| `components/api/FilterBar.tsx` | Add compatible_model + provider filter chips |

## Data / Schema Changes

**Frontend types only — no backend schema changes:**

- `VoiceProfile`: add `primaryModelId: string | null`, `recommendedModelId: string | null`
- `GenerationRequest`: replace OmniVoice fields with `params?: Record<string, unknown>`
- Remove `GenerationSettings` hardcoded type (replace with `Record<string, unknown>`)
- Remove `GenerationRequest` hardcoded OmniVoice fields

**Store shape change:**
- `selectedProfile` → `selectedVoice` (wider union type)
- `generationSettings` → `modelSettings` (per-model key-value map)
- Add `isTemporaryVoice: boolean` derived from `selectedVoice`

## Capability / Edition Gating

All changes are CE-compatible. No Cloud-specific features. No edition gating.

## Constrained by ADRs

- ADR-0012 (Voice Identity vs Catalog Resources) — N1 temporary selection
- ADR-0004 (Voice-Variant-Model Separation) — N2 primary_model_id
- ADR-0003 (Model Capability Contract) — N3 model-scoped settings
- ADR-0011 (Voice Creation Sources) — N4 type-gated display
- ADR-0001 (Voice-Variant Split) — N8 variant matrix states

## Risks

1. **Backend not returning `primary_model_id`** — The field may not be in the backend `VoiceProfile` schema yet. Mitigation: `primaryModelId` is `string | null`; when null, fall back to current behavior (first compatible model or default).

2. **Backend not supporting `?compatible_model=` filter** — Phase J4 specifies it, but it may not be implemented. Mitigation: frontend falls back to client-side filtering (iterate voices, filter by `compatibleModels.includes(modelId)`).

3. **Backend not supporting `?provider=` filter** — Phase J4 specifies it. Mitigation: frontend falls back to client-side filtering.

4. **Cursor-based pagination UX** — Page-based navigation without arbitrary page jumping may confuse power users. Mitigation: show "Prev" / "Next" buttons clearly; add page number display ("Page 2"); document that arbitrary page jumping requires backend `?page=` support.

5. **Per-model settings migration** — Existing users have settings in the current flat `generationSettings` store. On first load with new store shape, migrate by assigning current settings to the current model's key in `modelSettings`.

6. **Temporary voice discarded on navigation** — If user navigates away from TTS page, temporary voice is lost. Mitigation: this is intentional — temporary voices are ephemeral. Show a confirmation if user has unsaved generation text.
