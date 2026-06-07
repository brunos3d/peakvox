"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Library, SlidersHorizontal } from "lucide-react"
import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { FilterBar } from "@/components/common/FilterBar"
import { FilterChips } from "@/components/common/FilterChips"
import { PaginationControls } from "@/components/common/PaginationControls"
import { Chip } from "@/components/common/Chip"
import { SortDropdown } from "@/components/common/SortDropdown"
import { VariantDashboard } from "@/components/voice/VariantDashboard"
import { PresetVoicesTab } from "@/components/voice/PresetVoicesTab"
import { VoiceGrid } from "@/components/voice/VoiceGrid"
import { VoiceEditDialog } from "@/components/voice/VoiceEditDialog"
import { SelectedVoicePanel } from "@/components/voice/SelectedVoicePanel"
import { EmptyState } from "@/components/common/EmptyState"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { LanguageCombobox } from "@/components/common/LanguageCombobox"
import { useVoicesPage, useToggleFavorite } from "@/hooks/use-generation"
import { useAppStore, useActiveVoice } from "@/store/use-store"
import { useActiveModel, useRecommendedModelId } from "@/hooks/use-models"
import { deleteVoice } from "@/lib/api"
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
  const activeVoice = useActiveVoice()
  const discardTemporaryVoice = useAppStore((s) => s.discardTemporaryVoice)
  const queryClient = useQueryClient()

  const [scope, setScope] = useState<VoiceScope>("mine")
  const [viewMode, setViewMode] = useState<"library" | "variants">("library")
  const [search, setSearch] = useState("")
  const debouncedSearch = useDebouncedValue(search)
  const [filters, setFilters] = useState<VoiceQueryFilters>(EMPTY_FILTERS)
  const [showFilters, setShowFilters] = useState(false)
  const [creationSourceFilter, setCreationSourceFilter] = useState<CreationSource | null>(null)
  const [providerFilter, setProviderFilter] = useState<string | null>(null)
  const [compatibleWithModelFilter, setCompatibleWithModelFilter] = useState(false)
  const [sortBy, setSortBy] = useState<SortField>("last_used_at")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")
  const [recentlyUsed, setRecentlyUsed] = useState<string | undefined>(undefined)

  const [editVoice, setEditVoice] = useState<VoiceProfile | null>(null)
  const [editOpen, setEditOpen] = useState(false)

  const query = useVoicesPage(scope, debouncedSearch, filters, sortBy, sortDir, creationSourceFilter ?? undefined, recentlyUsed)
  const voices = useMemo(
    () => query.data?.pages.flatMap((p) => p.items) ?? [],
    [query.data],
  )

  const { activeModel } = useActiveModel()
  const recommendedModelId = useRecommendedModelId(activeVoice)
  const selectedModelId = useAppStore((s) => s.selectedModelId)
  const filteredVoices = useMemo(
    () => {
      let result = voices
      if (creationSourceFilter) {
        result = result.filter((v) => v.creation_source === creationSourceFilter)
      }
      if (providerFilter) {
        result = result.filter((v) => String(v.meta?.provider ?? "") === providerFilter)
      }
      if (compatibleWithModelFilter && activeModel) {
        result = result.filter((v) => v.compatible_models.includes(activeModel.id))
      }
      return result
    },
    [voices, creationSourceFilter, providerFilter, compatibleWithModelFilter, activeModel],
  )

  const creationSourceCounts = useMemo(() => {
    const counts: Record<string, number> = { all: voices.length }
    for (const v of voices) {
      counts[v.creation_source] = (counts[v.creation_source] ?? 0) + 1
    }
    return counts
  }, [voices])

  const providers = useMemo(() => {
    const set = new Set<string>()
    for (const v of voices) {
      const p = v.meta?.provider
      if (p != null) set.add(String(p))
    }
    return [...set].sort()
  }, [voices])

  const toggleFavorite = useToggleFavorite()
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteVoice(id),
    onSuccess: (_d, id) => {
      queryClient.invalidateQueries({ queryKey: ["voices-page"] })
      queryClient.invalidateQueries({ queryKey: ["voices"] })
      if (selectedProfile?.id === id) setSelectedProfile(null)
    },
  })

  const setFilter = (key: keyof VoiceQueryFilters, value: string | boolean | undefined) =>
    setFilters((f) => ({ ...f, [key]: value || undefined }))

  const activeFilterCount =
    Object.values(filters).filter((v) => v !== undefined && v !== false).length

  const openEdit = (voice: VoiceProfile) => {
    setEditVoice(voice)
    setEditOpen(true)
  }

  const contextPanel = (
    <SelectedVoicePanel
      voice={activeVoice}
      primaryModelId={selectedModelId}
      recommendedModelId={recommendedModelId}
      onUseInTts={(voice) => {
        setSelectedProfile(voice)
      }}
      onEdit={openEdit}
      onDelete={(voice) => deleteMutation.mutate(voice.id)}
      onDiscardTemporary={discardTemporaryVoice}
    />
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
            <PresetVoicesTab
              onScopeChange={(v) => setScope(v as VoiceScope)}
              onOpenLibraryVoice={(v) => {
                setScope("mine")
                setSelectedProfile(v)
              }}
            />
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
                {providers.length > 0 && (
                  <select
                    value={providerFilter ?? ""}
                    onChange={(e) => setProviderFilter(e.target.value || null)}
                    className="h-8 rounded-lg border border-border bg-surface px-2 text-xs text-muted-foreground"
                  >
                    <option value="">All providers</option>
                    {providers.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                )}
                {activeModel && (
                  <Chip
                    label={`Compatible with ${activeModel.name}`}
                    active={compatibleWithModelFilter}
                    onClick={() => setCompatibleWithModelFilter(!compatibleWithModelFilter)}
                  />
                )}
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
                  ...(providerFilter ? [{ key: "provider", label: `Provider: ${providerFilter}` }] : []),
                  ...(compatibleWithModelFilter && activeModel ? [{ key: "compatible", label: `Compatible: ${activeModel.name}` }] : []),
                  ...(filters.favorite ? [{ key: "favorite", label: "Favorites" }] : []),
                  ...(recentlyUsed ? [{ key: "recently_used", label: `Used: last ${recentlyUsed}` }] : []),
                  ...(filters.language_code ? [{ key: "language_code", label: `Language: ${filters.language_code}` }] : []),
                  ...(filters.gender ? [{ key: "gender", label: `Gender: ${filters.gender}` }] : []),
                  ...(filters.age_group ? [{ key: "age_group", label: `Age: ${filters.age_group}` }] : []),
                  ...(filters.accent ? [{ key: "accent", label: `Accent: ${filters.accent}` }] : []),
                ]}
                onRemove={(key) => {
                  if (key === "creation_source") setCreationSourceFilter(null)
                  else if (key === "provider") setProviderFilter(null)
                  else if (key === "compatible") setCompatibleWithModelFilter(false)
                  else if (key === "favorite") setFilter("favorite", false)
                  else if (key === "recently_used") setRecentlyUsed(undefined)
                  else if (key === "language_code") setFilter("language_code", undefined)
                  else if (key === "gender") setFilter("gender", undefined)
                  else if (key === "age_group") setFilter("age_group", undefined)
                  else if (key === "accent") setFilter("accent", undefined)
                }}
                onClearAll={() => {
                  setCreationSourceFilter(null)
                  setProviderFilter(null)
                  setCompatibleWithModelFilter(false)
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
                  title={
                    // First-run: the library is genuinely empty (no filters
                    // applied, no search, no scope change) — show a
                    // welcoming prompt instead of "no matches found".
                    voices.length === 0 &&
                    !debouncedSearch &&
                    !creationSourceFilter &&
                    activeFilterCount === 0 &&
                    scope === "mine"
                      ? "Your voice library is empty"
                      : compatibleWithModelFilter && activeModel
                        ? `No voices compatible with ${activeModel.name}`
                        : creationSourceFilter
                          ? `No ${creationSourceFilter.toLowerCase().replace("_", " ")} voices`
                          : scope === "recent"
                            ? "No recently used voices"
                            : "No matching voices"
                  }
                  description={
                    voices.length === 0 &&
                    !debouncedSearch &&
                    !creationSourceFilter &&
                    activeFilterCount === 0 &&
                    scope === "mine"
                      ? "Clone a voice from your own audio, or browse the preset library to get started."
                      : compatibleWithModelFilter && activeModel
                        ? "Try switching to a different model or clear the compatibility filter."
                        : creationSourceFilter
                          ? "Try switching filters or create a new voice."
                          : scope === "recent"
                            ? "Voices you generate with will appear here."
                            : "Try adjusting your search or filters, or create a new voice."
                  }
                  action={
                    voices.length === 0 &&
                    !debouncedSearch &&
                    !creationSourceFilter &&
                    activeFilterCount === 0 &&
                    scope === "mine" ? (
                      <div className="flex flex-wrap items-center justify-center gap-2">
                        <Button asChild className="gap-2">
                          <Link href="/clone"><Plus className="h-4 w-4" /> Clone a voice</Link>
                        </Button>
                        <Button asChild variant="outline" className="gap-2">
                          <Link href="/voices?tab=preset">Browse presets</Link>
                        </Button>
                      </div>
                    ) : (
                      <Button asChild className="gap-2"><Link href="/clone"><Plus className="h-4 w-4" /> Create voice</Link></Button>
                    )
                  }
                />
              ) : (
                <>
                  <VoiceGrid
                    voices={filteredVoices}
                    loading={query.isLoading}
                    selectedId={activeVoice?.id ?? null}
                    onSelect={setSelectedProfile}
                    onEdit={openEdit}
                    onDelete={(v) => deleteMutation.mutate(v.id)}
                    onToggleFavorite={(v) => toggleFavorite.mutate({ id: v.id, value: !v.is_favorite })}
                  />
                  <PaginationControls
                    hasNextPage={query.hasNextPage}
                    isFetchingNextPage={query.isFetchingNextPage}
                    onLoadMore={() => query.fetchNextPage()}
                  />
                </>
              )}
            </>
          )}
        </div>
      </PageLayout>

      <VoiceEditDialog voice={editVoice} open={editOpen} onOpenChange={setEditOpen} />
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
