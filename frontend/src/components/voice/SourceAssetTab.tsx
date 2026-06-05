"use client"

import { FileAudio, Clock, HardDrive, FileType } from "lucide-react"
import type { VoiceProfile } from "@/types"
import { formatFileSize } from "@/lib/utils"

interface SourceAssetTabProps {
  voice: VoiceProfile
}

function MetaRow({ icon: Icon, label, value }: { icon: typeof FileAudio; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 py-2 text-sm">
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="text-muted-foreground min-w-[80px]">{label}</span>
      <span className="ml-auto text-foreground/90 truncate">{value}</span>
    </div>
  )
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function SourceAssetTab({ voice }: SourceAssetTabProps) {
  const asset = voice.source_asset

  if (!asset) {
    return (
      <div className="rounded-lg border border-border bg-surface p-6 text-center">
        <FileAudio className="mx-auto h-8 w-8 text-muted-foreground mb-3" />
        <p className="text-sm text-muted-foreground">
          {voice.creation_source === "PRESET_VOICE"
            ? "This is a preset voice — no source audio file."
            : "No source asset recorded for this voice."}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-caption uppercase tracking-wide">Source material</p>
      <div className="rounded-lg border border-border bg-surface px-4 divide-y divide-border">
        <MetaRow icon={FileAudio} label="Filename" value={asset.original_filename ?? "—"} />
        <MetaRow icon={FileType} label="Type" value={asset.content_type ?? "—"} />
        <MetaRow icon={HardDrive} label="Size" value={asset.file_size != null ? formatFileSize(asset.file_size) : "—"} />
        <MetaRow icon={Clock} label="Duration" value={asset.audio_duration != null ? formatDuration(asset.audio_duration) : "—"} />
        <MetaRow icon={Clock} label="Uploaded" value={new Date(asset.created_at).toLocaleString()} />
      </div>
    </div>
  )
}
