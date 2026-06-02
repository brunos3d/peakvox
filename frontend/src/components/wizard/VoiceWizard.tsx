"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, ChevronLeft, ChevronRight, Mic, FileText, SlidersHorizontal, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { VoiceProfileAudioInput, type AudioInputResult } from "@/components/VoiceProfileAudioInput"
import { GenerationSettingsFields } from "@/components/GenerationSettingsFields"
import { createVoice } from "@/lib/api"
import { useAppStore, SYSTEM_DEFAULTS } from "@/store/use-store"
import { formatDuration, cn } from "@/lib/utils"
import type { VoiceGenerationDefaults } from "@/types"

const LANGUAGES = ["Auto", "English", "Portuguese", "Spanish", "French", "German", "Chinese", "Japanese"]

const STEPS = [
  { label: "Audio", icon: Mic },
  { label: "Details", icon: FileText },
  { label: "Defaults", icon: SlidersHorizontal },
  { label: "Review", icon: CheckCircle2 },
]

function Stepper({ step }: { step: number }) {
  return (
    <div className="flex items-center">
      {STEPS.map((s, i) => {
        const Icon = s.icon
        const done = i < step
        const active = i === step
        return (
          <div key={s.label} className="flex flex-1 items-center last:flex-none">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-full border text-sm transition-colors",
                  done && "border-primary bg-primary text-primary-foreground",
                  active && "border-primary bg-primary/15 text-primary",
                  !done && !active && "border-border bg-surface text-muted-foreground"
                )}
              >
                {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
              </div>
              <span className={cn("text-sm hidden sm:inline", active ? "text-foreground font-medium" : "text-muted-foreground")}>
                {s.label}
              </span>
            </div>
            {i < STEPS.length - 1 && <div className={cn("mx-3 h-px flex-1", done ? "bg-primary" : "bg-border")} />}
          </div>
        )
      })}
    </div>
  )
}

export function VoiceWizard() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)

  const [step, setStep] = useState(0)
  const [audio, setAudio] = useState<AudioInputResult | null>(null)
  const [name, setName] = useState("")
  const [language, setLanguage] = useState("Auto")
  const [transcript, setTranscript] = useState("")
  const [description, setDescription] = useState("")
  const [settings, setSettings] = useState<VoiceGenerationDefaults>(SYSTEM_DEFAULTS)

  const mutation = useMutation({
    mutationFn: (formData: FormData) => createVoice(formData),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["voices"] })
      setSelectedProfile(created)
      router.push("/voices")
    },
  })

  const canNext = step === 0 ? !!audio?.isValid : step === 1 ? !!name.trim() : true

  const handleCreate = () => {
    if (!audio?.isValid || !name.trim()) return
    const fd = new FormData()
    fd.append("name", name.trim())
    fd.append("description", description)
    fd.append("language", language === "Auto" ? "" : language)
    fd.append("transcript", transcript)
    fd.append("generation_defaults", JSON.stringify(settings))
    fd.append("file", audio.file)
    fd.append("crop_start", String(audio.cropStart))
    fd.append("crop_end", String(audio.cropEnd))
    mutation.mutate(fd)
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Stepper step={step} />

      <div className="mt-8 min-h-[280px]">
        {step === 0 && (
          <div className="space-y-3">
            <div>
              <h2 className="text-section-title">Add a voice sample</h2>
              <p className="text-caption mt-0.5">Upload or record audio. Clips longer than 15s open a crop editor.</p>
            </div>
            <VoiceProfileAudioInput onChange={setAudio} />
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-section-title">Voice details</h2>
              <p className="text-caption mt-0.5">Name your voice and add optional context.</p>
            </div>
            <div className="space-y-2">
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Narrator — warm" />
            </div>
            <div className="space-y-2">
              <Label>Language</Label>
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {LANGUAGES.map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Reference transcript <span className="font-normal text-muted-foreground">(optional)</span></Label>
              <Textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={2} placeholder="Transcript of the sample — improves cloning accuracy." />
            </div>
            <div className="space-y-2">
              <Label>Description <span className="font-normal text-muted-foreground">(optional)</span></Label>
              <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} placeholder="Notes about this voice." />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-section-title">Generation defaults</h2>
              <p className="text-caption mt-0.5">Optional — these become the preset loaded whenever this voice is selected.</p>
            </div>
            <GenerationSettingsFields value={settings} onChange={setSettings} />
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-section-title">Review</h2>
              <p className="text-caption mt-0.5">Confirm the details before creating your voice.</p>
            </div>
            <div className="rounded-xl border border-border bg-surface divide-y divide-border px-4">
              {[
                ["Name", name || "—"],
                ["Language", language],
                ["Sample", audio ? `${audio.file.name} · ${formatDuration(audio.cropEnd - audio.cropStart)}` : "—"],
                ["Transcript", transcript ? `${transcript.slice(0, 40)}${transcript.length > 40 ? "…" : ""}` : "—"],
                ["Steps / Guidance", `${settings.num_step} / ${settings.guidance_scale.toFixed(1)}`],
                ["GPU", settings.use_gpu ? "On" : "Off"],
              ].map(([k, v]) => (
                <div key={k} className="flex items-center justify-between py-2.5 text-sm">
                  <span className="text-muted-foreground">{k}</span>
                  <span className="text-foreground/90 text-right max-w-[60%] truncate">{v}</span>
                </div>
              ))}
            </div>
            {mutation.isError && (
              <p className="text-xs text-error">{(mutation.error as Error)?.message ?? "Failed to create voice"}</p>
            )}
          </div>
        )}
      </div>

      <div className="mt-8 flex items-center justify-between border-t border-border pt-5">
        <Button variant="ghost" className="gap-1.5" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
          <ChevronLeft className="h-4 w-4" /> Back
        </Button>
        {step < STEPS.length - 1 ? (
          <Button className="gap-1.5" onClick={() => setStep((s) => s + 1)} disabled={!canNext}>
            Next <ChevronRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button className="gap-2" onClick={handleCreate} disabled={mutation.isPending || !audio?.isValid || !name.trim()}>
            {mutation.isPending ? "Creating…" : <><Check className="h-4 w-4" /> Create voice</>}
          </Button>
        )}
      </div>
    </div>
  )
}
