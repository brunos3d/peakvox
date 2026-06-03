"use client"

import { useState } from "react"
import { Copy, Check } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { CodeTabs } from "@/components/api/CodeTabs"
import { ttsExamples } from "@/lib/api-examples"

interface UseInApiDialogProps {
  voiceId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** Shows a voice's public ID plus ready-to-run text-to-speech request examples. */
export function UseInApiDialog({ voiceId, open, onOpenChange }: UseInApiDialogProps) {
  const [copied, setCopied] = useState(false)

  const copyId = () => {
    navigator.clipboard?.writeText(voiceId).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Use this voice in the API</DialogTitle>
          <DialogDescription>
            Call the OmniVoice REST API with this voice. Replace the placeholder with an API
            key from the API → API Keys page.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <p className="text-caption uppercase tracking-wide">Voice ID</p>
            <button
              type="button"
              onClick={copyId}
              className="flex w-full items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm font-mono hover:bg-surface-2"
            >
              <span className="truncate">{voiceId}</span>
              {copied ? <Check className="h-4 w-4 shrink-0 text-success" /> : <Copy className="h-4 w-4 shrink-0 text-muted-foreground" />}
            </button>
          </div>

          <CodeTabs examples={ttsExamples(voiceId)} />
        </div>
      </DialogContent>
    </Dialog>
  )
}
