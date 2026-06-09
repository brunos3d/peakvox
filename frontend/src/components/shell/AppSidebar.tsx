"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { AudioLines, Library, Mic, History, Settings, LayoutDashboard, KeyRound, Code2, BarChart3, Cpu, type LucideIcon } from "lucide-react"
import { useActiveModel } from "@/hooks/use-models"
import { fetchDeviceSettings } from "@/lib/api"
import { StatusRow } from "@/components/shell/StatusRow"
import { cn } from "@/lib/utils"

interface NavItem {
  href: string
  label: string
  icon: LucideIcon
}

const NAV: NavItem[] = [
  { href: "/", label: "Text to Speech", icon: AudioLines },
  { href: "/voices", label: "Voice Library", icon: Library },
  { href: "/models", label: "Models", icon: Cpu },
  { href: "/clone", label: "Voice Clone", icon: Mic },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
]

const API_NAV: NavItem[] = [
  { href: "/api", label: "Overview", icon: LayoutDashboard },
  { href: "/api/keys", label: "API Keys", icon: KeyRound },
  { href: "/api/voices", label: "Voice API", icon: Code2 },
  { href: "/api/usage", label: "Usage", icon: BarChart3 },
]

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/"
  return pathname === href || pathname.startsWith(href + "/")
}

export function AppSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  const { activeModel } = useActiveModel()
  const { data: device } = useQuery({
    queryKey: ["device-settings"],
    queryFn: fetchDeviceSettings,
    refetchInterval: 15000,
  })

  const apiOnline = true
  const modelActive = activeModel?.activation_status === "active"
  const modelTone = modelActive ? "success" : activeModel ? "error" : "muted"
  const modelValue = modelActive ? "Ready" : activeModel ? "Offline" : "—"
  const gpuTone = device?.use_gpu && device?.cuda_available ? "success" : device?.cuda_available ? "info" : "muted"
  const gpuValue = !device
    ? "—"
    : device.use_gpu && device.cuda_available
      ? "GPU"
      : device.cuda_available
        ? "GPU idle"
        : "CPU"

  return (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-16 border-b border-border">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <AudioLines className="h-5 w-5" />
        </div>
        <span className="font-semibold tracking-tight">PeakVox</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {NAV.map((item) => {
          const active = isActive(pathname, item.href)
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/12 text-primary font-medium"
                  : "text-muted-foreground hover:bg-surface-2 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          )
        })}

        {/* API section */}
        <p className="px-3 pb-1 pt-5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
          API
        </p>
        {API_NAV.map((item) => {
          const active = pathname === item.href
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/12 text-primary font-medium"
                  : "text-muted-foreground hover:bg-surface-2 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Status footer */}
      <div className="border-t border-border py-2">
        <StatusRow label="System" value={apiOnline ? "Online" : "Offline"} tone={apiOnline ? "success" : "error"} />
        <StatusRow label="Model" value={modelValue} tone={modelTone} />
        <StatusRow label="GPU" value={gpuValue} tone={gpuTone} />
      </div>
    </div>
  )
}
