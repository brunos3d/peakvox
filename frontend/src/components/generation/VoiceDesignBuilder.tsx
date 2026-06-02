"use client"

import { useState } from "react"
import { Check, Plus, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
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
  VOICE_DESIGN_CATEGORIES,
  applyAttribute,
  attributeLabel,
} from "@/config/voice-design"

interface VoiceDesignBuilderProps {
  value: string[]
  onChange: (next: string[]) => void
  className?: string
  disabled?: boolean
}

const PLACEHOLDER = "Select speaker characteristics…"
const EXAMPLE_HINT = "Gender · Age · Pitch · Accent · Style"

export function VoiceDesignBuilder({
  value,
  onChange,
  className,
  disabled,
}: VoiceDesignBuilderProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")

  const selected = new Set(value)

  const toggle = (attr: string) => {
    // Selecting an active attribute removes it; otherwise add it, replacing any
    // existing attribute from the same category (one-per-category rule).
    onChange(selected.has(attr) ? value.filter((v) => v !== attr) : applyAttribute(value, attr))
  }

  const remove = (attr: string) => onChange(value.filter((v) => v !== attr))

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && search === "" && value.length > 0) {
      e.preventDefault()
      remove(value[value.length - 1])
    }
  }

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) setSearch("")
      }}
    >
      <PopoverAnchor asChild>
        <div
          role="button"
          tabIndex={disabled ? -1 : 0}
          aria-disabled={disabled}
          onClick={() => !disabled && setOpen(true)}
          onKeyDown={(e) => {
            if (disabled) return
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault()
              setOpen(true)
            }
          }}
          className={cn(
            "flex min-h-10 w-full flex-wrap items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1.5 text-sm",
            "ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            disabled ? "cursor-not-allowed opacity-50" : "cursor-text hover:border-ring/40",
            className,
          )}
        >
          {value.map((attr) => (
            <Badge
              key={attr}
              variant="secondary"
              className="gap-1 rounded-md py-0.5 pl-2 pr-1 font-normal"
            >
              {attributeLabel(attr)}
              <button
                type="button"
                aria-label={`Remove ${attributeLabel(attr)}`}
                onClick={(e) => {
                  e.stopPropagation()
                  remove(attr)
                }}
                className="rounded-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}

          {value.length === 0 ? (
            <span className="flex flex-col py-0.5 pl-1 text-muted-foreground">
              <span>{PLACEHOLDER}</span>
              <span className="text-[10px] text-muted-foreground/70">{EXAMPLE_HINT}</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 pl-1 text-xs text-muted-foreground">
              <Plus className="h-3 w-3" /> Add
            </span>
          )}
        </div>
      </PopoverAnchor>

      <PopoverContent className="w-[var(--radix-popover-trigger-width)] min-w-72 p-0" align="start">
        <Command loop>
          <CommandInput
            placeholder="Search characteristics…"
            value={search}
            onValueChange={setSearch}
            onKeyDown={handleInputKeyDown}
          />
          <CommandList>
            <CommandEmpty>No matching characteristics.</CommandEmpty>
            {VOICE_DESIGN_CATEGORIES.map((category) => (
              <CommandGroup key={category.id} heading={category.label}>
                {category.attributes.map((attr) => {
                  const isSelected = selected.has(attr.value)
                  return (
                    <CommandItem
                      key={attr.value}
                      value={attr.value}
                      keywords={[category.label]}
                      onSelect={() => toggle(attr.value)}
                    >
                      <Check
                        className={cn(
                          "h-4 w-4 shrink-0",
                          isSelected ? "opacity-100" : "opacity-0",
                        )}
                      />
                      <span className="flex-1">{attr.label ?? attr.value}</span>
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                        {category.label}
                      </span>
                    </CommandItem>
                  )
                })}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

// Re-exported for callers that build the instruct string from selections.
export { buildInstruct } from "@/config/voice-design"
