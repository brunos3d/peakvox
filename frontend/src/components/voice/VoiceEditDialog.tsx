"use client"

import { useEffect, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { VoiceProfileAudioInput, type AudioInputResult } from "@/components/VoiceProfileAudioInput"
import { GenerationSettingsFields } from "@/components/GenerationSettingsFields"
import { updateVoice as updateVoiceApi } from "@/lib/api"
import { useAppStore, SYSTEM_DEFAULTS } from "@/store/use-store"
import type { VoiceProfile, VoiceGenerationDefaults } from "@/types"

const LANGUAGES = ["Auto", "English", "Portuguese", "Spanish", "French", "German", "Chinese", "Japanese"]

interface VoiceEditDialogProps {
  voice: VoiceProfile | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function VoiceEditDialog({ voice, open, onOpenChange }: VoiceEditDialogProps) {
  const queryClient = useQueryClient()
  const selectedProfile = useAppStore((s) => s.selectedProfile)
  const setSelectedProfile = useAppStore((s) => s.setSelectedProfile)

  const [name, setName] = useState("")
  const [transcript, setTranscript] = useState("")
  const [language, setLanguage] = useState("Auto")
  const [settings, setSettings] = useState<VoiceGenerationDefaults>(SYSTEM_DEFAULTS)
  const [audio, setAudio] = useState<AudioInputResult | null>(null)

  useEffect(() => {
    if (voice) {
      setName(voice.name)
      setTranscript(voice.transcript || "")
      setLanguage(voice.language || "Auto")
      setSettings(voice.generation_defaults ?? SYSTEM_DEFAULTS)
      setAudio(null)
    }
  }, [voice])

  const mutation = useMutation({
    mutationFn: ({ id, formData }: { id: string; formData: FormData }) => updateVoiceApi(id, formData),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["voices"] })
      if (selectedProfile?.id === updated.id) setSelectedProfile(updated)
      onOpenChange(false)
    },
  })

  const isValid = !!name && (audio === null || audio.isValid)

  const handleSave = () => {
    if (!voice || !isValid) return
    const fd = new FormData()
    fd.append("name", name)
    fd.append("transcript", transcript)
    fd.append("language", language === "Auto" ? "" : language)
    fd.append("generation_defaults", JSON.stringify(settings))
    if (audio) {
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
          <DialogDescription>Update details, defaults, or replace the audio sample.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Voice name" />
          </div>
          <div className="space-y-2">
            <Label>Reference transcript <span className="font-normal text-muted-foreground">(optional)</span></Label>
            <Textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={2} placeholder="Transcript of the reference audio — improves cloning accuracy." />
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

          <Accordion type="single" collapsible className="w-full rounded-lg border px-3">
            <AccordionItem value="gen" className="border-none">
              <AccordionTrigger className="py-3 text-sm">Generation defaults</AccordionTrigger>
              <AccordionContent>
                <div className="pb-2">
                  <GenerationSettingsFields value={settings} onChange={setSettings} />
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          <div className="space-y-2">
            <Label>Replace audio <span className="font-normal text-muted-foreground">(optional)</span></Label>
            <VoiceProfileAudioInput onChange={setAudio} />
          </div>

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
