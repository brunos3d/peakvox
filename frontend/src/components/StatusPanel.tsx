"use client"

import { Loader2, CheckCircle, XCircle, Clock, AlertTriangle } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useJobStatus } from "@/hooks/use-generation"
import { useAppStore } from "@/store/use-store"
import type { JobStatus } from "@/types"

const statusConfig: Record<JobStatus, { label: string; color: string; icon: React.ReactNode }> = {
  pending: {
    label: "Queued",
    color: "bg-yellow-500/10 text-yellow-500 border-yellow-500/30",
    icon: <Clock className="h-3 w-3" />,
  },
  processing: {
    label: "Processing",
    color: "bg-blue-500/10 text-blue-500 border-blue-500/30",
    icon: <Loader2 className="h-3 w-3 animate-spin" />,
  },
  completed: {
    label: "Completed",
    color: "bg-green-500/10 text-green-500 border-green-500/30",
    icon: <CheckCircle className="h-3 w-3" />,
  },
  failed: {
    label: "Failed",
    color: "bg-red-500/10 text-red-500 border-red-500/30",
    icon: <XCircle className="h-3 w-3" />,
  },
}

export function StatusPanel() {
  const activeJobId = useAppStore((s) => s.activeJobId)
  const activeJobStatus = useAppStore((s) => s.activeJobStatus)
  const { data: job } = useJobStatus(activeJobId)

  if (!activeJobId) {
    return (
      <Card className="p-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm">No active generation</span>
        </div>
      </Card>
    )
  }

  const status = activeJobStatus || "pending"
  const config = statusConfig[status]

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={`gap-1 ${config.color}`}>
            {config.icon}
            {config.label}
          </Badge>
        </div>
        <span className="text-xs text-muted-foreground font-mono">
          {activeJobId.slice(0, 8)}...
        </span>
      </div>

      {(status === "pending" || status === "processing") && (
        <Progress value={status === "pending" ? 10 : 50} className="h-1" />
      )}

      {job?.logs && job.logs.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Inference Logs</p>
          <ScrollArea className="h-24 rounded border bg-muted/50 p-2">
            {job.logs.map((log, i) => (
              <p key={i} className="text-[11px] font-mono text-muted-foreground leading-relaxed">
                {log}
              </p>
            ))}
          </ScrollArea>
        </div>
      )}

      {status === "failed" && job?.error_message && (
        <div className="rounded bg-destructive/10 p-2">
          <p className="text-xs text-destructive font-mono">{job.error_message}</p>
        </div>
      )}

      {status === "completed" && job?.audio_duration && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>Duration: {job.audio_duration.toFixed(2)}s</span>
          <span>Generated: {new Date(job.completed_at!).toLocaleTimeString()}</span>
        </div>
      )}
    </Card>
  )
}
