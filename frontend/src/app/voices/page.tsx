"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Library, Wand2, Pencil, Trash2, SlidersHorizontal } from "lucide-react"
import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { FilterBar } from "@/components/common/FilterBar"
import { FilterChips } from "@/components/common/FilterChips"
import { SortDropdown } from "@/components/common/SortDropdown"
import { Chip } from "@/components/common/Chip"
import { VariantDashboard } from "@/components/voice/VariantDashboard"
import { PresetVoicesTab } from "@/components/voice/PresetVoicesTab"
import { VoiceGrid } from "@/components/voice/VoiceGrid"
import { VoiceDetailPanel } from "@/components/voice/VoiceDetailPanel"
import { VoiceEditDialog } from "@/components/voice/VoiceEditDialog"
import { EmptyState } from "@/components/common/EmptyState"
import { AudioPlayer } from "@/components/AudioPlayer"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { LanguageCombobox } from "@/components/common/LanguageCombobox"
import { useVoicesPage, useToggleFavorite } from "@/hooks/use-generation"
import { useAppStore } from "@/store/use-store"
import { deleteVoice, getVoiceAudioUrl } from "@/lib/api"
import { formatDuration } from "@/lib/utils"
import type { VoiceProfile, VoiceScope, VoiceQueryFilters, CreationSource, SortField } from "@/types"

const GENDERS = ["male", "female"]
const AGE_GROUPS = ["child", "teen", "young", "adult", "elderly"]
const ACCENTS = [
  "american", "british", "australian", "canadian", "indian",
  "chinese", "korean", "japanese", "portuguese", "russian",
]

const TABS: { value: VoiceScope; label: string }[] = [
  { value: "mine", label: "My Voices" },
  { value: "preset", label: "Preset Voices" },
]

const EMPTY_FILTERS: VoiceQueryFilters = {}

/** Tiny debounce so search feels instant without a request per keystroke. */
function useDebouncedValue<T>(value: T, delay = 200): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

