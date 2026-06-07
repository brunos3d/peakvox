"use client"

import { useState, useMemo, useEffect } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { fetchVoiceResources, importVoiceResource } from "@/lib/api"
import type { VoiceProfile, VoiceResourceResponse } from "@/types"
import { useAppStore } from "@/store/use-store"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Loader2, Plus, Play, Library } from "lucide-react"
import { useRouter } from "next/navigation"

interface PresetVoicesTabProps {
  onScopeChange?: (scope: string) => void
  onOpenLibraryVoice?: (voice: VoiceProfile) => void
}

export function PresetVoicesTab({ onScopeChange, onOpenLibraryVoice }: PresetVoicesTabProps) {
  const [provider, setProvider] = useState<string>("all")
  const [language, setLanguage] = useState<string>("all")
  const [gender, setGender] = useState<string>("all")
  const [search, setSearch] = useState<string>("")
  const [debouncedSearch, setDebouncedSearch] = useState<string>("")
  const [addError, setAddError] = useState<string | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(timer)
  }, [search])

  const { data: voices, isLoading, isError } = useQuery({
    queryKey: ["voice-resources", "preset", provider, language, gender, debouncedSearch],
    queryFn: () => fetchVoiceResources({
      resource_type: "preset",
      resource_origin: provider !== "all" ? provider : undefined,
      language: language !== "all" ? language : undefined,
      gender: gender !== "all" ? gender : undefined,
      search: debouncedSearch || undefined,
    }),
  })

  const providers = useMemo(() => {
    if (!voices) return []
    return [...new Set(voices.map((v) => v.provider_id).filter((p): p is string => !!p))].sort()
  }, [voices])

  const languages = useMemo(() => {
    if (!voices) return []
    return [...new Set(voices.map((v) => v.language).filter((l): l is string => !!l))].sort()
  }, [voices])

  const genders = useMemo(() => {
    if (!voices) return []
    return [...new Set(voices.map((v) => v.gender).filter((g): g is string => !!g))].sort()
  }, [voices])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="text-center py-16 text-destructive">
        Failed to load preset voices. Please try again.
      </div>
    )
  }

  return (
    <div>
      {addError && (
        <div className="mb-3 text-sm text-destructive">{addError}</div>
      )}
      <div className="flex gap-2 mb-4 flex-wrap">
        <Select value={provider} onValueChange={setProvider}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Providers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Providers</SelectItem>
            {providers.map((p) => (
              <SelectItem key={p} value={p}>{p}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={language} onValueChange={setLanguage}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Languages" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Languages</SelectItem>
            {languages.map((l) => (
              <SelectItem key={l} value={l}>{l}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={gender} onValueChange={setGender}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Genders" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Genders</SelectItem>
            {genders.map((g) => (
              <SelectItem key={g} value={g}>{g}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          placeholder="Search presets..."
          className="w-48"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {(!voices || voices.length === 0) ? (
        <div className="text-center py-16 text-muted-foreground">
          No preset voices found
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {voices.map((voice) => (
            <div key={voice.id}>
              <PresetVoiceCard
                voice={voice}
                onScopeChange={onScopeChange}
                onOpenLibraryVoice={onOpenLibraryVoice}
                onError={setAddError}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function PresetVoiceCard({
  voice,
  onScopeChange,
  onOpenLibraryVoice,
  onError,
}: {
  voice: VoiceResourceResponse
  onScopeChange?: (scope: string) => void
  onOpenLibraryVoice?: (voice: VoiceProfile) => void
  onError?: (msg: string | null) => void
}) {
  const queryClient = useQueryClient()
  const router = useRouter()
  const selectTemporaryVoice = useAppStore((s) => s.selectTemporaryVoice)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)
  const [isAdding, setIsAdding] = useState(false)

  const useInTts = () => {
    if (voice.is_in_library && voice.library_voice_id) {
      // Already imported — open the corresponding library voice in the library
      // context (switch to My Voices tab, select it, open its detail panel)
      // rather than navigating to TTS. This matches the button label
      // "Open Library Voice".
      const cached = queryClient.getQueryData<{ pages: { items: VoiceProfile[] }[] }>(
        ["voices-page", "mine", "", {}, "last_used_at", "desc", undefined, undefined],
      )
      const allVoices: VoiceProfile[] = cached?.pages.flatMap((p) => p.items) ?? []
      const existing =
        allVoices.find((v) => v.id === voice.library_voice_id) ??
        useAppStore.getState().voices.find((v) => v.id === voice.library_voice_id)

      if (existing && onOpenLibraryVoice) {
        onOpenLibraryVoice(existing)
        return
      }
    }
    // Not imported (or cache not yet hydrated) — send the user to TTS with a
    // temporary selection so they can try the voice before importing.
    selectTemporaryVoice(voice)
    router.push("/")
  }

  const importToLibrary = async () => {
    setIsAdding(true)
    onError?.(null)
    try {
      await importVoiceResource(voice.id)
      queryClient.invalidateQueries({ queryKey: ["voices-page"] })
      queryClient.invalidateQueries({ queryKey: ["voice-resources"] })
      onScopeChange?.("mine")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to add voice"
      onError?.(msg)
    } finally {
      setIsAdding(false)
    }
  }

  if (voice.is_in_library) {
    return (
      <div className="border border-border rounded-lg p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="font-semibold text-sm truncate">{voice.name}</div>
            <div className="text-xs text-muted-foreground mt-1 space-y-0.5">
              <div>{voice.provider_id ?? "unknown"} · {voice.language ?? "unknown"} · {voice.gender ?? "unknown"}</div>
              {voice.description && <div className="truncate">{voice.description}</div>}
            </div>
          </div>
          <span className="shrink-0 inline-flex items-center gap-1 rounded-md border border-success/30 bg-success/10 px-2 py-0.5 text-[10px] font-medium text-success">
            <Library className="h-3 w-3" />
            In Library
          </span>
        </div>
        <div className="flex gap-2 mt-3">
          <Button
            size="sm"
            variant="default"
            className="flex-1 gap-1"
            onClick={useInTts}
            disabled={isAdding}
          >
            <Play className="h-3 w-3" />
            Open Library Voice
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="border border-border rounded-lg p-4 hover:border-primary/50 transition-colors">
      <div className="font-semibold text-sm truncate">{voice.name}</div>
      <div className="text-xs text-muted-foreground mt-1 space-y-0.5">
        <div>{voice.provider_id ?? "unknown"} · {voice.language ?? "unknown"} · {voice.gender ?? "unknown"}</div>
        {voice.description && <div className="truncate">{voice.description}</div>}
      </div>
      <div className="flex gap-2 mt-3">
        <Button
          size="sm"
          variant="default"
          className="flex-1 gap-1"
          onClick={useInTts}
          disabled={isAdding}
        >
          <Play className="h-3 w-3" />
          Use in TTS
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1 gap-1"
          onClick={importToLibrary}
          disabled={isAdding}
        >
          {isAdding ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
          Import to Library
        </Button>
      </div>
    </div>
  )
}
