"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { Mic, ChevronRight, Plus, Search, AlertCircle, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { VoiceCard } from "@/components/voice/VoiceCard"
import { EmptyState } from "@/components/common/EmptyState"
import { useAppStore, useActiveVoice } from "@/store/use-store"
import { useActiveModel, useModels } from "@/hooks/use-models"
import { isTemporaryVoice } from "@/types"
import type { VoiceProfile } from "@/types"

const CREATION_SOURCE_LABELS: Record<string, string> = {
  SOURCE_ASSET: "Cloned",
  PRESET_VOICE: "Preset",
  MARKETPLACE_VOICE: "Marketplace",
  TRAINED_VOICE: "Trained",
  IMPORTED_VOICE: "Imported",
  SYSTEM_VOICE: "System",
}

export function VoiceSelector() {
  const voices = useAppStore((s) => s.voices)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)
  const discardTemporaryVoice = useAppStore((s) => s.discardTemporaryVoice)
  const activeVoice = useActiveVoice()
  const { activeModel } = useActiveModel()
  const { data: allModels } = useModels()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")

  const nameFilter = (v: VoiceProfile) => v.name.toLowerCase().includes(query.toLowerCase())

  // Group by declarative compat with the active model. We intentionally use the
  // flat `compatible_models` list here — fetching the full three-state variant
  // map for every voice in the picker would be impractical. Three-state
  // compatibility is computed only for the *active* voice and surfaced in the
  // model auto-switch logic in `GenerationPanel`.
  const grouped = useMemo(() => {
    const compatible: VoiceProfile[] = []
    const incompatible: VoiceProfile[] = []
    for (const v of voices) {
      if (!nameFilter(v)) continue
      if (activeModel && !v.compatible_models.includes(activeModel.id)) {
        incompatible.push(v)
      } else {
        compatible.push(v)
      }
    }
    return { compatible, incompatible }
  }, [voices, activeModel, query])

  const flatFiltered = grouped.compatible
  const hiddenCount = activeModel ? grouped.incompatible.length : 0

  const handleSelectLibraryVoice = (voice: VoiceProfile) => {
    if (isTemporaryVoice(activeVoice)) {
      discardTemporaryVoice()
    }
    setSelectedProfile(voice)
    setOpen(false)
  }

  const handleClearVoice = () => {
    if (isTemporaryVoice(activeVoice)) {
      discardTemporaryVoice()
    } else {
      setSelectedProfile(null)
    }
    setOpen(false)
  }

  const primaryModelName = activeVoice?.primary_model_id
    ? allModels?.find((m) => m.id === activeVoice.primary_model_id)?.name ?? null
    : null
  const creationSourceLabel = activeVoice && !isTemporaryVoice(activeVoice)
    ? CREATION_SOURCE_LABELS[activeVoice.creation_source] ?? activeVoice.creation_source
    : "Preset"
  const subtitleParts = activeVoice
    ? [activeVoice.language, creationSourceLabel, primaryModelName].filter(Boolean)
    : []
  const subtitle = activeVoice
    ? subtitleParts.join(" · ")
    : activeModel
      ? `${grouped.compatible.length} compatible · ${voices.length} total`
      : `${voices.length} voice${voices.length !== 1 ? "s" : ""}`

  return (
    <div className="space-y-2">
      <p className="text-caption uppercase tracking-wide">Voice</p>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <button className="flex w-full items-center gap-3 rounded-xl border border-border bg-surface p-3 text-left transition-colors hover:bg-surface-2">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
              <Mic className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-card-title truncate">{activeVoice ? activeVoice.name : "Select a voice"}</p>
              <p className="text-caption truncate">
                {subtitle ?? (activeModel
                  ? `${grouped.compatible.length} compatible · ${voices.length} total`
                  : `${voices.length} voice${voices.length !== 1 ? "s" : ""}`)}
              </p>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          </button>
        </SheetTrigger>
        <SheetContent side="right" className="w-full sm:max-w-md p-0">
          <SheetHeader className="border-b border-border">
            <SheetTitle>Select a voice</SheetTitle>
          </SheetHeader>
          <div className="border-b border-border p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search voices…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            {activeModel && (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Showing {flatFiltered.length} compatible with{" "}
                <span className="font-medium text-foreground">{activeModel.name}</span>
                {hiddenCount > 0 && (
                  <span> · {hiddenCount} hidden</span>
                )}
              </p>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {activeVoice && (
              <button
                onClick={handleClearVoice}
                className="flex w-full items-center gap-3 rounded-xl border border-dashed border-border bg-transparent p-3 text-left transition-colors hover:bg-surface-2"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <X className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-card-title">No voice selected</p>
                  <p className="text-caption">Clear the current selection</p>
                </div>
              </button>
            )}
            {flatFiltered.length > 0 ? (
              flatFiltered.map((voice) => (
                <VoiceCard
                  key={voice.id}
                  voice={voice}
                  selected={activeVoice?.id === voice.id}
                  onSelect={handleSelectLibraryVoice}
                />
              ))
            ) : query ? (
              <EmptyState
                icon={Search}
                title="No matching voices"
                description="Try a different search term."
              />
            ) : activeModel ? (
              <EmptyState
                icon={AlertCircle}
                title="No compatible voices"
                description={`No voices are compatible with ${activeModel.name}. Try selecting a different model.`}
                action={
                  <Button asChild className="gap-2">
                    <Link href="/clone" onClick={() => setOpen(false)}>
                      <Plus className="h-4 w-4" /> Create voice
                    </Link>
                  </Button>
                }
              />
            ) : (
              <EmptyState
                icon={Mic}
                title="No voices found"
                description="Create a voice to get started."
                action={
                  <Button asChild className="gap-2">
                    <Link href="/clone" onClick={() => setOpen(false)}>
                      <Plus className="h-4 w-4" /> Create voice
                    </Link>
                  </Button>
                }
              />
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
