"use client"

import { useState, useEffect } from "react"
import { Mic, Square, Play, Pause, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useMediaRecorder } from "@/hooks/use-media-recorder"
import { WaveformDisplay } from "@/components/WaveformDisplay"

interface VoiceRecorderProps {
  onRecordingComplete: (blob: Blob, url: string, duration: number) => void
}

export function VoiceRecorder({ onRecordingComplete }: VoiceRecorderProps) {
  const recorder = useMediaRecorder()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false)

  useEffect(() => {
    if (recorder.audioBlob && recorder.audioUrl) {
      setPreviewUrl(recorder.audioUrl)
      onRecordingComplete(recorder.audioBlob, recorder.audioUrl, recorder.duration)
    }
  }, [recorder.audioBlob, recorder.audioUrl, recorder.duration, onRecordingComplete])

  const handleClear = () => {
    recorder.clear()
    setPreviewUrl(null)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {!recorder.isRecording ? (
          <Button
            variant="outline"
            size="sm"
            onClick={recorder.start}
            className="gap-2"
          >
            <Mic className="h-4 w-4" />
            {previewUrl ? "Re-record" : "Record"}
          </Button>
        ) : (
          <Button
            variant="destructive"
            size="sm"
            onClick={recorder.stop}
            className="gap-2 animate-pulse"
          >
            <Square className="h-4 w-4" />
            Stop
          </Button>
        )}
        {recorder.isRecording && (
          <span className="text-sm text-destructive animate-pulse">
            Recording... {recorder.duration.toFixed(1)}s
          </span>
        )}
      </div>

      {recorder.error && (
        <p className="text-xs text-destructive">{recorder.error}</p>
      )}

      {previewUrl && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <audio
              src={previewUrl}
              controls
              className="h-8 w-full"
              onPlay={() => setIsPreviewPlaying(true)}
              onPause={() => setIsPreviewPlaying(false)}
            />
            <Button variant="ghost" size="icon" onClick={handleClear}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
          <WaveformDisplay audioUrl={previewUrl} isActive={isPreviewPlaying} />
        </div>
      )}
    </div>
  )
}
