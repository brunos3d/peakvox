"use client"

import { useState, useRef, useEffect } from "react"
import { Play, Pause, Download, Loader2, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu"
import { WaveformDisplay } from "@/components/WaveformDisplay"
import { formatDuration } from "@/lib/utils"
import { cn } from "@/lib/utils"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface AudioPlayerProps {
  audioUrl: string | null
  title?: string
  subtitle?: string
  duration?: number | null
  loading?: boolean
  className?: string
  jobId?: string | null
  variant?: "card" | "bar"
  autoPlay?: boolean
  onRegenerate?: () => void
}

async function downloadAudio(url: string, filename: string) {
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
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}

export function AudioPlayer({
  audioUrl,
  title,
  subtitle,
  duration,
  loading,
  className,
  jobId,
  variant = "card",
  autoPlay = false,
  onRegenerate,
}: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [naturalDuration, setNaturalDuration] = useState(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const effectiveDuration = naturalDuration || duration || 0

  useEffect(() => {
    setIsPlaying(false)
    setCurrentTime(0)
    setNaturalDuration(0)
  }, [audioUrl])

  const togglePlay = () => {
    const el = audioRef.current
    if (!el || !audioUrl) return
    if (isPlaying) el.pause()
    else el.play()
  }

  const handleSeek = (time: number) => {
    const el = audioRef.current
    if (!el) return
    el.currentTime = time
    setCurrentTime(time)
  }

  const wavUrl = audioUrl
  const convertedUrl = (fmt: "mp3" | "ogg") =>
    jobId
      ? `${API_URL}/jobs/${jobId}/audio/${fmt}`
      : audioUrl
        ? `${API_URL}/convert/${fmt}/${audioUrl.split("/").pop()}`
        : ""
  const mp3Url = convertedUrl("mp3")
  const oggUrl = convertedUrl("ogg")

  const downloadMenu = wavUrl ? (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" title="Download">
          <Download className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => downloadAudio(wavUrl, `omnivoice-${jobId || "output"}.wav`)}>
          Download WAV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => downloadAudio(mp3Url, `omnivoice-${jobId || "output"}.mp3`)}>
          Download MP3
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => downloadAudio(oggUrl, `omnivoice-${jobId || "output"}.ogg`)}>
          Download OGG
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  ) : null

  const mediaEl = audioUrl ? (
    <audio
      ref={audioRef}
      src={audioUrl}
      autoPlay={autoPlay}
      onLoadedMetadata={() => {
        if (audioRef.current) setNaturalDuration(audioRef.current.duration)
      }}
      onTimeUpdate={() => {
        if (audioRef.current) setCurrentTime(audioRef.current.currentTime)
      }}
      onPlay={() => setIsPlaying(true)}
      onPause={() => setIsPlaying(false)}
      onEnded={() => setIsPlaying(false)}
      className="hidden"
    />
  ) : null

  // ── Bar variant — for the persistent bottom player ───────────────────────
  if (variant === "bar") {
    return (
      <div className={cn("flex items-center gap-4 w-full", className)}>
        <Button
          variant="default"
          size="icon"
          className="h-10 w-10 rounded-full shrink-0"
          onClick={togglePlay}
          disabled={!audioUrl || loading}
          title={isPlaying ? "Pause" : "Play"}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
        </Button>

        <div className="hidden min-w-0 w-44 shrink-0 sm:block">
          <p className="text-card-title truncate">{title || "Output"}</p>
          <p className="text-caption truncate">
            {loading ? "Generating…" : subtitle || "Ready"}
          </p>
        </div>

        <div className="flex-1 min-w-0">
          <WaveformDisplay
            audioUrl={audioUrl}
            isActive={isPlaying}
            currentTime={currentTime}
            duration={effectiveDuration}
            onSeek={handleSeek}
            className="h-10"
          />
        </div>

        <span className="hidden w-24 shrink-0 text-right text-caption tabular-nums md:inline">
          {formatDuration(currentTime)} / {formatDuration(effectiveDuration || duration)}
        </span>

        <div className="flex items-center gap-1 shrink-0">
          {onRegenerate && (
            <Button variant="ghost" size="icon" onClick={onRegenerate} title="Regenerate" disabled={loading}>
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
          {downloadMenu}
        </div>
        {mediaEl}
      </div>
    )
  }

  // ── Card variant — previews, drawer, etc. ────────────────────────────────
  if (loading) {
    return (
      <div className={cn("rounded-xl border bg-surface p-6 flex items-center justify-center", className)}>
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <Loader2 className="h-7 w-7 animate-spin" />
          <span className="text-sm">Generating audio…</span>
        </div>
      </div>
    )
  }

  if (!audioUrl) {
    return (
      <div className={cn("rounded-xl border border-dashed bg-surface p-6 flex items-center justify-center", className)}>
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <div className="h-9 w-9 rounded-full border-2 border-dashed border-muted-foreground/40 flex items-center justify-center">
            <Play className="h-4 w-4" />
          </div>
          <span className="text-sm">No audio yet</span>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("rounded-xl border bg-surface p-4 space-y-3", className)}>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-card-title truncate">{title || "Generated Audio"}</p>
          <p className="text-caption tabular-nums">
            {formatDuration(currentTime)} / {formatDuration(effectiveDuration || duration)}
          </p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button variant="ghost" size="icon" onClick={togglePlay} title={isPlaying ? "Pause" : "Play"}>
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </Button>
          {onRegenerate && (
            <Button variant="ghost" size="icon" onClick={onRegenerate} title="Regenerate">
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
          {downloadMenu}
        </div>
      </div>
      <WaveformDisplay
        audioUrl={audioUrl}
        isActive={isPlaying}
        currentTime={currentTime}
        duration={effectiveDuration || duration || 0}
        onSeek={handleSeek}
      />
      {mediaEl}
    </div>
  )
}
