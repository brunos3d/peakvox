"use client"

import Link from "next/link"
import { Wand2, Pencil, Trash2, Sparkles, AudioLines } from "lucide-react"
import { Button } from "@/components/ui/button"
import { AudioPlayer } from "@/components/AudioPlayer"
import { getVoiceAudioUrl } from "@/lib/api"
import { formatDuration } from "@/lib/utils"
import { isTemporaryVoice, isVoiceProfile } from "@/types"
import type { AnyVoice, VoiceProfile } from "@/types"

const CREATION_SOURCE_LABELS: Record<string, string> = {
  SOURCE_ASSET: "Cloned",
  PRESET_VOICE: "Preset",
  MARKETPLACE_VOICE: "Marketplace",
  TRAINED_VOICE: "Trained",
  IMPORTED_VOICE: "Imported",
  SYSTEM_VOICE: "System",
}

interface SelectedVoicePanelProps {
  voice: AnyVoice | null
  onUseInTts?: (voice: VoiceProfile) => void
  onEdit?: (voice: VoiceProfile) => void
  onDelete?: (voice: VoiceProfile) => void
  onDiscardTemporary?: () => void
}

/**
 * Right-rail "Selected voice" panel.
 *
 * Renders distinct layouts for the two voice kinds:
 *   • **VoiceProfile (cloned / trained / marketplace / imported)** — shows
 *     reference audio, Edit + Delete, and a Use-in-TTS shortcut.
 *   • **VoiceProfile with `creation_source = PRESET_VOICE` or a TemporaryVoice**
 *     — never shows reference audio (presets are catalog records, not
 *     recordings the user owns). Edit + Delete are also hidden for presets
 *     because the user does not "own" them.
 *
 * The previous version rendered reference audio + Edit + Delete for every
 * VoiceProfile, which made imported preset voices (e.g. "Alloy (en-us)")
 * look identical to a cloned voice — including a non-functional
 * `--:-- / --:--` audio player and a misleading "Reference audio" label.
 */
export function SelectedVoicePanel({
  voice,
  onUseInTts,
  onEdit,
  onDelete,
  onDiscardTemporary,
}: SelectedVoicePanelProps) {
  if (!voice) {
    return (
      <div className="flex flex-col gap-5 p-6">
        <div>
          <h2 className="text-section-title">Selected voice</h2>
          <p className="text-caption mt-0.5">Single-click a card to select, double-click for details.</p>
        </div>
        <p className="text-sm text-muted-foreground">No voice selected.</p>
      </div>
    )
  }

  const profile = isVoiceProfile(voice) ? voice : null
  const isPreset =
    isTemporaryVoice(voice) || profile?.creation_source === "PRESET_VOICE"

  const subtitleParts: string[] = []
  if (voice.language) subtitleParts.push(voice.language)
  if (profile) {
    const sourceLabel = CREATION_SOURCE_LABELS[profile.creation_source] ?? profile.creation_source
    subtitleParts.push(sourceLabel)
    if (profile.audio_duration) subtitleParts.push(formatDuration(profile.audio_duration))
  } else {
    subtitleParts.push("Preset")
  }

  return (
    <div className="flex flex-col gap-5 p-6">
      <div>
        <h2 className="text-section-title">Selected voice</h2>
        <p className="text-caption mt-0.5">Single-click a card to select, double-click for details.</p>
      </div>

      <div className="space-y-4">
        <div>
          <p className="text-card-title">{voice.name}</p>
          <p className="text-caption">{subtitleParts.filter(Boolean).join(" · ")}</p>
        </div>

        {isPreset ? <PresetActions /> : (
          profile && (
            <ClonedActions
              profile={profile}
              onUseInTts={onUseInTts}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          )
        )}

        {/* Preset footer: small actions for clearing or going to TTS */}
        {isPreset && (
          <div className="flex gap-2">
            <Button asChild className="flex-1 gap-2">
              <Link href="/"><Wand2 className="h-4 w-4" /> Use in TTS</Link>
            </Button>
            {isTemporaryVoice(voice) && onDiscardTemporary && (
              <Button variant="outline" size="sm" onClick={onDiscardTemporary}>
                Clear
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ClonedActions({
  profile,
  onUseInTts,
  onEdit,
  onDelete,
}: Pick<SelectedVoicePanelProps, "onUseInTts" | "onEdit" | "onDelete"> & { profile: VoiceProfile }) {
  return (
    <>
      {profile.audio_duration != null && profile.audio_duration > 0 ? (
        <AudioPlayer
          audioUrl={getVoiceAudioUrl(profile.id)}
          title="Reference audio"
          duration={profile.audio_duration}
        />
      ) : (
        <div className="rounded-lg border border-dashed border-border bg-surface/40 px-3 py-4 text-center text-xs text-muted-foreground">
          <AudioLines className="mx-auto mb-1 h-4 w-4" />
          No reference audio stored
        </div>
      )}
      <div className="flex gap-2">
        <Button
          asChild={!onUseInTts}
          className="flex-1 gap-2"
          onClick={onUseInTts ? () => onUseInTts(profile) : undefined}
        >
          {onUseInTts ? (
            <>
              <Wand2 className="h-4 w-4" /> Use in TTS
            </>
          ) : (
            <Link href="/"><Wand2 className="h-4 w-4" /> Use in TTS</Link>
          )}
        </Button>
        {onEdit && (
          <Button variant="outline" size="icon" onClick={() => onEdit(profile)} title="Edit">
            <Pencil className="h-4 w-4" />
          </Button>
        )}
        {onDelete && (
          <Button
            variant="outline"
            size="icon"
            className="text-error hover:text-error"
            onClick={() => onDelete(profile)}
            title="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
    </>
  )
}

function PresetActions() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface/40 px-3 py-4 text-center text-xs text-muted-foreground">
      <Sparkles className="mx-auto mb-1 h-4 w-4" />
      Preset voices are catalog entries from a provider — they can&apos;t be edited or deleted.
      Use the <span className="font-medium text-foreground">Use in TTS</span> action to start
      generating, or import the voice to your library to make it permanent.
    </div>
  )
}
