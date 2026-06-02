"use client"

import { cn } from "@/lib/utils"

type StatusTone = "success" | "warning" | "error" | "info" | "muted"

const toneDot: Record<StatusTone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
  info: "bg-info",
  muted: "bg-muted-foreground/50",
}

interface StatusRowProps {
  label: string
  value: string
  tone?: StatusTone
  pulse?: boolean
}

export function StatusRow({ label, value, tone = "muted", pulse }: StatusRowProps) {
  return (
    <div className="flex items-center justify-between gap-2 px-3 py-1.5 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-1.5 text-foreground/90">
        <span className={cn("h-2 w-2 rounded-full", toneDot[tone], pulse && "animate-pulse")} />
        {value}
      </span>
    </div>
  )
}
