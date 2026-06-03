import { AppSidebar } from "@/components/shell/AppSidebar"
import { BottomPlayer } from "@/components/shell/BottomPlayer"
import { MobileNav } from "@/components/shell/MobileNav"
import { VoicesPreloader } from "@/components/shell/VoicesPreloader"

/**
 * Server Component. Lays out the static application frame and composes the
 * interactive pieces as client islands (sidebar, mobile nav, bottom player,
 * voices preloader). `children` (the page) keeps rendering on the server.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-border bg-surface">
        <AppSidebar />
      </aside>

      {/* Main column */}
      <div className="flex flex-1 min-w-0 flex-col">
        {/* Mobile top bar + slide-over (client island) */}
        <MobileNav />

        <main className="flex-1 min-h-0 overflow-hidden">{children}</main>

        <BottomPlayer />
      </div>

      {/* Warm the voices query once for the whole app (renders nothing) */}
      <VoicesPreloader />
    </div>
  )
}
