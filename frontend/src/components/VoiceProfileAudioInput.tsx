"use client"

import { useState, useCallback, useRef } from "react"
import { Upload, Trash2, CheckCircle, AlertCircle, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { VoiceRecorder } from "@/components/VoiceRecorder"
import { AudioCropEditor } from "@/components/AudioCropEditor"

const MAX_DURATION = 10

export interface AudioInputResult {
  file: File
  cropStart: number
  cropEnd: number
  audioDuration: number
  isValid: boolean
}

interface VoiceProfileAudioInputProps {
  onChange: (result: AudioInputResult | null) => void
}

type Stage = "idle" | "loading" | "error" | "ready" | "crop"

interface AudioState {
  stage: Stage
  file?: File
  url?: string
  duration?: number
  error?: string
}

function detectDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const audio = new Audio()
    audio.preload = "metadata"
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(url)
      if (isFinite(audio.duration) && audio.duration > 0) {
        resolve(audio.duration)
      } else {
        URL.revokeObjectURL(url)
        reject(new Error("Could not determine duration"))
      }
    }
    audio.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error("Browser cannot read this audio format"))
    }
    audio.src = url
  })
}

function fmtDur(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return m > 0 ? `${m}m ${sec}s` : `${s.toFixed(1)}s`
}

export function VoiceProfileAudioInput({ onChange }: VoiceProfileAudioInputProps) {
  const [audioState, setAudioState] = useState<AudioState>({ stage: "idle" })
  // Stable refs so WaveSurfer callbacks always read the latest file/duration
  const fileRef = useRef<File | null>(null)
  const durationRef = useRef<number>(0)

  const transition = useCallback(
    (file: File, duration: number) => {
      fileRef.current = file
      durationRef.current = duration
      const url = URL.createObjectURL(file)

      if (duration <= MAX_DURATION) {
        setAudioState({ stage: "ready", file, url, duration })
        onChange({ file, cropStart: 0, cropEnd: duration, audioDuration: duration, isValid: true })
      } else {
        const cropEnd = Math.min(MAX_DURATION, duration)
        setAudioState({ stage: "crop", file, url, duration })
        onChange({ file, cropStart: 0, cropEnd, audioDuration: duration, isValid: true })
      }
    },
    [onChange],
  )

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = "" // allow re-selecting same file
    if (!file) return

    setAudioState({ stage: "loading" })
    try {
      const duration = await detectDuration(file)
      transition(file, duration)
    } catch {
      setAudioState({ stage: "error", error: "Could not read audio file. Try another format or record directly." })
      onChange(null)
    }
  }

  const handleRecordingComplete = useCallback(
    (blob: Blob, _url: string, duration: number) => {
      const file = new File([blob], "recording.webm", { type: blob.type || "audio/webm" })
      transition(file, duration)
    },
    [transition],
  )

  // Called by AudioCropEditor on every region update-end
  const handleCropChange = useCallback(
    (start: number, end: number, isValid: boolean) => {
      onChange({
        file: fileRef.current!,
        cropStart: start,
        cropEnd: end,
        audioDuration: durationRef.current,
        isValid,
      })
    },
    [onChange],
  )

  const handleClear = () => {
    if (audioState.url) URL.revokeObjectURL(audioState.url)
    fileRef.current = null
    durationRef.current = 0
    setAudioState({ stage: "idle" })
    onChange(null)
  }

  const { stage, file, url, duration, error } = audioState

  if (stage === "idle") {
    return (
      <div className="space-y-2">
        <Button variant="outline" size="sm" className="gap-1.5" asChild>
          <label>
            <Upload className="h-3 w-3" />
            Upload Audio
            <input
              type="file"
              accept="audio/*,video/mp4,video/webm,.m4a,.flac,.opus"
              hidden
              onChange={handleFileChange}
            />
          </label>
        </Button>
        <VoiceRecorder onRecordingComplete={handleRecordingComplete} />
      </div>
    )
  }

  if (stage === "loading") {
    return (
      <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
        <span className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        Analyzing audio…
      </div>
    )
  }

  if (stage === "error") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
        <Button variant="outline" size="sm" onClick={handleClear}>
          Try Again
        </Button>
      </div>
    )
  }

  if (stage === "ready" && file && url && duration !== undefined) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <CheckCircle className="h-4 w-4 shrink-0 text-green-500" />
            <span className="truncate text-sm max-w-[190px]">{file.name}</span>
            <Badge variant="secondary" className="shrink-0 gap-1 text-xs">
              <Clock className="h-3 w-3" />
              {fmtDur(duration)}
            </Badge>
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={handleClear}>
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
        <audio controls src={url} className="h-8 w-full" />
      </div>
    )
  }

  if (stage === "crop" && file && url && duration !== undefined) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="truncate text-sm max-w-[165px]">{file.name}</span>
            <Badge
              variant="outline"
              className="shrink-0 gap-1 text-xs text-amber-500 border-amber-500/40"
            >
              <Clock className="h-3 w-3" />
              {fmtDur(duration)} — trim required
            </Badge>
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={handleClear}>
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
        <AudioCropEditor
          audioUrl={url}
          totalDuration={duration}
          onCropChange={handleCropChange}
        />
      </div>
    )
  }

  return null
}
