"use client"

import { useEffect, useRef, useState } from "react"
import { Play, Pause, ZoomIn, ZoomOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"

const MAX_CLIP = 10
const MIN_CLIP = 3

interface AudioCropEditorProps {
  audioUrl: string
  totalDuration: number
  onCropChange: (start: number, end: number, isValid: boolean) => void
}

function fmt(s: number): string {
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(1).padStart(4, "0")
  return `${m}:${sec}`
}

export function AudioCropEditor({ audioUrl, totalDuration, onCropChange }: AudioCropEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<any>(null)
  const regionRef = useRef<any>(null)
  // Keep a stable ref to onCropChange so the WaveSurfer handler never goes stale
  const onCropChangeRef = useRef(onCropChange)
  onCropChangeRef.current = onCropChange

  const [isReady, setIsReady] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [cropStart, setCropStart] = useState(0)
  const [cropEnd, setCropEnd] = useState(Math.min(MAX_CLIP, totalDuration))
  const [zoom, setZoom] = useState(50)
  const [validationError, setValidationError] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    let destroyed = false
    let ws: any = null

    const init = async () => {
      const { default: WaveSurfer } = await import("wavesurfer.js")
      const { default: RegionsPlugin } = await import("wavesurfer.js/plugins/regions")

      if (destroyed || !containerRef.current) return

      const regionsPlugin = RegionsPlugin.create()

      ws = WaveSurfer.create({
        container: containerRef.current,
        waveColor: "rgba(148, 163, 184, 0.45)",
        progressColor: "rgba(99, 102, 241, 0.8)",
        cursorColor: "rgba(255, 255, 255, 0.75)",
        cursorWidth: 2,
        height: 80,
        normalize: true,
        plugins: [regionsPlugin],
      })
      wsRef.current = ws
      if (destroyed) { ws.destroy(); wsRef.current = null; return }

      ws.load(audioUrl)

      ws.on("ready", () => {
        if (destroyed) return
        setIsReady(true)

        const initialEnd = Math.min(MAX_CLIP, totalDuration)
        const region = regionsPlugin.addRegion({
          start: 0,
          end: initialEnd,
          color: "rgba(99, 102, 241, 0.18)",
          drag: true,
          resize: true,
          minLength: MIN_CLIP,
          maxLength: MAX_CLIP,
        })
        regionRef.current = region

        setCropStart(0)
        setCropEnd(initialEnd)
        setValidationError(null)
        onCropChangeRef.current(0, initialEnd, true)

        // Update display while dragging
        region.on("update", () => {
          setCropStart(region.start)
          setCropEnd(region.end)
        })

        // Validate after the drag/resize ends
        region.on("update-end", () => {
          const s = region.start
          const e = region.end
          const len = e - s
          let error: string | null = null
          let valid = true
          if (len > MAX_CLIP) {
            error = `Reference voice samples must be ${MAX_CLIP} seconds or shorter.`
            valid = false
          } else if (len < MIN_CLIP) {
            error = `Minimum duration is ${MIN_CLIP} seconds.`
            valid = false
          }
          setValidationError(error)
          onCropChangeRef.current(s, e, valid)
        })
      })

      ws.on("audioprocess", (t: number) => setCurrentTime(t))
      ws.on("play", () => setIsPlaying(true))
      ws.on("pause", () => setIsPlaying(false))
      ws.on("finish", () => setIsPlaying(false))
    }

    init()

    return () => {
      destroyed = true
      wsRef.current?.destroy()
      wsRef.current = null
      regionRef.current = null
      setIsReady(false)
      setIsPlaying(false)
    }
  }, [audioUrl, totalDuration]) // eslint-disable-line react-hooks/exhaustive-deps

  // Apply zoom changes after WaveSurfer is ready
  useEffect(() => {
    if (wsRef.current && isReady) {
      wsRef.current.zoom(zoom)
    }
  }, [zoom, isReady])

  const handlePlayPause = () => {
    if (!wsRef.current || !isReady) return
    if (isPlaying) {
      wsRef.current.pause()
    } else {
      regionRef.current ? regionRef.current.play() : wsRef.current.play()
    }
  }

  const clipLen = cropEnd - cropStart
  const lenColor =
    clipLen > MAX_CLIP ? "text-destructive" : clipLen < MIN_CLIP ? "text-amber-500" : "text-primary"

  return (
    <div className="space-y-2 rounded-lg border bg-card/50 p-3">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Drag the highlighted region — max {MAX_CLIP}s, min {MIN_CLIP}s</span>
        <span>Total: {fmt(totalDuration)}</span>
      </div>

      {/* WaveSurfer mounts here */}
      <div ref={containerRef} className="overflow-hidden rounded bg-muted/30" style={{ minHeight: 80 }} />

      {!isReady && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="h-3 w-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          Loading waveform…
        </div>
      )}

      {validationError && (
        <p className="text-xs font-medium text-destructive">{validationError}</p>
      )}

      {/* Controls row */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        {/* Play / time */}
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="h-7 w-7"
            onClick={handlePlayPause}
            disabled={!isReady}
          >
            {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
          </Button>
          <span className="w-12 text-xs tabular-nums text-muted-foreground">{fmt(currentTime)}</span>
        </div>

        {/* Selected range + duration */}
        <div className="flex items-center gap-2 text-xs">
          <span className="tabular-nums text-muted-foreground">
            {fmt(cropStart)} → {fmt(cropEnd)}
          </span>
          <span className={`font-semibold tabular-nums ${lenColor}`}>
            {clipLen.toFixed(1)}s
          </span>
        </div>

        {/* Zoom */}
        <div className="flex items-center gap-1.5">
          <ZoomOut className="h-3 w-3 text-muted-foreground" />
          <Slider
            min={10}
            max={300}
            step={10}
            value={[zoom]}
            onValueChange={([v]) => setZoom(v)}
            className="w-20"
          />
          <ZoomIn className="h-3 w-3 text-muted-foreground" />
        </div>
      </div>
    </div>
  )
}
