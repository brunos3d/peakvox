"use client"

import { useEffect } from "react"
import { AudioPlayer } from "@/components/AudioPlayer"
import { useJobStatus, useSubmitGeneration } from "@/hooks/use-generation"
import { useAppStore } from "@/store/use-store"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

/**
 * Persistent bottom player. Mounted once in the app shell so it survives route
 * changes and keeps polling the active job. Owns the active-job → currentAudio
 * sync (with the job-id desync guard) and one-click regeneration.
 */
export function BottomPlayer() {
  const activeJobId = useAppStore((s) => s.activeJobId)
  const activeJobStatus = useAppStore((s) => s.activeJobStatus)
  const currentAudio = useAppStore((s) => s.currentAudio)
  const setCurrentAudio = useAppStore((s) => s.setCurrentAudio)
  const lastRequest = useAppStore((s) => s.lastRequest)
  const voices = useAppStore((s) => s.voices)

  const { data: jobData } = useJobStatus(activeJobId)
  const submit = useSubmitGeneration()

  const isGenerating = activeJobStatus === "pending" || activeJobStatus === "processing"

  // Clear stale audio the moment a new generation starts.
  useEffect(() => {
    if (isGenerating) setCurrentAudio(null)
  }, [isGenerating, setCurrentAudio])

  // Promote a completed job to the player — guarded against a Zustand/React
  // Query desync where status is briefly "completed" for job N-1.
  useEffect(() => {
    if (activeJobStatus === "completed" && jobData?.audio_url && jobData.id === activeJobId) {
      const voiceName = voices.find((v) => v.id === jobData.voice_profile_id)?.name
      setCurrentAudio({
        url: `${API_URL}${jobData.audio_url}`,
        duration: jobData.audio_duration ?? null,
        jobId: jobData.id,
        title: "Latest generation",
        subtitle: voiceName ? `Voice: ${voiceName}` : undefined,
      })
    }
  }, [activeJobStatus, jobData, activeJobId, voices, setCurrentAudio])

  if (!currentAudio && !isGenerating) return null

  return (
    <div className="border-t border-border bg-surface/80 backdrop-blur px-4 lg:px-6 py-3">
      <AudioPlayer
        variant="bar"
        audioUrl={currentAudio?.url ?? null}
        title={currentAudio?.title ?? "Generating"}
        subtitle={currentAudio?.subtitle}
        duration={currentAudio?.duration}
        jobId={currentAudio?.jobId}
        loading={isGenerating}
        onRegenerate={lastRequest && !isGenerating ? () => submit.mutate(lastRequest) : undefined}
      />
    </div>
  )
}
