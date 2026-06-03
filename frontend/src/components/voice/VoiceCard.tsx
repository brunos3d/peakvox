"use client"

import { useRef, useState } from "react"
import { Play, Pause, Pencil, Trash2, Sparkles, Star, Copy, Check } from "lucide-react"
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
  onToggleFavorite?: (voice: VoiceProfile) => void
}

export function VoiceCard({
  voice,
  selected,
  onSelect,
  onOpenDetails,
  onEdit,
  onDelete,
  onToggleFavorite,
}: VoiceCardProps) {
  const [playing, setPlaying] = useState(false)
  const [copied, setCopied] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const togglePreview = (e: React.MouseEvent) => {
    e.stopPropagation()
    const el = audioRef.current
    if (!el) return
    if (playing) el.pause()
    else el.play()
  }

  const copyId = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard?.writeText(voice.public_voice_id).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  const initials = voice.name.slice(0, 2).toUpperCase()
  const chars = voice.characteristics
  const chips = [chars?.gender, chars?.accent].filter(Boolean) as string[]

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
            {chips.map((c) => (
              <Badge key={c} variant="secondary" className="px-1.5 py-0 text-[10px] capitalize">
                {c}
              </Badge>
            ))}
          </div>
        </div>
        {onToggleFavorite && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={(e) => {
              e.stopPropagation()
              onToggleFavorite(voice)
            }}
            title={voice.is_favorite ? "Unfavorite" : "Favorite"}
          >
            <Star
              className={cn(
                "h-4 w-4",
                voice.is_favorite ? "fill-warning text-warning" : "text-muted-foreground",
              )}
            />
          </Button>
        )}
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
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={copyId}
            title="Copy Voice ID"
            className="inline-flex items-center gap-1 rounded text-caption font-mono hover:text-foreground"
          >
            {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
            {voice.public_voice_id}
          </button>
          <span className="text-caption">· {voice.usage_count} uses</span>
        </div>
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
