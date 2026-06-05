"use client"

import { useState, useMemo } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { fetchProviderVoices, createVoiceFromPreset } from "@/lib/api"
import type { ProviderVoiceResponse } from "@/types"
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
import { Loader2, Plus, Play } from "lucide-react"
import { useRouter } from "next/navigation"

interface PresetVoicesTabProps {
  onScopeChange?: (scope: string) => void
}

export function PresetVoicesTab({ onScopeChange }: PresetVoicesTabProps) {
  const [provider, setProvider] = useState<string>("")
  const [language, setLanguage] = useState<string>("")
  const [gender, setGender] = useState<string>("")
  const [search, setSearch] = useState<string>("")

  const { data: voices, isLoading } = useQuery({
    queryKey: ["provider-voices", provider, language, gender, search],
    queryFn: () => fetchProviderVoices({ provider, language, gender, search }),
  })

  const providers = useMemo(() => {
    if (!voices) return []
    return [...new Set(voices.map((v) => v.provider_id))].sort()
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

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        <Select value={provider} onValueChange={setProvider}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Providers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Providers</SelectItem>
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
            <SelectItem value="">All Languages</SelectItem>
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
            <SelectItem value="">All Genders</SelectItem>
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
            <div key={voice.provider_voice_id}>
              <PresetVoiceCard voice={voice} onScopeChange={onScopeChange} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function PresetVoiceCard({ voice, onScopeChange }: { voice: ProviderVoiceResponse; onScopeChange?: (scope: string) => void }) {
  const queryClient = useQueryClient()
  const router = useRouter()
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)
  const [isAdding, setIsAdding] = useState(false)

  const addToLibrary = async (useNow: boolean) => {
    setIsAdding(true)
    try {
      const profile = await createVoiceFromPreset({
        provider: voice.provider_id,
        preset_name: voice.external_id,
        name: `${voice.name} (${voice.provider_id})`,
        model_id: `${voice.provider_id}-base`,
      })
      queryClient.invalidateQueries({ queryKey: ["voices-page"] })
      if (useNow) {
        setSelectedProfile(profile)
        router.push("/")
      } else if (onScopeChange) {
        onScopeChange("mine")
      }
    } finally {
      setIsAdding(false)
    }
  }

  return (
    <div className="border border-border rounded-lg p-4 hover:border-primary/50 transition-colors">
      <div className="font-semibold text-sm truncate">{voice.name}</div>
      <div className="text-xs text-muted-foreground mt-1 space-y-0.5">
        <div>{voice.provider_id} · {voice.language ?? "unknown"} · {voice.gender ?? "unknown"}</div>
        {voice.description && <div className="truncate">{voice.description}</div>}
      </div>
      <div className="flex gap-2 mt-3">
        <Button
          size="sm"
          variant="default"
          className="flex-1 gap-1"
          onClick={() => addToLibrary(true)}
          disabled={isAdding}
        >
          {isAdding ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
          Use Now
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1 gap-1"
          onClick={() => addToLibrary(false)}
          disabled={isAdding}
        >
          {isAdding ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
          Library
        </Button>
      </div>
    </div>
  )
}
