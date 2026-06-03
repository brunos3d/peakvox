"use client"

import { useEffect, useRef } from "react"

interface WaveformDisplayProps {
  audioUrl: string | null
  isActive?: boolean
  currentTime?: number
  duration?: number
  onSeek?: (time: number) => void
  className?: string
}

// Pure renderer — kept at module scope so it's a stable reference for effects.
function drawWaveform(
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
  channelData: Float32Array,
  time: number,
  dur: number
) {
  const w = canvas.width
  const h = canvas.height
  const samples = w
  const blockSize = Math.max(1, Math.floor(channelData.length / samples))
  const progress = dur > 0 ? Math.min(1, time / dur) : 0
  const playedX = Math.floor(progress * w)

  // Canvas can't resolve `var(--x)`; read the computed CSS values first.
  const styles = getComputedStyle(canvas)
  const bg = `hsl(${styles.getPropertyValue("--background").trim() || "0 0% 100%"})`
  const primary = styles.getPropertyValue("--primary").trim() || "0 0% 0%"
  const playedColor = `hsl(${primary})`
  const unplayedColor = `hsl(${primary} / 0.35)`

  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, w, h)

  for (let i = 0; i < samples; i++) {
    let sum = 0
    for (let j = 0; j < blockSize; j++) {
      sum += Math.abs(channelData[i * blockSize + j] ?? 0)
    }
    const avg = sum / blockSize
    const barH = Math.max(2, avg * h * 2.5)
    ctx.fillStyle = i < playedX ? playedColor : unplayedColor
    ctx.fillRect(i, (h - barH) / 2, 1, barH)
  }

  // Playhead line
  if (playedX > 0 && playedX < w) {
    ctx.fillStyle = playedColor
    ctx.fillRect(playedX - 1, 0, 2, h)
  }
}

export function WaveformDisplay({
  audioUrl,
  isActive,
  currentTime = 0,
  duration = 0,
  onSeek,
  className,
}: WaveformDisplayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const waveDataRef = useRef<Float32Array | null>(null)

  // Fetch and decode audio into PCM data once per URL — no playback
  useEffect(() => {
    if (!audioUrl) return
    waveDataRef.current = null

    const canvas = canvasRef.current
    const ctx = canvas?.getContext("2d")
    if (canvas && ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
    }

    const controller = new AbortController()

    fetch(audioUrl, { signal: controller.signal })
      .then((r) => r.arrayBuffer())
      .then(async (buffer) => {
        const audioCtx = new AudioContext()
        try {
          const decoded = await audioCtx.decodeAudioData(buffer)
          waveDataRef.current = decoded.getChannelData(0)
          if (canvas && ctx) drawWaveform(canvas, ctx, waveDataRef.current, 0, 0)
        } finally {
          await audioCtx.close()
        }
      })
      .catch(() => {})

    return () => controller.abort()
  }, [audioUrl])

  // Redraw playhead whenever playback position changes
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !waveDataRef.current) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    drawWaveform(canvas, ctx, waveDataRef.current, currentTime, duration)
  }, [currentTime, duration])

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onSeek || !duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    onSeek(((e.clientX - rect.left) / rect.width) * duration)
  }

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={80}
      onClick={handleClick}
      className={`w-full h-20 rounded-md border ${isActive ? "border-primary" : "border-border"} ${onSeek && duration ? "cursor-pointer" : ""} ${className ?? ""}`}
    />
  )
}
