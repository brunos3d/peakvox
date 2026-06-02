"use client"

import { useRef, useState } from "react"
import { Play, Pause, Pencil, Trash2, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { getVoiceAudioUrl } from "@/lib/api"
import { formatDuration, cn } from "@/lib/utils"
import type { VoiceProfile } from "@/types"

interface VoiceCardProps {
  voice: VoiceProfile
  selected?: boolean
  onSelect?: (voice: VoiceProfile) => void
  onOpenDetails?: (voice: VoiceProfile) => void
  onEdit?: (voice: VoiceProfile) => void
  onDelete?: (voice: VoiceProfile) => void
}

export function VoiceCard({ voice, selected, onSelect, onOpenDetails, onEdit, onDelete }: VoiceCardProps) {
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const togglePreview = (e: React.MouseEvent) => {
    e.stopPropagation()
    const el = audioRef.current
    if (!el) return
    if (playing) el.pause()
    else el.play()
  }

  const initials = voice.name.slice(0, 2).toUpperCase()

  return (
    <div
      onClick={() => onSelect?.(voice)}
      onDoubleClick={() => onOpenDetails?.(voice)}
      className={cn(
        "group relative flex flex-col gap-3 rounded-xl border bg-surface p-4 cursor-pointer transition-all hover:bg-surface-2",
        selected ? "border-primary ring-1 ring-primary/30" : "border-border hover:border-border"
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary text-sm font-semibold">
          {initials}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-card-title truncate">{voice.name}</p>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {voice.language && (
              <Badge variant="outline" className="px-1.5 py-0 text-[10px]">{voice.language}</Badge>
            )}
            <span className="text-caption">{formatDuration(voice.audio_duration)}</span>
            {voice.generation_defaults && (
              <Badge className="gap-1 bg-primary/15 px-1.5 py-0 text-[10px] text-primary hover:bg-primary/20">
                <Sparkles className="h-2.5 w-2.5" /> preset
              </Badge>
            )}
          </div>
        </div>
        <Button
          variant="secondary"
          size="icon"
          className="h-8 w-8 shrink-0 rounded-full"
          onClick={togglePreview}
          title={playing ? "Pause preview" : "Preview"}
        >
          {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
        </Button>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-caption">
          {voice.last_used_at ? `Used ${new Date(voice.last_used_at).toLocaleDateString()}` : "Never used"}
        </span>
        <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          {onEdit && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={(e) => {
                e.stopPropagation()
                onEdit(voice)
              }}
              title="Edit"
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
          )}
          {onDelete && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-error hover:text-error"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(voice)
              }}
              title="Delete"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      <audio
        ref={audioRef}
        src={getVoiceAudioUrl(voice.id)}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        className="hidden"
      />
    </div>
  )
}
