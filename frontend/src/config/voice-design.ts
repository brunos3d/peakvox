// Controlled vocabulary for the OmniVoice Voice Design Builder.
//
// Single source of truth for every speaker attribute the model accepts. To
// support new OmniVoice attributes, add them here — the builder UI, validation,
// and instruct-string generation all derive from this file automatically.
//
// Rule enforced by the builder: only ONE attribute per category may be active.
// Reference: https://github.com/k2-fsa/OmniVoice/blob/master/docs/voice-design.md

export interface VoiceAttribute {
  /** The exact token sent to OmniVoice (e.g. "young adult"). */
  value: string
  /** Human-facing label (defaults to value when omitted). */
  label?: string
}

export interface VoiceCategory {
  id: string
  /** Group heading shown in the picker and per-item category hint. */
  label: string
  attributes: VoiceAttribute[]
}

export const VOICE_DESIGN_CATEGORIES: VoiceCategory[] = [
  {
    id: "gender",
    label: "Gender",
    attributes: [{ value: "male" }, { value: "female" }],
  },
  {
    id: "age",
    label: "Age",
    attributes: [
      { value: "child" },
      { value: "teenager" },
      { value: "young adult" },
      { value: "middle-aged" },
      { value: "elderly" },
    ],
  },
  {
    id: "pitch",
    label: "Pitch",
    attributes: [
      { value: "very low pitch" },
      { value: "low pitch" },
      { value: "moderate pitch" },
      { value: "high pitch" },
      { value: "very high pitch" },
    ],
  },
  {
    id: "style",
    label: "Style",
    attributes: [{ value: "whisper" }],
  },
  {
    id: "accent",
    label: "English Accent",
    attributes: [
      { value: "american accent" },
      { value: "british accent" },
      { value: "australian accent" },
      { value: "canadian accent" },
      { value: "indian accent" },
      { value: "chinese accent" },
      { value: "korean accent" },
      { value: "japanese accent" },
      { value: "portuguese accent" },
      { value: "russian accent" },
    ],
  },
  {
    id: "dialect",
    label: "Chinese Dialect",
    attributes: [
      { value: "河南话" },
      { value: "陕西话" },
      { value: "四川话" },
      { value: "贵州话" },
      { value: "云南话" },
      { value: "桂林话" },
      { value: "济南话" },
      { value: "石家庄话" },
      { value: "甘肃话" },
      { value: "宁夏话" },
      { value: "青岛话" },
      { value: "东北话" },
    ],
  },
]

/** Maps an attribute value to the category it belongs to. */
const VALUE_TO_CATEGORY = new Map<string, VoiceCategory>(
  VOICE_DESIGN_CATEGORIES.flatMap((category) =>
    category.attributes.map((attr) => [attr.value, category] as const),
  ),
)

/** Returns the category for an attribute value, or undefined if unknown. */
export function categoryOf(value: string): VoiceCategory | undefined {
  return VALUE_TO_CATEGORY.get(value)
}

/** Human label for an attribute value (falls back to the value itself). */
export function attributeLabel(value: string): string {
  const category = VALUE_TO_CATEGORY.get(value)
  const attr = category?.attributes.find((a) => a.value === value)
  return attr?.label ?? value
}

/** True when the value is part of the supported controlled vocabulary. */
export function isValidAttribute(value: string): boolean {
  return VALUE_TO_CATEGORY.has(value)
}

/**
 * Adds `value` to the current selection, replacing any existing attribute from
 * the same category (enforces the one-per-category rule). Unknown values are
 * ignored. Returns a new array.
 */
export function applyAttribute(current: string[], value: string): string[] {
  const category = VALUE_TO_CATEGORY.get(value)
  if (!category) return current
  const withoutCategory = current.filter(
    (v) => VALUE_TO_CATEGORY.get(v)?.id !== category.id,
  )
  return [...withoutCategory, value]
}

/**
 * Builds the flat `instruct` string OmniVoice expects, e.g.
 * "male, young adult, low pitch, british accent". Returns "" when empty.
 */
export function buildInstruct(values: string[]): string {
  return values.join(", ")
}
