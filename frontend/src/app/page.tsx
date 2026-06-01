"use client"

import { useEffect, useState } from "react"
import { Volume2, Loader2 } from "lucide-react"
import { useVoices, useModelStatus, useJobStatus } from "@/hooks/use-generation"
import { GenerationForm } from "@/components/GenerationForm"
import { AudioPlayer } from "@/components/AudioPlayer"
import { StatusPanel } from "@/components/StatusPanel"
import { VoiceLibrary } from "@/components/VoiceLibrary"
import { Separator } from "@/components/ui/separator"
import { useAppStore } from "@/store/use-store"

function ModelLoadingScreen() {
  const { data: status } = useModelStatus()

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4 text-center max-w-md">
        <div className="relative">
          <Volume2 className="h-16 w-16 text-primary animate-pulse" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary-foreground" />
          </div>
        </div>
        <h1 className="text-2xl font-bold">OmniVoice Platform</h1>
        <p className="text-muted-foreground">
          Loading the voice model... This may take a few minutes on the first run.
        </p>
        {status?.error && (
          <p className="text-sm text-destructive bg-destructive/10 rounded-md p-3">
            Error: {status.error}
          </p>
        )}
        {status?.loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Downloading model weights...
          </div>
        )}
      </div>
    </div>
  )
}

export default function Home() {
  const { data: status, isLoading: statusLoading } = useModelStatus()
  useVoices()

  const activeJobId = useAppStore((s) => s.activeJobId)
  const activeJobStatus = useAppStore((s) => s.activeJobStatus)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [audioDuration, setAudioDuration] = useState<number | null>(null)

  const { data: jobData } = useJobStatus(activeJobId)

  useEffect(() => {
    if (activeJobStatus === "completed" && jobData?.audio_url) {
      setAudioUrl(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${jobData.audio_url}`)
      setAudioDuration(jobData.audio_duration ?? null)
    }
  }, [activeJobStatus, jobData])

  useEffect(() => {
    if (activeJobStatus === "pending" || activeJobStatus === "processing") {
      setAudioUrl(null)
      setAudioDuration(null)
    }
  }, [activeJobStatus])

  if (statusLoading) {
    return <ModelLoadingScreen />
  }

  const isModelReady = status?.loaded

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-3">
          <Volume2 className="h-5 w-5 text-primary" />
          <h1 className="font-semibold text-sm">OmniVoice Platform</h1>
          <div className="flex items-center gap-1.5 ml-auto">
            <div className={`h-2 w-2 rounded-full ${isModelReady ? "bg-green-500" : "bg-yellow-500 animate-pulse"}`} />
            <span className="text-xs text-muted-foreground">
              {isModelReady ? "Model Ready" : status?.loading ? "Loading..." : "Offline"}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {!isModelReady ? (
          <ModelLoadingScreen />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 space-y-6">
              <div className="rounded-xl border bg-card p-5">
                <GenerationForm />
              </div>
            </div>

            <div className="lg:col-span-2 space-y-4">
              <AudioPlayer
                audioUrl={audioUrl}
                title="Output Audio"
                duration={audioDuration}
                loading={activeJobStatus === "pending" || activeJobStatus === "processing"}
                jobId={activeJobId}
              />

              <StatusPanel />

              <Separator />

              <div className="rounded-xl border bg-card p-4">
                <VoiceLibrary />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}


