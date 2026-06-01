"use client"

import { useState, useRef, useEffect } from "react"
import { Play, Pause, Square, Download, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu"
import { WaveformDisplay } from "@/components/WaveformDisplay"
import { formatDuration } from "@/lib/utils"
import { Card } from "@/components/ui/card"

interface AudioPlayerProps {
  audioUrl: string | null
  title?: string
  duration?: number | null
  loading?: boolean
  className?: string
  jobId?: string | null
}

export function AudioPlayer({ audioUrl, title, duration, loading, className, jobId }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    setIsPlaying(false)
    setCurrentTime(0)
  }, [audioUrl])

  const togglePlay = () => {
    const el = audioRef.current
    if (!el || !audioUrl) return
    if (isPlaying) {
      el.pause()
    } else {
      el.play()
    }
  }

  const handleStop = () => {
    const el = audioRef.current
    if (!el) return
    el.pause()
    el.currentTime = 0
    setIsPlaying(false)
  }

  const downloadAudio = async (url: string, filename: string) => {
    try {
      const res = await fetch(url)
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = objectUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(objectUrl)
    } catch {
      const a = document.createElement("a")
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
  }

  if (loading) {
    return (
      <Card className={`p-6 flex items-center justify-center ${className || ""}`}>
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="text-sm">Generating audio...</span>
        </div>
      </Card>
    )
  }

  if (!audioUrl) {
    return (
      <Card className={`p-6 flex items-center justify-center ${className || ""}`}>
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <div className="h-8 w-8 rounded-full border-2 border-dashed border-muted-foreground/40 flex items-center justify-center">
            <Play className="h-4 w-4" />
          </div>
          <span className="text-sm">No audio generated yet</span>
        </div>
      </Card>
    )
  }

  return (
    <Card className={`p-4 ${className || ""}`}>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-medium">{title || "Generated Audio"}</h4>
            {duration && (
              <p className="text-xs text-muted-foreground">
                {formatDuration(duration)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={togglePlay}>
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={handleStop}>
              <Square className="h-4 w-4" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Download className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => downloadAudio(audioUrl, `omnivoice-${jobId || "output"}.wav`)}>
                  Download WAV
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
                    let mp3Url: string
                    if (jobId) {
                      mp3Url = `${apiUrl}/jobs/${jobId}/audio/mp3`
                    } else {
                      const filename = audioUrl.split("/").pop()
                      mp3Url = `${apiUrl}/convert/mp3/${filename}`
                    }
                    downloadAudio(mp3Url, `omnivoice-${jobId || "output"}.mp3`)
                  }}
                >
                  Download MP3
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <WaveformDisplay audioUrl={audioUrl} isActive={isPlaying} />
        <audio
          ref={audioRef}
          src={audioUrl}
          onTimeUpdate={() => {
            if (audioRef.current) setCurrentTime(audioRef.current.currentTime)
          }}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
          className="hidden"
        />
      </div>
    </Card>
  )
}
