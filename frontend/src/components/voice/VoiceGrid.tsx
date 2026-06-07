"use client"

import { useRef, useState, useEffect, useCallback } from "react"
import { useVirtualizer } from "@tanstack/react-virtual"
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

const CARD_HEIGHT_ESTIMATE = 140
const ROW_GAP_PX = 16 // 1rem — must match the pb-4 on each row and the column gap
const OVERSCAN = 3

/**
 * Viewport-based column count using the same breakpoints as Tailwind's
 * `grid-cols-1 sm:grid-cols-2 xl:grid-cols-3` (640px / 1280px). This must
 * match the skeleton grid exactly, otherwise loaded cards and skeletons
 * render with different column counts.
 */
function useColumnCount(): number {
  const [columns, setColumns] = useState(3)

  useEffect(() => {
    if (typeof window === "undefined") return

    const xl = window.matchMedia("(min-width: 1280px)")
    const sm = window.matchMedia("(min-width: 640px)")

    const update = () => {
      if (xl.matches) setColumns(3)
      else if (sm.matches) setColumns(2)
      else setColumns(1)
    }

    update()
    xl.addEventListener("change", update)
    sm.addEventListener("change", update)
    return () => {
      xl.removeEventListener("change", update)
      sm.removeEventListener("change", update)
    }
  }, [])

  return columns
}

export function VoiceGrid({
  voices,
  loading,
  selectedId,
  onSelect,
  onOpenDetails,
  onEdit,
  onDelete,
  onToggleFavorite,
}: VoiceGridProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const columns = useColumnCount()

  const rowCount = Math.ceil(voices.length / columns)

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: useCallback(() => scrollRef.current, []),
    estimateSize: () => CARD_HEIGHT_ESTIMATE + ROW_GAP_PX,
    overscan: OVERSCAN,
  })

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[124px] w-full rounded-xl" />
        ))}
      </div>
    )
  }

  if (voices.length === 0) return null

  return (
    <div>
      <div
        ref={scrollRef}
        className="overflow-auto pr-4"
        style={{ maxHeight: "calc(100vh - 320px)" }}
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            position: "relative",
          }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const rowIndex = virtualRow.index
            const startIdx = rowIndex * columns
            const rowItems = voices.slice(startIdx, startIdx + columns)

            return (
              <div
                key={virtualRow.key}
                data-index={virtualRow.index}
                ref={virtualizer.measureElement}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {rowItems.map((voice) => (
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
                {/* Spacer: equal inter-row gap matching the column gap (gap-4 = 1rem) */}
                <div className="h-4" aria-hidden="true" />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
