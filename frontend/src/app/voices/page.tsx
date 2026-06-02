"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Library, Wand2, Pencil, Trash2 } from "lucide-react"
import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { FilterBar } from "@/components/common/FilterBar"
import { Chip } from "@/components/common/Chip"
import { VoiceGrid } from "@/components/voice/VoiceGrid"
import { VoiceDetailsDrawer } from "@/components/voice/VoiceDetailsDrawer"
import { VoiceEditDialog } from "@/components/voice/VoiceEditDialog"
import { EmptyState } from "@/components/common/EmptyState"
import { AudioPlayer } from "@/components/AudioPlayer"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useVoices } from "@/hooks/use-generation"
import { useAppStore } from "@/store/use-store"
import { deleteVoice, getVoiceAudioUrl } from "@/lib/api"
import { formatDuration } from "@/lib/utils"
import type { VoiceProfile } from "@/types"

export default function VoiceLibraryPage() {
  const { isLoading } = useVoices()
  const voices = useAppStore((s) => s.voices)
  const selectedProfile = useAppStore((s) => s.selectedProfile)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)
  const queryClient = useQueryClient()

  const [search, setSearch] = useState("")
  const [language, setLanguage] = useState("all")
  const [onlyPreset, setOnlyPreset] = useState(false)
  const [onlyRecent, setOnlyRecent] = useState(false)

  const [detailsVoice, setDetailsVoice] = useState<VoiceProfile | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [editVoice, setEditVoice] = useState<VoiceProfile | null>(null)
  const [editOpen, setEditOpen] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteVoice(id),
    onSuccess: (_d, id) => {
      queryClient.invalidateQueries({ queryKey: ["voices"] })
      if (selectedProfile?.id === id) setSelectedProfile(null)
      if (detailsVoice?.id === id) setDetailsOpen(false)
    },
  })

  const languages = useMemo(
    () => Array.from(new Set(voices.map((v) => v.language).filter(Boolean))) as string[],
    [voices]
  )

  const filtered = useMemo(() => {
    let list = voices.filter((v) => {
      const q = search.toLowerCase()
      const matchesSearch = !q || v.name.toLowerCase().includes(q) || (v.transcript || "").toLowerCase().includes(q)
      const matchesLang = language === "all" || v.language === language
      const matchesPreset = !onlyPreset || !!v.generation_defaults
      const matchesRecent = !onlyRecent || !!v.last_used_at
      return matchesSearch && matchesLang && matchesPreset && matchesRecent
    })
    if (onlyRecent) {
      list = [...list].sort(
        (a, b) => new Date(b.last_used_at || 0).getTime() - new Date(a.last_used_at || 0).getTime()
      )
    }
    return list
  }, [voices, search, language, onlyPreset, onlyRecent])

  const openDetails = (voice: VoiceProfile) => {
    setDetailsVoice(voice)
    setDetailsOpen(true)
  }
  const openEdit = (voice: VoiceProfile) => {
    setEditVoice(voice)
    setEditOpen(true)
  }

  const contextPanel = (
    <div className="flex flex-col gap-5 p-6">
      <div>
        <h2 className="text-section-title">Selected voice</h2>
        <p className="text-caption mt-0.5">Single-click a card to select, double-click for details.</p>
      </div>
      {selectedProfile ? (
        <div className="space-y-4">
          <div>
            <p className="text-card-title">{selectedProfile.name}</p>
            <p className="text-caption">
              {[selectedProfile.language, formatDuration(selectedProfile.audio_duration)].filter(Boolean).join(" · ")}
            </p>
          </div>
          <AudioPlayer audioUrl={getVoiceAudioUrl(selectedProfile.id)} title="Reference audio" duration={selectedProfile.audio_duration} />
          <div className="flex gap-2">
            <Button asChild className="flex-1 gap-2">
              <Link href="/"><Wand2 className="h-4 w-4" /> Use in TTS</Link>
            </Button>
            <Button variant="outline" size="icon" onClick={() => openEdit(selectedProfile)} title="Edit">
              <Pencil className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" className="text-error hover:text-error" onClick={() => deleteMutation.mutate(selectedProfile.id)} title="Delete">
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No voice selected.</p>
      )}
    </div>
  )

  return (
    <>
      <PageLayout contextPanel={contextPanel} contextTitle="Selected voice">
        <PageHeader
          title="Voice Library"
          description="Browse, preview and manage your cloned voices."
          actions={
            <Button asChild className="gap-2">
              <Link href="/clone"><Plus className="h-4 w-4" /> Create voice</Link>
            </Button>
          }
        />

        <div className="mt-6 space-y-4">
          <FilterBar search={search} onSearchChange={setSearch} placeholder="Search voices…">
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="h-8 w-[150px]"><SelectValue placeholder="Language" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All languages</SelectItem>
                {languages.map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
              </SelectContent>
            </Select>
            <Chip label="With preset" active={onlyPreset} onClick={() => setOnlyPreset((v) => !v)} />
            <Chip label="Recently used" active={onlyRecent} onClick={() => setOnlyRecent((v) => !v)} />
          </FilterBar>

          {!isLoading && filtered.length === 0 ? (
            <EmptyState
              icon={Library}
              title={voices.length === 0 ? "No voices yet" : "No matching voices"}
              description={voices.length === 0 ? "Create your first voice to get started." : "Try adjusting your filters."}
              action={
                voices.length === 0 ? (
                  <Button asChild className="gap-2"><Link href="/clone"><Plus className="h-4 w-4" /> Create voice</Link></Button>
                ) : undefined
              }
            />
          ) : (
            <VoiceGrid
              voices={filtered}
              loading={isLoading}
              selectedId={selectedProfile?.id}
              onSelect={setSelectedProfile}
              onOpenDetails={openDetails}
              onEdit={openEdit}
              onDelete={(v) => deleteMutation.mutate(v.id)}
            />
          )}
        </div>
      </PageLayout>

      <VoiceDetailsDrawer
        voice={detailsVoice}
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        onUse={(v) => { setSelectedProfile(v); setDetailsOpen(false) }}
        onEdit={(v) => { setDetailsOpen(false); openEdit(v) }}
        onDelete={(v) => deleteMutation.mutate(v.id)}
      />
      <VoiceEditDialog voice={editVoice} open={editOpen} onOpenChange={setEditOpen} />
    </>
  )
}
