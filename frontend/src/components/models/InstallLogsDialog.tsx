"use client"

import * as React from "react"
import { Loader2, CheckCircle2, XCircle, Terminal } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { fetchRuntimeInstallLogs, type RuntimeInstallLogs } from "@/lib/api"

const POLL_INTERVAL_MS = 1000

/**
 * Terminal-style modal that shows the real `docker build` / `docker pull`
 * output captured during a runtime install — for advanced users who want to
 * watch the image being built instead of only the coarse "Pulling runtime image
 * (30%)" step text. Polls GET /runtimes/{id}/install-logs while open and the
 * install is active; auto-scrolls to follow the output.
 */
export function InstallLogsDialog({
  runtimeId,
  imageRef,
  open,
  onOpenChange,
}: {
  runtimeId: string
  imageRef?: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [logs, setLogs] = React.useState<RuntimeInstallLogs | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const scrollRef = React.useRef<HTMLDivElement | null>(null)
  // Track whether the user has scrolled up, so we don't yank them back down.
  const stickToBottomRef = React.useRef(true)

  React.useEffect(() => {
    if (!open) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    const tick = async () => {
      try {
        const next = await fetchRuntimeInstallLogs(runtimeId)
        if (cancelled) return
        setLogs(next)
        setError(null)
        // Keep polling while the install is still running; otherwise stop.
        if (next.active) {
          timer = setTimeout(tick, POLL_INTERVAL_MS)
        }
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : "Failed to load logs")
        timer = setTimeout(tick, POLL_INTERVAL_MS)
      }
    }

    tick()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [open, runtimeId])

  // Auto-scroll to the bottom when new lines arrive, unless the user scrolled up.
  React.useEffect(() => {
    const el = scrollRef.current
    if (el && stickToBottomRef.current) {
      el.scrollTop = el.scrollHeight
    }
  }, [logs?.seq])

  const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    stickToBottomRef.current = nearBottom
  }

  const lines = logs?.lines ?? []
  const status: "running" | "done" | "failed" | "idle" = !logs
    ? "idle"
    : logs.active
      ? "running"
      : logs.ok === false
        ? "failed"
        : logs.ok === true
          ? "done"
          : "idle"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Terminal className="h-4 w-4" />
            Install logs
            <StatusBadge status={status} />
          </DialogTitle>
          <DialogDescription className="font-mono text-xs break-all">
            {imageRef ? imageRef : runtimeId}
          </DialogDescription>
        </DialogHeader>

        <div
          ref={scrollRef}
          onScroll={onScroll}
          className="h-[55vh] overflow-y-auto rounded-md border border-border bg-[#0b0b0c] p-3 font-mono text-[11px] leading-relaxed text-zinc-200"
        >
          {lines.length === 0 ? (
            <p className="text-zinc-500">
              {status === "running"
                ? "Waiting for build output…"
                : "No install output captured yet. Output appears here while the image is being built or pulled."}
            </p>
          ) : (
            lines.map((line, i) => (
              <div key={i} className="whitespace-pre-wrap break-all">
                {line || " "}
              </div>
            ))
          )}
          {error && (
            <p className="mt-2 text-error">Could not refresh logs: {error}</p>
          )}
        </div>

        <DialogFooter className="sm:justify-between">
          <span className="text-[11px] text-muted-foreground self-center">
            {status === "running"
              ? "Live — refreshing every second"
              : status === "done"
                ? "Build completed"
                : status === "failed"
                  ? logs?.error || "Build failed"
                  : ""}
          </span>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function StatusBadge({ status }: { status: "running" | "done" | "failed" | "idle" }) {
  if (status === "running") {
    return (
      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium bg-warning/15 text-warning">
        <Loader2 className="h-3 w-3 animate-spin" /> building
      </span>
    )
  }
  if (status === "done") {
    return (
      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium bg-success/15 text-success">
        <CheckCircle2 className="h-3 w-3" /> done
      </span>
    )
  }
  if (status === "failed") {
    return (
      <span className={cn("inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium bg-error/15 text-error")}>
        <XCircle className="h-3 w-3" /> failed
      </span>
    )
  }
  return null
}
