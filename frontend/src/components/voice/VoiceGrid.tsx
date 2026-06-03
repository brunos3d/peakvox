"use client"

import { VoiceCard } from "@/components/voice/VoiceCard"
import { Skeleton } from "@/components/ui/skeleton"
import type { VoiceProfile } from "@/types"

interface VoiceGridProps {
  voices: VoiceProfile[]
  loading?: boolean
  selectedId?: string | null
  onSelect?: (voice: VoiceProfile) => void
  onOpenDetails?: (voice: VoiceProfile) => void
  onEdit?: (voice: VoiceProfile) => void
  onDelete?: (voice: VoiceProfile) => void
  onToggleFavorite?: (voice: VoiceProfile) => void
}

export function VoiceGrid({ voices, loading, selectedId, onSelect, onOpenDetails, onEdit, onDelete, onToggleFavorite }: VoiceGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[124px] w-full rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {voices.map((voice) => (
        <VoiceCard
          key={voice.id}
          voice={voice}
          selected={selectedId === voice.id}
          onSelect={onSelect}
          onOpenDetails={onOpenDetails}
          onEdit={onEdit}
          onDelete={onDelete}
          onToggleFavorite={onToggleFavorite}
        />
      ))}
    </div>
  )
}