export default function VoiceLibraryPage() {
  const selectedProfile = useAppStore((s) => s.selectedProfile)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)
  const queryClient = useQueryClient()

  const [scope, setScope] = useState<VoiceScope>("mine")
  const [viewMode, setViewMode] = useState<"library" | "variants">("library")
  const [search, setSearch] = useState("")
  const debouncedSearch = useDebouncedValue(search)
  const [filters, setFilters] = useState<VoiceQueryFilters>(EMPTY_FILTERS)
  const [showFilters, setShowFilters] = useState(false)
  const [creationSourceFilter, setCreationSourceFilter] = useState<CreationSource | null>(null)
  const [sortBy, setSortBy] = useState<SortField>("last_used_at")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")
  const [recentlyUsed, setRecentlyUsed] = useState<string | undefined>(undefined)

  const [detailsVoice, setDetailsVoice] = useState<VoiceProfile | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [editVoice, setEditVoice] = useState<VoiceProfile | null>(null)
  const [editOpen, setEditOpen] = useState(false)

  const query = useVoicesPage(scope, debouncedSearch, filters, sortBy, sortDir, creationSourceFilter ?? undefined, recentlyUsed)
  const voices = useMemo(
    () => query.data?.pages.flatMap((p) => p.items) ?? [],
    [query.data],
  )

  const filteredVoices = useMemo(
    () =>
      creationSourceFilter
        ? voices.filter((v) => v.creation_source === creationSourceFilter)
        : voices,
    [voices, creationSourceFilter],
  )

  const creationSourceCounts = useMemo(() => {
    const counts: Record<string, number> = { all: voices.length }
    for (const v of voices) {
      counts[v.creation_source] = (counts[v.creation_source] ?? 0) + 1
    }
    return counts
  }, [voices])

  const toggleFavorite = useToggleFavorite()
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteVoice(id),
    onSuccess: (_d, id) => {
      queryClient.invalidateQueries({ queryKey: ["voices-page"] })
      queryClient.invalidateQueries({ queryKey: ["voices"] })
      if (selectedProfile?.id === id) setSelectedProfile(null)
      if (detailsVoice?.id === id) setDetailsOpen(false)
    },
  })

  const setFilter = (key: keyof VoiceQueryFilters, value: string | boolean | undefined) =>
    setFilters((f) => ({ ...f, [key]: value || undefined }))

  const activeFilterCount =
    Object.values(filters).filter((v) => v !== undefined && v !== false).length

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
          description="Browse, preview and manage your voices."
          actions={
            <Button asChild className="gap-2">
              <Link href="/clone"><Plus className="h-4 w-4" /> Create voice</Link>
            </Button>
          }
        />

        <div className="mt-6 space-y-4">
          <div className="flex items-center justify-between">
            <Tabs value={scope} onValueChange={(v) => setScope(v as VoiceScope)}>
              <TabsList>
                {TABS.map((t) => (
                  <TabsTrigger key={t.value} value={t.value}>{t.label}</TabsTrigger>
                ))}
              </TabsList>
            </Tabs>

            <div className="flex gap-0.5 bg-surface rounded-lg p-0.5 border border-border">
              <button
                onClick={() => setViewMode("library")}
                className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                  viewMode === "library"
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Library
              </button>
              <button
                onClick={() => setViewMode("variants")}
                className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                  viewMode === "variants"
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Variants
              </button>
            </div>
          </div>

          {viewMode === "variants" ? (
            <VariantDashboard
              onSelectVoice={(voiceId) => {
                const voice = voices.find((v) => v.id === voiceId)
                if (voice) setSelectedProfile(voice)
              }}
            />
          ) : scope === "preset" ? (
            <PresetVoicesTab onScopeChange={(v) => setScope(v as VoiceScope)} />
          ) : (
            <>
              <FilterBar search={search} onSearchChange={setSearch} placeholder="Search voices…">
                <Chip
                  label="All"
                  active={!creationSourceFilter && !filters.favorite}
                  onClick={() => setCreationSourceFilter(null)}
                />
                <Chip
                  label={`Cloned (${creationSourceCounts["SOURCE_ASSET"] ?? 0})`}
                  active={creationSourceFilter === "SOURCE_ASSET"}
                  onClick={() =>
                    setCreationSourceFilter(
                      creationSourceFilter === "SOURCE_ASSET" ? null : "SOURCE_ASSET",
                    )
                  }
                />
                <Chip
                  label={`Preset (${creationSourceCounts["PRESET_VOICE"] ?? 0})`}
                  active={creationSourceFilter === "PRESET_VOICE"}
                  onClick={() =>
                    setCreationSourceFilter(
                      creationSourceFilter === "PRESET_VOICE" ? null : "PRESET_VOICE",
                    )
                  }
                />
                <Chip
                  label="Favorites"
                  active={!!filters.favorite}
                  onClick={() => setFilter("favorite", !filters.favorite)}
                />
                <Chip
                  label="Last 7 days"
                  active={recentlyUsed === "7d"}
                  onClick={() => setRecentlyUsed(recentlyUsed === "7d" ? undefined : "7d")}
                />
                <Chip
                  label="Last 30 days"
                  active={recentlyUsed === "30d"}
                  onClick={() => setRecentlyUsed(recentlyUsed === "30d" ? undefined : "30d")}
                />
                <Chip
                  label="Last 90 days"
                  active={recentlyUsed === "90d"}
                  onClick={() => setRecentlyUsed(recentlyUsed === "90d" ? undefined : "90d")}
                />
                <SortDropdown
                  sortBy={sortBy}
                  sortDir={sortDir}
                  onSortByChange={setSortBy}
                  onSortDirChange={setSortDir}
                />
                <Button
                  variant={showFilters ? "secondary" : "outline"}
                  size="sm"
                  className="h-8 gap-1.5"
                  onClick={() => setShowFilters((v) => !v)}
                >
                  <SlidersHorizontal className="h-3.5 w-3.5" />
                  Filters{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
                </Button>
              </FilterBar>

              <FilterChips
                chips={[
                  ...(creationSourceFilter ? [{ key: "creation_source", label: `Source: ${creationSourceFilter}` }] : []),
                  ...(filters.favorite ? [{ key: "favorite", label: "Favorites" }] : []),
                  ...(recentlyUsed ? [{ key: "recently_used", label: `Used: last ${recentlyUsed}` }] : []),
                  ...(filters.language_code ? [{ key: "language_code", label: `Language: ${filters.language_code}` }] : []),
                  ...(filters.gender ? [{ key: "gender", label: `Gender: ${filters.gender}` }] : []),
                  ...(filters.age_group ? [{ key: "age_group", label: `Age: ${filters.age_group}` }] : []),
                  ...(filters.accent ? [{ key: "accent", label: `Accent: ${filters.accent}` }] : []),
                ]}
                onRemove={(key) => {
                  if (key === "creation_source") setCreationSourceFilter(null)
                  else if (key === "favorite") setFilter("favorite", false)
                  else if (key === "recently_used") setRecentlyUsed(undefined)
                  else if (key === "language_code") setFilter("language_code", undefined)
                  else if (key === "gender") setFilter("gender", undefined)
                  else if (key === "age_group") setFilter("age_group", undefined)
                  else if (key === "accent") setFilter("accent", undefined)
                }}
                onClearAll={() => {
                  setCreationSourceFilter(null)
                  setFilters(EMPTY_FILTERS)
                  setRecentlyUsed(undefined)
                }}
              />

              {showFilters && (
                <div className="grid grid-cols-1 gap-3 rounded-xl border border-border bg-surface p-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground">Language</label>
                    <LanguageCombobox
                      value={filters.language_code ?? null}
                      includeAuto={false}
                      onChange={(l) => setFilter("language_code", l?.id)}
                    />
                  </div>
                  <FilterSelect
                    label="Gender"
                    value={filters.gender ?? "all"}
                    options={GENDERS}
                    onChange={(v) => setFilter("gender", v)}
                  />
                  <FilterSelect
                    label="Age"
                    value={filters.age_group ?? "all"}
                    options={AGE_GROUPS}
                    onChange={(v) => setFilter("age_group", v)}
                  />
                  <FilterSelect
                    label="Accent"
                    value={filters.accent ?? "all"}
                    options={ACCENTS}
                    onChange={(v) => setFilter("accent", v)}
                  />
                  {activeFilterCount > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="justify-self-start text-muted-foreground"
                      onClick={() => setFilters(EMPTY_FILTERS)}
                    >
                      Clear filters
                    </Button>
                  )}
                </div>
              )}

              {!query.isLoading && filteredVoices.length === 0 ? (
                <EmptyState
                  icon={Library}
                  title={creationSourceFilter ? `No ${creationSourceFilter.toLowerCase().replace("_", " ")} voices` : scope === "recent" ? "No recently used voices" : "No matching voices"}
                  description={
                    creationSourceFilter
                      ? "Try switching filters or create a new voice."
                      : scope === "recent"
                        ? "Voices you generate with will appear here."
                        : "Try adjusting your search or filters, or create a new voice."
                  }
                  action={
                    <Button asChild className="gap-2"><Link href="/clone"><Plus className="h-4 w-4" /> Create voice</Link></Button>
                  }
                />
              ) : (
                <>
                  <VoiceGrid
                    voices={filteredVoices}
                    loading={query.isLoading}
                    selectedId={selectedProfile?.id}
                    onSelect={setSelectedProfile}
                    onOpenDetails={openDetails}
                    onEdit={openEdit}
                    onDelete={(v) => deleteMutation.mutate(v.id)}
                    onToggleFavorite={(v) => toggleFavorite.mutate({ id: v.id, value: !v.is_favorite })}
                  />
                  {query.hasNextPage && (
                    <div className="flex justify-center pt-2">
                      <Button
                        variant="outline"
                        onClick={() => query.fetchNextPage()}
                        disabled={query.isFetchingNextPage}
                      >
                        {query.isFetchingNextPage ? "Loading…" : "Load more"}
                      </Button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </PageLayout>

      <VoiceDetailPanel
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

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string | undefined) => void
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs text-muted-foreground">{label}</label>
      <Select value={value} onValueChange={(v) => onChange(v === "all" ? undefined : v)}>
        <SelectTrigger className="h-10"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Any</SelectItem>
          {options.map((o) => (
            <SelectItem key={o} value={o} className="capitalize">{o}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
