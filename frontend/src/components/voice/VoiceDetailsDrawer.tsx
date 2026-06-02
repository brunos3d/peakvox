"use client"

import { Pencil, Trash2, Wand2 } from "lucide-react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { AudioPlayer } from "@/components/AudioPlayer"
import { getVoiceAudioUrl } from "@/lib/api"
import { formatDuration } from "@/lib/utils"
import type { VoiceProfile } from "@/types"

interface VoiceDetailsDrawerProps {
  voice: VoiceProfile | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUse?: (voice: VoiceProfile) => void
  onEdit?: (voice: VoiceProfile) => void
  onDelete?: (voice: VoiceProfile) => void
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-foreground/90">{value}</span>
    </div>
  )
}

export function VoiceDetailsDrawer({ voice, open, onOpenChange, onUse, onEdit, onDelete }: VoiceDetailsDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md p-0">
        {voice && (
          <>
            <SheetHeader className="border-b border-border">
              <SheetTitle>{voice.name}</SheetTitle>
              <SheetDescription>
                {[voice.language, formatDuration(voice.audio_duration)].filter(Boolean).join(" · ")}
              </SheetDescription>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <AudioPlayer audioUrl={getVoiceAudioUrl(voice.id)} title="Reference audio" duration={voice.audio_duration} />

              {voice.description && (
                <div className="space-y-1">
                  <p className="text-caption uppercase tracking-wide">Description</p>
                  <p className="text-sm text-foreground/90">{voice.description}</p>
                </div>
              )}

              {voice.transcript && (
                <div className="space-y-1">
                  <p className="text-caption uppercase tracking-wide">Transcript</p>
                  <p className="text-sm text-foreground/90 leading-relaxed">{voice.transcript}</p>
                </div>
              )}

              <div className="space-y-1">
                <p className="text-caption uppercase tracking-wide">Metadata</p>
                <div className="rounded-lg border border-border bg-surface px-3 divide-y divide-border">
                  <MetaRow label="Created" value={new Date(voice.created_at).toLocaleString()} />
                  <MetaRow label="Last used" value={voice.last_used_at ? new Date(voice.last_used_at).toLocaleString() : "Never"} />
                  <MetaRow label="Duration" value={formatDuration(voice.audio_duration)} />
                </div>
              </div>

              {voice.generation_defaults && (
                <div className="space-y-1">
                  <p className="text-caption uppercase tracking-wide flex items-center gap-1.5">
                    Generation defaults <Badge className="bg-primary/15 px-1.5 py-0 text-[10px] text-primary">preset</Badge>
                  </p>
                  <div className="rounded-lg border border-border bg-surface px-3 divide-y divide-border">
                    <MetaRow label="Steps" value={String(voice.generation_defaults.num_step)} />
                    <MetaRow label="Guidance" value={voice.generation_defaults.guidance_scale.toFixed(1)} />
                    <MetaRow label="Speed" value={voice.generation_defaults.speed ? `${voice.generation_defaults.speed}x` : "Auto"} />
                    <MetaRow label="Time shift" value={voice.generation_defaults.t_shift.toFixed(2)} />
                    <MetaRow label="Denoise" value={voice.generation_defaults.denoise ? "On" : "Off"} />
                    <MetaRow label="GPU" value={voice.generation_defaults.use_gpu ? "On" : "Off"} />
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-border p-4 flex items-center gap-2">
              {onUse && (
                <Button className="flex-1 gap-2" onClick={() => onUse(voice)}>
                  <Wand2 className="h-4 w-4" /> Use voice
                </Button>
              )}
              {onEdit && (
                <Button variant="outline" size="icon" onClick={() => onEdit(voice)} title="Edit">
                  <Pencil className="h-4 w-4" />
                </Button>
              )}
              {onDelete && (
                <Button variant="outline" size="icon" className="text-error hover:text-error" onClick={() => onDelete(voice)} title="Delete">
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
