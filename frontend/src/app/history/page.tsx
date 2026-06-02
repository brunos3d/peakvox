"use client"

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { History as HistoryIcon } from "lucide-react"
import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { FilterBar } from "@/components/common/FilterBar"
import { Chip } from "@/components/common/Chip"
import { EmptyState } from "@/components/common/EmptyState"
import { HistoryItem } from "@/components/history/HistoryItem"
import { Skeleton } from "@/components/ui/skeleton"
import { fetchJobs, deleteJob } from "@/lib/api"
import { useAppStore } from "@/store/use-store"
import type { JobResponse, JobStatus } from "@/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const STATUS_FILTERS: { key: "all" | JobStatus; label: string }[] = [
  { key: "all", label: "All" },
  { key: "completed", label: "Completed" },
  { key: "failed", label: "Failed" },
]

export default function HistoryPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const voices = useAppStore((s) => s.voices)
  const currentAudio = useAppStore((s) => s.currentAudio)
  const setCurrentAudio = useAppStore((s) => s.setCurrentAudio)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)
  const setTtsText = useAppStore((s) => s.setTtsText)
  const updateGenerationSettings = useAppStore((s) => s.updateGenerationSettings)
  const outputFormat = useAppStore((s) => s.outputFormat)

  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<"all" | JobStatus>("all")

  const { data: jobs, isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => fetchJobs({ limit: 100 }),
    refetchInterval: 8000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteJob(id),
    onSuccess: (_d, id) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
      if (currentAudio?.jobId === id) setCurrentAudio(null)
    },
  })

  const voiceName = (id: string | null) => voices.find((v) => v.id === id)?.name

  const filtered = useMemo(() => {
    return (jobs ?? []).filter((j) => {
      const matchesStatus = statusFilter === "all" || j.status === statusFilter
      const matchesSearch = !search || j.text.toLowerCase().includes(search.toLowerCase())
      return matchesStatus && matchesSearch
    })
  }, [jobs, statusFilter, search])

  const handlePlay = (job: JobResponse) => {
    if (!job.audio_url) return
    setCurrentAudio({
      url: `${API_URL}${job.audio_url}`,
      duration: job.audio_duration ?? null,
      jobId: job.id,
      title: "History playback",
      subtitle: voiceName(job.voice_profile_id) ? `Voice: ${voiceName(job.voice_profile_id)}` : undefined,
    })
  }

  const handleRegenerate = (job: JobResponse) => {
    const voice = voices.find((v) => v.id === job.voice_profile_id)
    if (voice) setSelectedProfile(voice)
    const p = job.generation_params || {}
    updateGenerationSettings({
      num_step: (p.num_step as number) ?? undefined,
      guidance_scale: (p.guidance_scale as number) ?? undefined,
      speed: (p.speed as number | null) ?? null,
      duration: (p.duration as number | null) ?? null,
      t_shift: (p.t_shift as number) ?? undefined,
      denoise: (p.denoise as boolean) ?? undefined,
    })
    setTtsText(job.text)
    router.push("/")
  }

  const contextPanel = (
    <div className="flex flex-col gap-5 p-6">
      <div>
        <h2 className="text-section-title">Status</h2>
        <p className="text-caption mt-0.5">Filter your generation history.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((f) => (
          <Chip key={f.key} label={f.label} active={statusFilter === f.key} onClick={() => setStatusFilter(f.key)} />
        ))}
      </div>
      <p className="text-caption">{filtered.length} of {jobs?.length ?? 0} generations</p>
    </div>
  )

  return (
    <PageLayout contextPanel={contextPanel} contextTitle="Filters">
      <PageHeader title="History" description="Replay, download, regenerate or remove past generations." />

      <div className="mt-6 space-y-4">
        <FilterBar search={search} onSearchChange={setSearch} placeholder="Search generated text…">
          <div className="hidden xl:flex items-center gap-2">
            {STATUS_FILTERS.map((f) => (
              <Chip key={f.key} label={f.label} active={statusFilter === f.key} onClick={() => setStatusFilter(f.key)} />
            ))}
          </div>
        </FilterBar>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-[76px] w-full rounded-xl" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={HistoryIcon}
            title={(jobs?.length ?? 0) === 0 ? "No generations yet" : "No matching generations"}
            description={(jobs?.length ?? 0) === 0 ? "Your generated audio will appear here." : "Try adjusting your filters."}
          />
        ) : (
          <div className="space-y-3">
            {filtered.map((job) => (
              <HistoryItem
                key={job.id}
                job={job}
                voiceName={voiceName(job.voice_profile_id)}
                active={currentAudio?.jobId === job.id}
                outputFormat={outputFormat}
                onPlay={handlePlay}
                onRegenerate={handleRegenerate}
                onDelete={(j) => deleteMutation.mutate(j.id)}
              />
            ))}
          </div>
        )}
      </div>
    </PageLayout>
  )
}
