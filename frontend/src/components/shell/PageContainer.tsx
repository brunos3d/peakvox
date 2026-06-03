import { cn } from "@/lib/utils"

interface PageContainerProps {
  children: React.ReactNode
  className?: string
}

/**
 * Server Component. The standard scrollable, padded content column — the same
 * frame {@link PageLayout} renders when it has no context panel, minus the
 * client machinery. Use this for pages (or section layouts) that don't need a
 * stateful right-hand panel, so the page itself can stay a Server Component.
 */
export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <div className="flex h-full min-h-0">
      <div className={cn("flex-1 min-w-0 overflow-y-auto px-6 lg:px-10 py-8", className)}>
        {children}
      </div>
    </div>
  )
}
