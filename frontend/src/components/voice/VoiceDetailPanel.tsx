"use client"

import { useState } from "react"
import {
  Heart,
  Code2,
  ChevronDown,
  ChevronRight,
  Loader2,
  Plus,
  Music2,
  Copy,
  Check,
} from "lucide-react"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AudioPlayer } from "@/components/AudioPlayer"
import { UseInApiDialog } from "@/components/api/UseInApiDialog"
import { VariantManager } from "@/components/voice/VariantManager"
import { getVoiceAudioUrl, setVoiceFavorite, importVoiceResource } from "@/lib/api"
import { cn, formatDuration } from "@/lib/utils"
import type { AnyVoice, VoiceProfile } from "@/types"
import { isVoiceProfile, isTemporaryVoice } from "@/types"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"

interface VoiceDetailPanelProps {
  voice: AnyVoice | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function hasSourceAudio(voice: AnyVoice): voice is VoiceProfile {
  return isVoiceProfile(voice) && voice.creation_source === "SOURCE_ASSET" && voice.source_asset != null
}

function hasTranscript(voice: AnyVoice): boolean {
  return isVoiceProfile(voice) && voice.creation_source !== "PRESET_VOICE" && !!voice.transcript
}

function hasProvider(voice: AnyVoice): string | null {
  if (isTemporaryVoice(voice)) return voice.provider_id
  if (isVoiceProfile(voice) && voice.meta?.provider != null) return String(voice.meta.provider)
  return null
}

function isPresetVoice(voice: AnyVoice): boolean {
  return isTemporaryVoice(voice) || (isVoiceProfile(voice) && voice.creation_source === "PRESET_VOICE")
}

function Section({
  title,
  open: defaultOpen = true,
  children,
}: {
  title: string
  open?: boolean
  children: React.ReactNode
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  if (!children) return null

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-2 px-6 py-3 text-caption uppercase tracking-wide hover:bg-muted/30 transition-colors"
      >
        {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {title}
      </button>
      {isOpen && <div className="px-6 pb-4">{children}</div>}
    </div>
  )
}

/**
 * VoiceDetailPanel — the deep-dive sheet for power users.
 *
 * The right-rail ``SelectedVoicePanel`` is the canonical inspector (header,
 * preview, overview, compat, actions). The detail dialog now focuses on
 * the information that is NOT already in the right rail:
 *
 *   - Description (long-form text)
 *   - Source audio (for SOURCE_ASSET voices that have a stored source clip)
 *   - Transcript (for non-preset profiles with a transcript)
 *   - Preset tags (cloned voices only)
 *   - Variants (version history + manual rebuild) — the *only* reason to
 *     open this dialog in the day-to-day flow
 *   - Power-user actions: Use in API, Copy voice ID, Favorite toggle
 *   - Import to Library (for temporary voices that haven't been imported)
 *
 * Anything that is already visible on the right rail (name, language,
 * creation source, usage, compat matrix, Use in TTS, Edit, Delete) is
 * intentionally NOT re-rendered here.
 */
export function VoiceDetailPanel({ voice, open, onOpenChange }: VoiceDetailPanelProps) {
  const [copied, setCopied] = useState(false)
  const [apiOpen, setApiOpen] = useState(false)
  const [importing, setImporting] = useState(false)
  const queryClient = useQueryClient()
  const router = useRouter()

  const toggleFav = useMutation({
    mutationFn: ({ id, value }: { id: string; value: boolean }) => setVoiceFavorite(id, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voices-page"] })
      queryClient.invalidateQueries({ queryKey: ["voices"] })
    },
  })

  if (!voice) return null

  const profile = isVoiceProfile(voice) ? voice : null
  const tempVoice = isTemporaryVoice(voice) ? voice : null
  const hasProv = hasProvider(voice)
  const showImport = isPresetVoice(voice) && !!tempVoice && !profile

  const handleImport = async () => {
    if (!tempVoice) return
    setImporting(true)
    try {
      const newProfile = await importVoiceResource(tempVoice.source_resource_id)
      queryClient.invalidateQueries({ queryKey: ["voices-page"] })
      queryClient.invalidateQueries({ queryKey: ["voices"] })
      // Promote the new profile to the right rail.
      onOpenChange(false)
      router.push("/voices")
    } finally {
      setImporting(false)
    }
  }

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="right" className="w-full sm:max-w-md p-0 flex flex-col">
          <SheetHeader className="border-b border-border px-6 py-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 space-y-1">
                <SheetTitle className="truncate">{voice.name}</SheetTitle>
                {profile && (
                  <p className="text-xs text-muted-foreground">
                    {voice.description ? truncate(voice.description, 120) : "Voice details"}
                  </p>
                )}
              </div>
              {profile && (
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn("shrink-0", profile.is_favorite && "text-red-500 hover:text-red-600")}
                  onClick={() => toggleFav.mutate({ id: profile.id, value: !profile.is_favorite })}
                  disabled={toggleFav.isPending}
                  title={profile.is_favorite ? "Remove from favorites" : "Add to favorites"}
                >
                  <Heart className={cn("h-5 w-5", profile.is_favorite && "fill-current")} />
                </Button>
              )}
            </div>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto divide-y divide-border">
            {profile?.description && (
              <Section title="Description">
                <p className="text-sm text-foreground/90 leading-relaxed">{profile.description}</p>
              </Section>
            )}

            {hasSourceAudio(voice) && (
              <Section title="Source Audio">
                <div className="rounded-lg border border-border bg-surface p-3 space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <Music2 className="h-3.5 w-3.5 text-muted-foreground" />
                    <p className="text-caption uppercase tracking-wide">Source audio</p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {voice.source_asset!.original_filename ?? "Untitled source"} &middot;{" "}
                    {voice.source_asset!.audio_duration ? formatDuration(voice.source_asset!.audio_duration) : "\u2014"}
                  </p>
                  <AudioPlayer
                    audioUrl={getVoiceAudioUrl(voice.id)}
                    title="Source audio"
                    duration={voice.audio_duration ?? undefined}
                  />
                </div>
              </Section>
            )}

            {hasTranscript(voice) && (
              <Section title="Transcript">
                <p className="text-sm text-foreground/90 leading-relaxed">{voice.transcript}</p>
              </Section>
            )}

            {profile?.preset_tags && profile.preset_tags.length > 0 && (
              <Section title="Tags">
                <div className="flex flex-wrap gap-1.5">
                  {profile.preset_tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                  ))}
                </div>
              </Section>
            )}

            {profile && (
              <Section title="Variants" open={false}>
                <VariantManager publicVoiceId={profile.public_voice_id} />
              </Section>
            )}

            {!profile && hasProv && (
              <Section title="Provider">
                <Badge variant="secondary" className="gap-1 text-xs">{hasProv}</Badge>
              </Section>
            )}
          </div>

          {/* Power-user actions: API / Copy / Import (for temp voices)        */}
          {/* Use-in-TTS / Edit / Delete live on the right rail — no duplicates. */}
          <div className="border-t border-border p-4 flex items-center gap-2">
            {profile ? (
              <>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setApiOpen(true)}
                  title="Use in API"
                >
                  <Code2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => {
                    navigator.clipboard?.writeText(profile.public_voice_id).then(() => {
                      setCopied(true)
                      setTimeout(() => setCopied(false), 1500)
                    })
                  }}
                  title="Copy voice ID"
                >
                  {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                </Button>
                <span className="ml-auto text-[10px] text-muted-foreground">
                  Use-in-TTS, Edit and Delete are in the right rail.
                </span>
              </>
            ) : showImport ? (
              <Button className="flex-1 gap-2" onClick={handleImport} disabled={importing}>
                {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Import to Library
              </Button>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
      {profile && (
        <UseInApiDialog voiceId={profile.public_voice_id} open={apiOpen} onOpenChange={setApiOpen} />
      )}
    </>
  )
}

function truncate(s: string, max: number): string {
  if (s.length <= max) return s
  return s.slice(0, max - 1).trimEnd() + "\u2026"
}
