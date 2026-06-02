"use client"

import { FileAudio } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAppStore } from "@/store/use-store"

export function OutputFormatSelector() {
  const outputFormat = useAppStore((s) => s.outputFormat)
  const setOutputFormat = useAppStore((s) => s.setOutputFormat)

  return (
    <div className="space-y-2">
      <p className="text-caption uppercase tracking-wide">Output format</p>
      <Select value={outputFormat} onValueChange={(v) => setOutputFormat(v as "wav" | "mp3")}>
        <SelectTrigger>
          <span className="flex items-center gap-2">
            <FileAudio className="h-4 w-4 text-primary" />
            <SelectValue />
          </span>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="wav">WAV (lossless)</SelectItem>
          <SelectItem value="mp3">MP3 (compressed)</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}
