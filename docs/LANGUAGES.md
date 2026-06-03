# Language Registry

OmniVoice supports **646 languages**. The frontend ships a centralized, generated
registry rather than a hand-maintained list.

> See also: [Voice Model](VOICE_MODEL.md) · [API](API.md)

---

## Source of truth

The list is generated from OmniVoice's official `docs/languages.md`, vendored at
`frontend/scripts/languages.source.md`. Its table has four columns:

```
| # | Language | OmniVoice ID | ISO 639-3 | Duration (h) |
| 164 | English | en | eng | 206061.1 |
| 463 | Portuguese | pt | por | 16855.05 |
```

**Never edit the language list by hand.** Edit the source snapshot and regenerate.

---

## Pipeline

```
languages.source.md ──(scripts/generate-languages.mjs)──► src/lib/languages.generated.ts
                                                                 │
                                          src/lib/languages.ts (curated overlay)
```

- `scripts/generate-languages.mjs` — parses the markdown table (pure `parseLanguages`,
  unit-tested with `node --test scripts/generate-languages.test.mjs`) and writes the
  typed `GENERATED_LANGUAGES` array (DO NOT EDIT).
- `src/lib/languages.ts` — the curated overlay: the `SupportedLanguage` interface,
  common-language ordering, representative flags, and lookup/search helpers.

### Regenerating

```bash
cd frontend
# optional: refresh the snapshot from upstream
curl -sSL https://raw.githubusercontent.com/k2-fsa/OmniVoice/refs/heads/master/docs/languages.md \
  -o scripts/languages.source.md
node scripts/generate-languages.mjs      # rewrites src/lib/languages.generated.ts
node --test scripts/generate-languages.test.mjs
```

---

## The `SupportedLanguage` shape

```ts
interface SupportedLanguage {
  id: string        // OmniVoice ID — the value sent to the model (e.g. "en")
  name: string      // display name (e.g. "English")
  isoCode: string   // ISO 639-3 (e.g. "eng") — metadata
  trainingHours?: number
  flag?: string     // curated, optional (most of the 646 have none)
}
```

### Which value goes where

- **Sent to the model** (`generate(language=…)`) and stored as a voice's
  `language_code`: the **OmniVoice ID** (`en`, `pt`). This matches the brief's example
  `{ language_code: "pt", language: "Portuguese" }`.
- **Display** (`language`, voice cards, pickers): the `name`.
- `isoCode` is carried as metadata for interoperability.
- `Auto` (auto-detect) is represented as `null` (no language sent).

Legacy voices created before the registry may store a display name with no
`language_code`; `getLanguageByName` resolves them for display.

---

## UI

`LanguageCombobox` (`src/components/common/LanguageCombobox.tsx`) is a searchable
combobox (cmdk) with: an `Auto` option pinned on top, a curated **Common** group, an
alphabetical **All languages** group, fuzzy search, keyboard navigation, and flags. It is
used by the TTS screen, the voice create/edit flows, and the library's language filter.
