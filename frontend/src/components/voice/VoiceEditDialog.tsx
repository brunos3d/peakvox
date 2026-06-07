"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { VoiceProfileAudioInput, type AudioInputResult } from "@/components/VoiceProfileAudioInput"
import { GenerationSettingsFields } from "@/components/GenerationSettingsFields"
import { VoiceDesignBuilder } from "@/components/generation/VoiceDesignBuilder"
import { LanguageCombobox } from "@/components/common/LanguageCombobox"
import { getLanguageById, getLanguageByName } from "@/lib/languages"
import { updateVoice as updateVoiceApi } from "@/lib/api"
import { useAppStore, SYSTEM_DEFAULTS } from "@/store/use-store"
import type { VoiceProfile, VoiceGenerationDefaults } from "@/types"

interface VoiceEditDialogProps {
  voice: VoiceProfile | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

const SOURCE_AUDIO_CREATIONS = new Set(["SOURCE_ASSET", "TRAINED_VOICE"])
const REFERENCE_AUDIO_CREATIONS = new Set(["SOURCE_ASSET", "TRAINED_VOICE", "MARKETPLACE_VOICE", "IMPORTED_VOICE"])

function hasSourceAudio(voice: VoiceProfile): boolean {
  return SOURCE_AUDIO_CREATIONS.has(voice.creation_source)
}

function hasReferenceAudio(voice: VoiceProfile): boolean {
  return REFERENCE_AUDIO_CREATIONS.has(voice.creation_source)
}

export function VoiceEditDialog({ voice, open, onOpenChange }: VoiceEditDialogProps) {
  const queryClient = useQueryClient()
  const selectedProfile = useAppStore((s) => s.selectedProfile)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)

  const [name, setName] = useState("")
  const [transcript, setTranscript] = useState("")
  const [languageId, setLanguageId] = useState<string | null>(null)
  const [settings, setSettings] = useState<VoiceGenerationDefaults>(SYSTEM_DEFAULTS)
  const [audio, setAudio] = useState<AudioInputResult | null>(null)

  const [prevVoice, setPrevVoice] = useState<VoiceProfile | null>(voice)
  if (voice !== prevVoice) {
    setPrevVoice(voice)
    if (voice) {
      setName(voice.name)
      setTranscript(voice.transcript || "")
      const resolved =
        getLanguageById(voice.language_code) ?? getLanguageByName(voice.language)
      setLanguageId(resolved?.id ?? null)
      setSettings(voice.generation_defaults ?? SYSTEM_DEFAULTS)
      setAudio(null)
    }
  }

  const mutation = useMutation({
    mutationFn: ({ id, formData }: { id: string; formData: FormData }) => updateVoiceApi(id, formData),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["voices"] })
      if (selectedProfile?.id === updated.id) setSelectedProfile(updated)
      onOpenChange(false)
    },
  })

  const canReplaceAudio = voice ? hasSourceAudio(voice) : true
  const canEditTranscript = voice ? hasReferenceAudio(voice) : true
  const isValid = !!name && (audio === null || audio.isValid)

  const handleSave = () => {
    if (!voice || !isValid) return
    const lang = getLanguageById(languageId)
    const fd = new FormData()
    fd.append("name", name)
    fd.append("transcript", canEditTranscript ? transcript : "")
    fd.append("language", lang?.name ?? "")
    fd.append("language_code", lang?.id ?? "")
    fd.append("generation_defaults", JSON.stringify(settings))
    if (audio && canReplaceAudio) {
      fd.append("file", audio.file)
      fd.append("crop_start", String(audio.cropStart))
      fd.append("crop_end", String(audio.cropEnd))
    }
    mutation.mutate({ id: voice.id, formData: fd })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit voice</DialogTitle>
          <DialogDescription>
            {canReplaceAudio
              ? "Update details, defaults, or replace the audio sample."
              : "Update name, language, or generation defaults."}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Voice name" />
          </div>

          {canEditTranscript && (
            <div className="space-y-2">
              <Label>Reference transcript <span className="font-normal text-muted-foreground">(optional)</span></Label>
              <Textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={2} placeholder="Transcript of the reference audio — improves cloning accuracy." />
            </div>
          )}

          <div className="space-y-2">
            <Label>Language</Label>
            <LanguageCombobox value={languageId} onChange={(l) => setLanguageId(l?.id ?? null)} />
          </div>

          <Accordion type="single" collapsible className="w-full rounded-lg border px-3">
            <AccordionItem value="gen" className="border-none">
              <AccordionTrigger className="py-3 text-sm">Generation defaults</AccordionTrigger>
              <AccordionContent>
                <div className="space-y-4 pb-2">
                  <div className="space-y-2">
                    <Label className="text-xs">Voice design <span className="font-normal text-muted-foreground">(optional)</span></Label>
                    <VoiceDesignBuilder
                      value={settings.voice_design ?? []}
                      onChange={(voice_design) => setSettings((s) => ({ ...s, voice_design }))}
                    />
                  </div>
                  <GenerationSettingsFields value={settings} onChange={setSettings} />
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          {canReplaceAudio && (
            <div className="space-y-2">
              <Label>Replace audio <span className="font-normal text-muted-foreground">(optional)</span></Label>
              <VoiceProfileAudioInput onChange={setAudio} />
            </div>
          )}

          {mutation.isError && (
            <p className="text-xs text-error">{(mutation.error as Error)?.message ?? "Failed to save changes"}</p>
          )}

          <Button className="w-full" onClick={handleSave} disabled={!isValid || mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
