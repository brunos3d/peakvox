"use client"

import { useState } from "react"
import { Wand2 } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { GenerationSettings } from "@/components/GenerationSettings"
import { useAppStore } from "@/store/use-store"
import { useSubmitGeneration } from "@/hooks/use-generation"

const LANGUAGES = ["Auto", "English", "Portuguese", "Spanish", "French", "German", "Chinese", "Japanese"]

const STYLE_EXAMPLES = [
  "male",
  "female",
  "british accent",
  "young adult",
  "high pitch, whisper",
  "low pitch, elderly",
]

export function GenerationForm() {
  const [text, setText] = useState("")
  const [language, setLanguage] = useState("Auto")
  const [instruct, setInstruct] = useState("")

  const selectedProfile = useAppStore((s) => s.selectedProfile)
  const generationSettings = useAppStore((s) => s.generationSettings)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)
  const activeJobId = useAppStore((s) => s.activeJobId)

  const generateMutation = useSubmitGeneration()

  const handleGenerate = () => {
    if (!text.trim()) return

    generateMutation.mutate({
      text: text.trim(),
      voice_profile_id: selectedProfile?.id ?? null,
      language: language === "Auto" ? null : language,
      ref_text: selectedProfile?.transcript || null,
      instruct: instruct || null,
      ...generationSettings,
    })
  }

  const clearAudio = () => {
    useAppStore.getState().resetAudio()
  }

  const hasAudioSource = !!selectedProfile
  const isGenerating = generateMutation.isPending || !!activeJobId

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Label>Text To Synthesize</Label>
        <Textarea
          placeholder="Enter the text you want to convert into speech..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="min-h-[120px] resize-y text-base leading-relaxed"
        />
      </div>

      <Separator />

      <div className="space-y-3">
        <Label>Reference Voice</Label>

        {selectedProfile && (
          <div className="flex items-center justify-between rounded-md border border-primary/30 bg-primary/5 p-3">
            <div className="flex items-center gap-2">
              <Wand2 className="h-4 w-4 text-primary" />
              <div>
                <p className="text-sm font-medium">{selectedProfile.name}</p>
                <p className="text-xs text-muted-foreground">
                  Profile voice
                  {selectedProfile.language && ` · ${selectedProfile.language}`}
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={clearAudio}>Change</Button>
          </div>
        )}

        {!selectedProfile && (
          <p className="text-sm text-muted-foreground">
            Select a voice profile from the Voice Library to get started.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label>Language (Optional)</Label>
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
        <Label>Style Prompt (Optional)</Label>
        <Textarea
          placeholder={STYLE_EXAMPLES[0]}
          value={instruct}
          onChange={(e) => setInstruct(e.target.value)}
          className="min-h-[60px] text-sm"
        />
        <div className="flex flex-wrap gap-1">
          {STYLE_EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground px-2 py-0.5 rounded-md bg-muted/50 hover:bg-muted transition-colors"
              onClick={() => setInstruct(example)}
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      <GenerationSettings />

      {generateMutation.isError && (
        <p className="text-xs text-destructive rounded-md bg-destructive/10 px-3 py-2">
          {(generateMutation.error as Error)?.message ?? "Generation failed. Please try again."}
        </p>
      )}

      <Button
        className="w-full gap-2 h-11 text-base"
        onClick={handleGenerate}
        disabled={!text.trim() || !hasAudioSource || isGenerating}
      >
        {isGenerating ? (
          <span className="animate-pulse">Generating...</span>
        ) : (
          <>
            <Wand2 className="h-5 w-5" />
            Generate Speech
          </>
        )}
      </Button>
    </div>
  )
}
