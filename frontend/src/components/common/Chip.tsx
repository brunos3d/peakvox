"use client"

import { cn } from "@/lib/utils"

interface ChipProps {
  label: string
  active?: boolean
  onClick?: () => void
  icon?: React.ReactNode
}

/** A small toggleable filter pill. */
export function Chip({ label, active, onClick, icon }: ChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
        active
          ? "border-primary/40 bg-primary/12 text-primary"
          : "border-border bg-surface text-muted-foreground hover:text-foreground hover:bg-surface-2"
      )}
    >
      {icon}
      {label}
    </button>
  )
}
