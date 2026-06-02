"use client"

import { useState } from "react"
import { Menu, AudioLines } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { AppSidebar } from "@/components/shell/AppSidebar"
import { BottomPlayer } from "@/components/shell/BottomPlayer"
import { useVoices } from "@/hooks/use-generation"

export function AppShell({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  // Load voices once for the whole app (pages read from the store).
  useVoices()

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-border bg-surface">
        <AppSidebar />
      </aside>

      {/* Mobile sidebar */}
      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="w-64 p-0 bg-surface">
          <AppSidebar onNavigate={() => setMenuOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Main column */}
      <div className="flex flex-1 min-w-0 flex-col">
        <header className="md:hidden flex items-center gap-3 h-14 px-4 border-b border-border bg-surface">
          <Button variant="ghost" size="icon" onClick={() => setMenuOpen(true)} title="Menu">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2">
            <AudioLines className="h-5 w-5 text-primary" />
            <span className="font-semibold">OmniVoice</span>
          </div>
        </header>

        <main className="flex-1 min-h-0 overflow-hidden">{children}</main>

        <BottomPlayer />
      </div>
    </div>
  )
}
