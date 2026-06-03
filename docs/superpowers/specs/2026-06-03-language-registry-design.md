# Language Registry — Design Spec

**Date:** 2026-06-03
**Status:** Approved (decisions confirmed)
**Sub-project:** B of the OmniVoice Phase 2 platform initiative

---

## Context

Phase 3 of the Phase 2 brief replaces the hardcoded 8-item language list with a
centralized registry covering all **646 languages** OmniVoice supports, plus a
searchable combobox UI.

Current hardcoded list (`["Auto","English","Portuguese","Spanish","French","German",
"Chinese","Japanese"]`) is duplicated in three places:
[page.tsx](../../../frontend/src/app/page.tsx), [VoiceEditDialog.tsx](../../../frontend/src/components/voice/VoiceEditDialog.tsx),
[VoiceWizard.tsx](../../../frontend/src/components/wizard/VoiceWizard.tsx).

The model receives the language verbatim — `omnivoice_service.generate(language=...)`
([omnivoice_service.py:266](../../../backend/app/services/omnivoice_service.py#L266)).
Today the app passes the display name (`"English"`).

### Source data

`docs/languages.md` (k2-fsa/OmniVoice) is a 4-column markdown table:

```
| # | Language | OmniVoice ID | ISO 639-3 | Duration (h) |
| 164 | English | en | eng | 206061.1 |
| 463 | Portuguese | pt | por | 16855.05 |
```

The brief's own example (`{ language_code: "pt", language: "Portuguese" }`) uses the
**OmniVoice ID** as `language_code`, not ISO 639-3.

## Confirmed decisions

1. **Model value:** send the **OmniVoice ID** to `generate(language=...)`. `name`
   (display) + `isoCode` (ISO 639-3) are metadata. Auto → `null` (unchanged).
2. **Generation:** commit a generated file + a regeneration script (no build-time
   network dependency).
3. **Flags:** curated flags for a small common set; `flag` stays optional for the rest.
4. **Grouping:** an `Auto` option pinned on top, a curated **Common** group, then an
   alphabetical **All languages** group.

---

## Architecture

### Data pipeline (generate, don't hand-maintain)

- **Vendored snapshot:** `frontend/scripts/languages.source.md` — committed copy of
  OmniVoice's languages.md (646 rows). Refreshed by re-downloading; documented in the
  script header.
- **Generator:** `frontend/scripts/generate-languages.mjs` — parses the markdown table
  with a pure `parseLanguages(markdown)` function and writes the typed array to
  `frontend/src/lib/languages.generated.ts`. The generated file carries a
  "DO NOT EDIT" banner.
- **Test:** `frontend/scripts/generate-languages.test.mjs` using Node's built-in
  `node:test` (zero new dependencies). Covers: 646 entries parsed, header/separator
  rows ignored, English → `{id:"en", isoCode:"eng", trainingHours:206061.1}`, fields
  trimmed.

### Overlay (hand-maintained, small)

`frontend/src/lib/languages.ts` imports the generated array and adds:

```ts
export interface SupportedLanguage {
  id: string          // OmniVoice ID — the value sent to the model (e.g. "en")
  name: string        // display name (e.g. "English")
  isoCode: string     // ISO 639-3 (e.g. "eng") — metadata
  trainingHours?: number
  flag?: string       // curated, optional
}

export const AUTO_LANGUAGE_ID = null            // "Auto" / auto-detect sentinel
export const COMMON_LANGUAGE_IDS: string[]      // curated common ids
export const LANGUAGE_FLAGS: Record<string, string>  // curated id → emoji

export const SUPPORTED_LANGUAGES: SupportedLanguage[]      // generated + flags merged
export function getLanguageById(id: string | null): SupportedLanguage | undefined
export function getLanguageByName(name: string): SupportedLanguage | undefined
export function getLanguageLabel(value: string | null): string  // for legacy display
export function searchLanguages(query: string): SupportedLanguage[]
```

`getLanguageByName` lets legacy voices (which stored a display name and may have a null
`language_code`) still resolve in the UI.

### Component

`frontend/src/components/common/LanguageCombobox.tsx`, built on the existing
[command.tsx](../../../frontend/src/components/ui/command.tsx) (cmdk) +
[popover.tsx](../../../frontend/src/components/ui/popover.tsx):

- Props: `value: string | null` (OmniVoice id, or null for Auto), `onChange(language:
  SupportedLanguage | null)`, optional `includeAuto` (default true).
- Auto option pinned at top; **Common** group; **All languages** alphabetical group.
- Fuzzy search via cmdk's default command-score; keyboard nav built in.
- Shows flag (when present) + name; training hours as a subtle hint.
- Trigger shows current selection (flag + name, or "Auto").

### Integration

- **TTS** ([page.tsx](../../../frontend/src/app/page.tsx)): replace the select with
  `LanguageCombobox`; track the selected `SupportedLanguage`. Send
  `language = lang?.id ?? null` in the generation request. Pass `lang?.name` to
  QuickPrompts (`resolveQuickPromptLanguage` expects a display label; it already falls
  back to English for unknowns).
- **Voice create/update** ([VoiceEditDialog.tsx](../../../frontend/src/components/voice/VoiceEditDialog.tsx),
  [VoiceWizard.tsx](../../../frontend/src/components/wizard/VoiceWizard.tsx)): replace the
  select; on save send `language = name` (display) and `language_code = id` (OmniVoice ID)
  — the create/update endpoints already accept `language_code` (sub-project A).

### Backend

No code change. `GenerationRequest.language` now carries the OmniVoice ID and passes
through to the model. Quick-prompt resolution stays in the frontend.

---

## Risks & mitigations

- **Model value change (display name → OmniVoice ID):** user-accepted; "en"/"pt" are the
  model's documented identifiers so risk is low, but a real generation must be verified
  (docker) before merge. Auto (`null`) is unaffected.
- **646-item combobox performance:** cmdk filters to matches, so typical render is small;
  add windowing only if the unfiltered open proves heavy.
- **Legacy voices:** `language_code` may be null and `language` holds a display name;
  `getLanguageByName` resolves them for display.
- **Quick prompts** cover only a few languages; existing English fallback handles the rest.

---

## Success criteria

- Single source of truth: all 646 languages from languages.md, generated not
  hand-maintained, with a committed regeneration script + test.
- All three hardcoded lists replaced by the searchable combobox.
- Selecting a language sends the OmniVoice ID to the model and stores
  display name + OmniVoice ID on voices.
- Existing voices still display their language correctly.
- `tsc --noEmit`, lint, and the parser test all pass.

## Execution order

1. Vendor `languages.source.md`.
2. Parser + generator + `node:test` (TDD).
3. Run generator → `languages.generated.ts`.
4. `languages.ts` overlay (interface, helpers, common ids, flags, Auto).
5. `LanguageCombobox` component.
6. Integrate into page.tsx, VoiceEditDialog, VoiceWizard.
7. Verify: parser test, `tsc --noEmit`, lint.
