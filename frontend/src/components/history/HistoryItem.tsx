"use client"

import { Play, Download, RotateCcw, Trash2, Loader2, CheckCircle2, XCircle, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatDuration, cn } from "@/lib/utils"
import type { JobResponse, JobStatus } from "@/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const STATUS: Record<JobStatus, { label: string; cls: string; icon: React.ReactNode }> = {
  pending: { label: "Queued", cls: "text-warning border-warning/30 bg-warning/10", icon: <Clock className="h-3 w-3" /> },
  processing: { label: "Processing", cls: "text-info border-info/30 bg-info/10", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
  completed: { label: "Completed", cls: "text-success border-success/30 bg-success/10", icon: <CheckCircle2 className="h-3 w-3" /> },
  failed: { label: "Failed", cls: "text-error border-error/30 bg-error/10", icon: <XCircle className="h-3 w-3" /> },
}

async function download(url: string, filename: string) {
  try {
    const res = await fetch(url)
    const blob = await res.blob()
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = objectUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(objectUrl)
  } catch {
    window.open(url, "_blank")
  }
}

interface HistoryItemProps {
  job: JobResponse
  voiceName?: string
  active?: boolean
  outputFormat: "wav" | "mp3" | "ogg"
  onPlay: (job: JobResponse) => void
  onRegenerate: (job: JobResponse) => void
  onDelete: (job: JobResponse) => void
}

export function HistoryItem({ job, voiceName, active, outputFormat, onPlay, onRegenerate, onDelete }: HistoryItemProps) {
  const status = STATUS[job.status]
  const isCompleted = job.status === "completed"

  const handleDownload = () => {
    const url = outputFormat === "wav" ? `${API_URL}/jobs/${job.id}/audio` : `${API_URL}/jobs/${job.id}/audio/${outputFormat}`
    download(url, `omnivoice-${job.id}.${outputFormat}`)
  }

  return (
    <div className={cn("flex items-center gap-4 rounded-xl border bg-surface p-4 transition-colors", active ? "border-primary" : "border-border hover:bg-surface-2")}>
      <Button
        variant="secondary"
        size="icon"
        className="h-10 w-10 shrink-0 rounded-full"
        disabled={!isCompleted}
        onClick={() => onPlay(job)}
        title="Play"
      >
        <Play className="h-4 w-4" />
      </Button>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-foreground/90">{job.text}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <Badge variant="outline" className={cn("gap-1 px-1.5 py-0 text-[10px]", status.cls)}>
            {status.icon}{status.label}
          </Badge>
          {voiceName && <span className="text-caption">{voiceName}</span>}
          <span className="text-caption">{new Date(job.created_at).toLocaleString()}</span>
          {job.audio_duration != null && <span className="text-caption tabular-nums">{formatDuration(job.audio_duration)}</span>}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-0.5">
        <Button variant="ghost" size="icon" className="h-8 w-8" disabled={!isCompleted} onClick={handleDownload} title="Download">
          <Download className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onRegenerate(job)} title="Regenerate">
          <RotateCcw className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-error hover:text-error" onClick={() => onDelete(job)} title="Delete">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
