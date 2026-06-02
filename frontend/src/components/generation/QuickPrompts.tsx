"use client"

import {
  QUICK_PROMPT_CATEGORIES,
  quickPrompts,
  resolveQuickPromptLanguage,
} from "@/config/quick-prompts"

interface QuickPromptsProps {
  /** Currently selected language label (e.g. "English", "Auto"). */
  language: string
  /** Fired with the full prompt text for the active language + category. */
  onSelect: (text: string) => void
}

/**
 * Language-aware quick-prompt buttons. Content is fully driven by the
 * centralized config in `@/config/quick-prompts`, so categories and languages
 * can be added there without touching this component.
 *
 * Visibility (show only when the textarea is empty) is controlled by the
 * parent via conditional rendering + a fade wrapper, keeping this component
 * purely presentational.
 */
export function QuickPrompts({ language, onSelect }: QuickPromptsProps) {
  const langKey = resolveQuickPromptLanguage(language)
  const content = quickPrompts[langKey]

  return (
    <div className="flex flex-wrap gap-2">
      {QUICK_PROMPT_CATEGORIES.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          type="button"
          onClick={() => onSelect(content[id])}
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
        >
          <Icon className="h-4 w-4 text-primary" />
          {label}
        </button>
      ))}
    </div>
  )
}
