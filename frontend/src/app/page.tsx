"use client"

import { useState } from "react"
import { Wand2, Loader2, AlertCircle } from "lucide-react"
import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { GenerationPanel } from "@/components/generation/GenerationPanel"
import { QuickPrompts } from "@/components/generation/QuickPrompts"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAppStore } from "@/store/use-store"
import { useSubmitGeneration, useModelStatus } from "@/hooks/use-generation"

const LANGUAGES = ["Auto", "English", "Portuguese", "Spanish", "French", "German", "Chinese", "Japanese"]
const STYLE_EXAMPLES = ["male", "female", "british accent", "young adult", "high pitch, whisper", "low pitch, elderly"]

export default function TextToSpeechPage() {
  const text = useAppStore((s) => s.ttsText)
  const setText = useAppStore((s) => s.setTtsText)
  const selectedProfile = useAppStore((s) => s.selectedProfile)
  const generationSettings = useAppStore((s) => s.generationSettings)
  const activeJobId = useAppStore((s) => s.activeJobId)

  const [language, setLanguage] = useState("Auto")
  const [instruct, setInstruct] = useState("")

  const { data: model } = useModelStatus()
  const generate = useSubmitGeneration()

  const modelReady = !!model?.loaded
  const isGenerating = generate.isPending || !!activeJobId
  const canGenerate = !!text.trim() && !!selectedProfile && modelReady && !isGenerating

  const handleGenerate = () => {
    if (!canGenerate) return
    generate.mutate({
      text: text.trim(),
      voice_profile_id: selectedProfile?.id ?? null,
      language: language === "Auto" ? null : language,
      ref_text: selectedProfile?.transcript || null,
      instruct: instruct || null,
      ...generationSettings,
    })
  }

  const insertPrompt = (prompt: string) => {
    setText(text.trim() ? `${text.trim()}\n\n${prompt}` : prompt)
  }

  return (
    <PageLayout contextPanel={<GenerationPanel />} contextTitle="Settings">
      <div className="mx-auto flex h-full max-w-3xl flex-col">
        <PageHeader title="Text to Speech" description="Type or paste text and generate speech with your voices." />

        {!modelReady && (
          <div className="mt-5 flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
            <Loader2 className="h-4 w-4 animate-spin" />
            {model?.loading ? "Loading the voice model — this can take a few minutes on first run." : "Model is offline."}
          </div>
        )}

        <div className="mt-6 flex flex-1 flex-col">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type or paste text to generate speech..."
            className="min-h-[260px] flex-1 resize-none rounded-xl border-border bg-surface p-5 text-base leading-relaxed"
          />

          <div className="mt-4">
            <p className="text-caption mb-2">Quick prompts</p>
            <QuickPrompts onSelect={insertPrompt} />
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-xs">Language</Label>
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LANGUAGES.map((lang) => (
                    <SelectItem key={lang} value={lang}>{lang}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Style prompt (optional)</Label>
              <Textarea
                value={instruct}
                onChange={(e) => setInstruct(e.target.value)}
                placeholder={STYLE_EXAMPLES[0]}
                className="min-h-[38px] resize-none text-sm"
              />
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {STYLE_EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setInstruct(ex)}
                className="rounded-md bg-surface-2 px-2 py-0.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
              >
                {ex}
              </button>
            ))}
          </div>

          {generate.isError && (
            <p className="mt-4 flex items-center gap-2 rounded-lg bg-error/10 px-3 py-2 text-xs text-error">
              <AlertCircle className="h-4 w-4" />
              {(generate.error as Error)?.message ?? "Generation failed. Please try again."}
            </p>
          )}

          {!selectedProfile && (
            <p className="mt-4 text-sm text-muted-foreground">
              Select a voice in the Settings panel to get started.
            </p>
          )}

          <div className="mt-6 pb-2">
            <Button className="h-11 w-full gap-2 text-base" onClick={handleGenerate} disabled={!canGenerate}>
              {isGenerating ? (
                <span className="animate-pulse">Generating…</span>
              ) : (
                <>
                  <Wand2 className="h-5 w-5" /> Generate speech
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </PageLayout>
  )
}
