"use client"

import { useState } from "react"
import { PanelRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"

interface PageLayoutProps {
  children: React.ReactNode
  contextPanel?: React.ReactNode
  contextTitle?: string
  className?: string
}

/**
 * Standard page frame: a scrollable content column plus an optional right
 * context panel. On wide screens the panel is docked; on tablet/mobile it
 * collapses behind a "Panel" trigger that opens a slide-over sheet.
 */
export function PageLayout({ children, contextPanel, contextTitle = "Panel", className }: PageLayoutProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex h-full min-h-0">
      <div className={cn("flex-1 min-w-0 overflow-y-auto px-6 lg:px-10 py-8", className)}>
        {children}
      </div>

      {contextPanel && (
        <>
          <aside className="hidden xl:flex w-[360px] shrink-0 flex-col overflow-y-auto border-l border-border bg-surface/40">
            {contextPanel}
          </aside>

          <div className="xl:hidden fixed bottom-24 right-5 z-30">
            <Button
              size="icon"
              variant="secondary"
              className="h-11 w-11 rounded-full shadow-lg"
              onClick={() => setOpen(true)}
              title={contextTitle}
            >
              <PanelRight className="h-5 w-5" />
            </Button>
          </div>

          <Sheet open={open} onOpenChange={setOpen}>
            <SheetContent side="right" className="w-[360px] p-0">
              <SheetHeader className="border-b border-border">
                <SheetTitle>{contextTitle}</SheetTitle>
              </SheetHeader>
              <div className="flex-1 overflow-y-auto">{contextPanel}</div>
            </SheetContent>
          </Sheet>
        </>
      )}
    </div>
  )
}
