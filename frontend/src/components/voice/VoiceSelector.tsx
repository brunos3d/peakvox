"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { Mic, ChevronRight, Plus, Search, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { VoiceCard } from "@/components/voice/VoiceCard"
import { EmptyState } from "@/components/common/EmptyState"
import { useAppStore } from "@/store/use-store"
import { useActiveModel } from "@/hooks/use-models"

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
  const selected = useAppStore((s) => s.selectedProfile)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)
  const { activeModel } = useActiveModel()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")

  const { compatible, notCompatible } = useMemo(() => {
    if (!activeModel) {
      return { compatible: voices, notCompatible: [] as typeof voices }
    }
    const comp: typeof voices = []
    const not: typeof voices = []
    for (const v of voices) {
      if (v.compatible_models.includes(activeModel.id)) {
        comp.push(v)
      } else {
        not.push(v)
      }
    }
    return { compatible: comp, notCompatible: not }
  }, [voices, activeModel])

  const nameFilter = (v: typeof voices[0]) => v.name.toLowerCase().includes(query.toLowerCase())
  const filteredCompatible = compatible.filter(nameFilter)
  const filteredNotCompatible = notCompatible.filter(nameFilter)

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
              <p className="text-card-title truncate">{selected ? selected.name : "Select a voice"}</p>
              <p className="text-caption truncate">
                {selected
                  ? [selected.language, CREATION_SOURCE_LABELS[selected.creation_source] ?? selected.creation_source].filter(Boolean).join(" · ")
                  : activeModel
                    ? `${compatible.length} compatible · ${voices.length} total`
                    : `${voices.length} voice${voices.length !== 1 ? "s" : ""}`}
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
                Showing {filteredCompatible.length} compatible with{" "}
                <span className="font-medium text-foreground">{activeModel.name}</span>
                {filteredNotCompatible.length > 0 && (
                  <span> · {filteredNotCompatible.length} hidden</span>
                )}
              </p>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {filteredCompatible.length > 0 ? (
              filteredCompatible.map((voice) => (
                <VoiceCard
                  key={voice.id}
                  voice={voice}
                  selected={selected?.id === voice.id}
                  onSelect={(v) => {
                    setSelectedProfile(v)
                    setOpen(false)
                  }}
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
