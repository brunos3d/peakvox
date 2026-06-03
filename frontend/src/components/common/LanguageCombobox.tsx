"use client"

import { useMemo, useState } from "react"
import { Check, ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  ALL_LANGUAGES_SORTED,
  COMMON_LANGUAGES,
  getLanguageById,
  type SupportedLanguage,
} from "@/lib/languages"

interface LanguageComboboxProps {
  /** OmniVoice language id, or null for "Auto" / auto-detect. */
  value: string | null
  /** Receives the chosen language, or null when "Auto" is selected. */
  onChange: (language: SupportedLanguage | null) => void
  includeAuto?: boolean
  disabled?: boolean
  className?: string
}

const AUTO_VALUE = "__auto__"

function LanguageRow({ language, selected }: { language: SupportedLanguage; selected: boolean }) {
  return (
    <>
      <Check className={cn("h-4 w-4 shrink-0", selected ? "opacity-100" : "opacity-0")} />
      <span className="w-5 shrink-0 text-center">{language.flag ?? ""}</span>
      <span className="flex-1 truncate">{language.name}</span>
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {language.id}
      </span>
    </>
  )
}

export function LanguageCombobox({
  value,
  onChange,
  includeAuto = true,
  disabled,
  className,
}: LanguageComboboxProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")

  const selected = getLanguageById(value)

  // "Common" duplicates entries that also appear in "All languages"; cmdk needs unique
  // item values, so the common group's items use a prefixed value.
  const commonIds = useMemo(() => new Set(COMMON_LANGUAGES.map((l) => l.id)), [])

  const triggerLabel = !value
    ? "Auto"
    : selected
      ? `${selected.flag ? `${selected.flag} ` : ""}${selected.name}`
      : value

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        if (disabled) return
        setOpen(next)
        if (!next) setSearch("")
      }}
    >
      <PopoverAnchor asChild>
        <button
          type="button"
          disabled={disabled}
          aria-expanded={open}
          onClick={() => !disabled && setOpen((o) => !o)}
          className={cn(
            "flex h-10 w-full items-center justify-between gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm",
            "ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
            "disabled:cursor-not-allowed disabled:opacity-50",
            className,
          )}
        >
          <span className="truncate">{triggerLabel}</span>
          <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverAnchor>

      <PopoverContent className="w-[var(--radix-popover-trigger-width)] min-w-72 p-0" align="start">
        <Command loop>
          <CommandInput
            placeholder="Search 646 languages…"
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>No matching language.</CommandEmpty>

            {includeAuto && (
              <CommandGroup>
                <CommandItem
                  value={AUTO_VALUE}
                  keywords={["auto", "detect", "automatic"]}
                  onSelect={() => {
                    onChange(null)
                    setOpen(false)
                  }}
                >
                  <Check className={cn("h-4 w-4 shrink-0", !value ? "opacity-100" : "opacity-0")} />
                  <span className="w-5 shrink-0 text-center">✨</span>
                  <span className="flex-1">Auto</span>
                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    detect
                  </span>
                </CommandItem>
              </CommandGroup>
            )}

            <CommandGroup heading="Common">
              {COMMON_LANGUAGES.map((lang) => (
                <CommandItem
                  key={`common-${lang.id}`}
                  value={`common:${lang.id}`}
                  keywords={[lang.name, lang.isoCode]}
                  onSelect={() => {
                    onChange(lang)
                    setOpen(false)
                  }}
                >
                  <LanguageRow language={lang} selected={value === lang.id} />
                </CommandItem>
              ))}
            </CommandGroup>

            <CommandGroup heading="All languages">
              {ALL_LANGUAGES_SORTED.map((lang) => (
                <CommandItem
                  key={lang.id}
                  value={lang.id}
                  keywords={[lang.name, lang.isoCode, commonIds.has(lang.id) ? "common" : ""]}
                  onSelect={() => {
                    onChange(lang)
                    setOpen(false)
                  }}
                >
                  <LanguageRow language={lang} selected={value === lang.id} />
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
