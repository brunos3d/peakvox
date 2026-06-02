import { type LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center rounded-xl border border-dashed border-border bg-surface/40 px-6 py-16",
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-2 text-muted-foreground">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-section-title">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
