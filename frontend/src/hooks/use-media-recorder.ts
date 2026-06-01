"use client"

import { useState, useRef, useCallback } from "react"

interface UseMediaRecorderReturn {
  start: () => Promise<void>
  stop: () => void
  pause: () => void
  resume: () => void
  audioBlob: Blob | null
  audioUrl: string | null
  isRecording: boolean
  isPaused: boolean
  duration: number
  error: string | null
  clear: () => void
}

export function useMediaRecorder(): UseMediaRecorderReturn {
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number>(0)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now()
    timerRef.current = setInterval(() => {
      setDuration((Date.now() - startTimeRef.current) / 1000)
    }, 100)
  }, [])

  const start = useCallback(async () => {
    try {
      setError(null)
      setAudioBlob(null)
      setAudioUrl(null)
      setDuration(0)
      chunksRef.current = []

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm"

      const recorder = new MediaRecorder(stream, { mimeType })

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" })
        const url = URL.createObjectURL(blob)
        setAudioBlob(blob)
        setAudioUrl(url)
        setIsRecording(false)
        setIsPaused(false)
        clearTimer()
        stream.getTracks().forEach((t) => t.stop())
      }

      recorder.onerror = () => {
        setError("Recording error occurred")
        setIsRecording(false)
        clearTimer()
        stream.getTracks().forEach((t) => t.stop())
      }

      mediaRecorderRef.current = recorder
      recorder.start(100)
      setIsRecording(true)
      startTimer()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone access denied")
    }
  }, [clearTimer, startTimer])

  const stop = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop()
    }
  }, [])

  const pause = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.pause()
      setIsPaused(true)
      clearTimer()
    }
  }, [clearTimer])

  const resume = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
      mediaRecorderRef.current.resume()
      setIsPaused(false)
      startTimer()
    }
  }, [startTimer])

  const clear = useCallback(() => {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    setAudioBlob(null)
    setAudioUrl(null)
    setDuration(0)
    setError(null)
  }, [audioUrl])

  return { start, stop, pause, resume, audioBlob, audioUrl, isRecording, isPaused, duration, error, clear }
}
