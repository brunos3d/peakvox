"use client"

import { useState } from "react"
import { Menu, AudioLines } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { AppSidebar } from "@/components/shell/AppSidebar"

/**
 * Client island for mobile navigation: the `md:hidden` top bar with the menu
 * trigger plus the slide-over sheet that hosts the sidebar. Owns the open/close
 * state so the rest of the shell frame can stay a Server Component.
 */
export function MobileNav() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <>
      <header className="md:hidden flex items-center gap-3 h-14 px-4 border-b border-border bg-surface">
        <Button variant="ghost" size="icon" onClick={() => setMenuOpen(true)} title="Menu">
          <Menu className="h-5 w-5" />
        </Button>
        <div className="flex items-center gap-2">
          <AudioLines className="h-5 w-5 text-primary" />
          <span className="font-semibold">OmniVoice</span>
        </div>
      </header>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="w-64 p-0 bg-surface">
          <AppSidebar onNavigate={() => setMenuOpen(false)} />
        </SheetContent>
      </Sheet>
    </>
  )
}
