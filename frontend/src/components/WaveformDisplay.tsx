"use client"

import { useEffect, useRef } from "react"

interface WaveformDisplayProps {
  audioUrl: string | null
  isActive?: boolean
  className?: string
}

export function WaveformDisplay({ audioUrl, isActive, className }: WaveformDisplayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>(0)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)

  useEffect(() => {
    if (!audioUrl || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let audio: HTMLAudioElement | null = new Audio(audioUrl)
    audio.crossOrigin = "anonymous"

    const audioContext = new AudioContext()
    audioContextRef.current = audioContext

    audio.addEventListener("canplay", () => {
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      sourceRef.current = audioContext.createMediaElementSource(audio!)
      sourceRef.current.connect(analyser)
      analyser.connect(audioContext.destination)

      analyserRef.current = analyser
      audio?.play()
    })

    function draw() {
      if (!canvas || !ctx) return
      const w = canvas.width
      const h = canvas.height

      ctx.fillStyle = "hsl(var(--background))"
      ctx.fillRect(0, 0, w, h)

      if (analyserRef.current) {
        const bufferLength = analyserRef.current.frequencyBinCount
        const dataArray = new Uint8Array(bufferLength)
        analyserRef.current.getByteTimeDomainData(dataArray)

        ctx.lineWidth = 2
        ctx.strokeStyle = "hsl(var(--primary))"
        ctx.beginPath()

        const sliceWidth = w / bufferLength
        let x = 0

        for (let i = 0; i < bufferLength; i++) {
          const v = dataArray[i] / 128.0
          const y = (v * h) / 2
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
          x += sliceWidth
        }

        ctx.stroke()
      }

      animationRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      cancelAnimationFrame(animationRef.current)
      audio?.pause()
      audio = null
      audioContext.close()
    }
  }, [audioUrl])

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={80}
      className={`w-full h-20 rounded-md border ${isActive ? "border-primary" : "border-border"} ${className || ""}`}
    />
  )
}
