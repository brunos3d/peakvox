// Centralized language registry. The full list is generated from OmniVoice's
// languages.md (see languages.generated.ts + scripts/generate-languages.mjs) and must
// never be hand-maintained. This module adds the small, curated overlay: common-language
// ordering, flags, and lookup/search helpers.

import { GENERATED_LANGUAGES } from "./languages.generated"

export interface SupportedLanguage {
  /** OmniVoice language ID — the value sent to the model's generate(language=...). */
  id: string
  name: string
  /** ISO 639-3 code (metadata). */
  isoCode: string
  trainingHours?: number
  /** Curated, optional — most of the 646 languages have none. */
  flag?: string
}

/** Curated short list surfaced in the "Common" group, in display order. */
export const COMMON_LANGUAGE_IDS = [
  "en",
  "es",
  "pt",
  "fr",
  "de",
  "it",
  "ru",
  "zh",
  "ja",
  "ko",
  "hi",
  "arb",
] as const

/** Best-effort representative flags for common languages (languages ≠ countries). */
export const LANGUAGE_FLAGS: Record<string, string> = {
  en: "🇬🇧",
  es: "🇪🇸",
  pt: "🇵🇹",
  fr: "🇫🇷",
  de: "🇩🇪",
  it: "🇮🇹",
  ru: "🇷🇺",
  zh: "🇨🇳",
  ja: "🇯🇵",
  ko: "🇰🇷",
  hi: "🇮🇳",
  arb: "🇸🇦",
}

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = GENERATED_LANGUAGES.map((l) => ({
  ...l,
  flag: LANGUAGE_FLAGS[l.id],
}))

const BY_ID = new Map(SUPPORTED_LANGUAGES.map((l) => [l.id, l]))
const BY_NAME = new Map(SUPPORTED_LANGUAGES.map((l) => [l.name.toLowerCase(), l]))

export function getLanguageById(id: string | null | undefined): SupportedLanguage | undefined {
  return id ? BY_ID.get(id) : undefined
}

export function getLanguageByName(name: string | null | undefined): SupportedLanguage | undefined {
  return name ? BY_NAME.get(name.toLowerCase()) : undefined
}

/**
 * Resolve a stored value to a display label. Accepts either an OmniVoice id (current)
 * or a legacy display name (older voices), falling back to the raw value, then "Auto".
 */
export function getLanguageLabel(value: string | null | undefined): string {
  if (!value) return "Auto"
  return (getLanguageById(value) ?? getLanguageByName(value))?.name ?? value
}

export const COMMON_LANGUAGES: SupportedLanguage[] = COMMON_LANGUAGE_IDS.map((id) =>
  BY_ID.get(id),
).filter((l): l is SupportedLanguage => Boolean(l))

export const ALL_LANGUAGES_SORTED: SupportedLanguage[] = [...SUPPORTED_LANGUAGES].sort(
  (a, b) => a.name.localeCompare(b.name),
)

/** Simple substring search across name, OmniVoice id, and ISO code. */
export function searchLanguages(query: string): SupportedLanguage[] {
  const q = query.trim().toLowerCase()
  if (!q) return ALL_LANGUAGES_SORTED
  return ALL_LANGUAGES_SORTED.filter(
    (l) =>
      l.name.toLowerCase().includes(q) ||
      l.id.toLowerCase().includes(q) ||
      l.isoCode.toLowerCase().includes(q),
  )
}
