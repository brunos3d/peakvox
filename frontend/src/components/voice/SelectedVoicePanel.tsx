"use client"

import { useState } from "react"
import Link from "next/link"
import {
  CheckCircle2,
  Circle,
  Hammer,
  Loader2,
  XCircle,
  Wand2,
  Pencil,
  Trash2,
  Sparkles,
  AudioLines,
  Heart,
  Clock,
  Calendar,
  Activity,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { AudioPlayer } from "@/components/AudioPlayer"
import { getVoiceAudioUrl, ensureVariant } from "@/lib/api"
import { formatDuration } from "@/lib/utils"
import { useVoiceModelCompatibility } from "@/hooks/use-voice-model-compatibility"
import { useModels } from "@/hooks/use-models"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { isTemporaryVoice, isVoiceProfile } from "@/types"
import type { AnyVoice, VoiceProfile } from "@/types"
import { cn } from "@/lib/utils"

const CREATION_SOURCE_LABELS: Record<string, string> = {
  SOURCE_ASSET: "Cloned",
  PRESET_VOICE: "Preset",
  MARKETPLACE_VOICE: "Marketplace",
  TRAINED_VOICE: "Trained",
  IMPORTED_VOICE: "Imported",
  SYSTEM_VOICE: "System",
}

const STATE_ICONS: Record<string, typeof CheckCircle2> = {
  ready: CheckCircle2,
  buildable: Circle,
  incompatible: XCircle,
}

const STATE_COLORS: Record<string, string> = {
  ready: "text-success",
  buildable: "text-warning",
  incompatible: "text-muted-foreground",
}

interface SelectedVoicePanelProps {
  voice: AnyVoice | null
  primaryModelId?: string | null
  recommendedModelId?: string | null
  onUseInTts?: (voice: VoiceProfile) => void
  onEdit?: (voice: VoiceProfile) => void
  onDelete?: (voice: VoiceProfile) => void
  onDiscardTemporary?: () => void
}

/**
 * The right-rail "Selected voice" inspector — the canonical, single place
 * to see everything about a voice once it's selected in the library.
 *
 * Layout (top → bottom):
 *   1. Header        — name, language, voice type, favorite
 *   2. Preview       — reference audio for cloned voices; empty state for presets
 *   3. Overview      — provider, usage, created, last used (lightweight metadata)
 *   4. Compatibility — model matrix with ready / build / incompatible states
 *   5. Variants      — counts + per-model build state (if any)
 *   6. Actions       — Use in TTS, Edit, Delete (existing buttons, near the bottom)
 *
 * For preset voices, sections that depend on owned data (preview, edit, delete,
 * variants) are hidden. Use in TTS is always present.
 */
export function SelectedVoicePanel({
  voice,
  primaryModelId,
  recommendedModelId,
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

  return (
    <div className="flex flex-col gap-5 p-6">
      <VoiceHeader voice={voice} profile={profile} isPreset={isPreset} />

      <PreviewSection voice={voice} profile={profile} isPreset={isPreset} />

      <OverviewSection voice={voice} profile={profile} isPreset={isPreset} />

      {profile && (
        <CompatibilitySection
          voice={profile}
          primaryModelId={primaryModelId}
          recommendedModelId={recommendedModelId}
        />
      )}

      <ActionsSection
        voice={voice}
        profile={profile}
        isPreset={isPreset}
        onUseInTts={onUseInTts}
        onEdit={onEdit}
        onDelete={onDelete}
        onDiscardTemporary={onDiscardTemporary}
      />
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Header                                                                    */
/* -------------------------------------------------------------------------- */

function VoiceHeader({
  voice,
  profile,
  isPreset,
}: {
  voice: AnyVoice
  profile: VoiceProfile | null
  isPreset: boolean
}) {
  const sourceLabel =
    profile
      ? CREATION_SOURCE_LABELS[profile.creation_source] ?? profile.creation_source
      : "Preset"
  const language = voice.language ?? voice.language_code ?? "—"
  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-card-title truncate">{voice.name}</p>
          <p className="text-caption truncate">
            {language} · {sourceLabel}
            {profile?.audio_duration ? ` · ${formatDuration(profile.audio_duration)}` : null}
          </p>
        </div>
        {profile?.is_favorite && (
          <Heart className="h-4 w-4 shrink-0 fill-current text-error" aria-label="Favorite" />
        )}
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Preview                                                                   */
/* -------------------------------------------------------------------------- */

function PreviewSection({
  voice,
  profile,
  isPreset,
}: {
  voice: AnyVoice
  profile: VoiceProfile | null
  isPreset: boolean
}) {
  if (isPreset) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-surface/40 px-3 py-4 text-center text-xs text-muted-foreground">
        <Sparkles className="mx-auto mb-1 h-4 w-4" />
        Preset voices are catalog entries from a provider — they have no stored
        reference sample. Use <span className="font-medium text-foreground">Use in TTS</span> to
        try one, or import it to your library to make it permanent.
      </div>
    )
  }
  if (!profile) return null
  if (profile.audio_duration != null && profile.audio_duration > 0) {
    return (
      <AudioPlayer
        audioUrl={getVoiceAudioUrl(profile.id)}
        title="Reference audio"
        duration={profile.audio_duration}
      />
    )
  }
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface/40 px-3 py-4 text-center text-xs text-muted-foreground">
      <AudioLines className="mx-auto mb-1 h-4 w-4" />
      No reference audio stored
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Overview                                                                  */
/* -------------------------------------------------------------------------- */

function OverviewSection({
  voice,
  profile,
  isPreset,
}: {
  voice: AnyVoice
  profile: VoiceProfile | null
  isPreset: boolean
}) {
  const provider =
    profile?.meta?.provider ??
    (isTemporaryVoice(voice) ? voice.provider_id : null) ??
    (isPreset ? "Provider" : "—")
  const usageCount = profile?.usage_count
  const createdAt = profile?.created_at
  const lastUsedAt = profile?.last_used_at

  return (
    <div className="space-y-1.5">
      <p className="text-caption uppercase tracking-wide">Overview</p>
      <dl className="rounded-lg border border-border divide-y divide-border text-xs">
        {provider && (
          <MetaRow label="Provider" value={String(provider)} icon={Sparkles} />
        )}
        {usageCount != null && (
          <MetaRow label="Usage count" value={String(usageCount)} icon={Activity} />
        )}
        {createdAt && (
          <MetaRow label="Created" value={formatDate(createdAt)} icon={Calendar} />
        )}
        {lastUsedAt != null && (
          <MetaRow
            label="Last used"
            value={lastUsedAt ? formatDate(lastUsedAt) : "Never"}
            icon={Clock}
          />
        )}
      </dl>
    </div>
  )
}

function MetaRow({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: string
  icon?: React.ComponentType<{ className?: string }>
}) {
  return (
    <div className="flex items-center justify-between gap-2 px-3 py-2">
      <dt className="flex items-center gap-1.5 text-muted-foreground">
        {Icon && <Icon className="h-3 w-3" />}
        {label}
      </dt>
      <dd className="truncate font-medium">{value}</dd>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Compatibility                                                             */
/* -------------------------------------------------------------------------- */

function CompatibilitySection({
  voice,
  primaryModelId,
  recommendedModelId,
}: {
  voice: AnyVoice
  primaryModelId?: string | null
  recommendedModelId?: string | null
}) {
  const { compat, loading, getState } = useVoiceModelCompatibility(voice)
  const { data: models } = useModels()
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState(true)

  const buildMut = useMutation({
    mutationFn: (modelId: string) => {
      if (!("public_voice_id" in voice)) {
        return Promise.reject(new Error("Cannot build variant for temporary voice"))
      }
      return ensureVariant(voice.public_voice_id, modelId)
    },
    onSuccess: () => {
      if (!("public_voice_id" in voice)) return
      queryClient.invalidateQueries({
        queryKey: ["voice-variants", voice.public_voice_id],
      })
      queryClient.invalidateQueries({ queryKey: ["variant-summary"] })
    },
  })

  if (loading) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-surface/40 px-3 py-3 text-center text-xs text-muted-foreground">
        <Loader2 className="mx-auto h-4 w-4 animate-spin" />
        Loading compatibility…
      </div>
    )
  }
  if (compat.length === 0) return null

  // Compact 1-line summary: "X ready · Y buildable · Z not available"
  const counts = {
    ready: compat.filter((c) => c.state === "ready").length,
    buildable: compat.filter((c) => c.state === "buildable").length,
    incompatible: compat.filter((c) => c.state === "incompatible").length,
  }
  const modelNameMap = new Map((models ?? []).map((m) => [m.id, m.name]))

  return (
    <div className="space-y-1.5">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-caption uppercase tracking-wide hover:text-foreground"
      >
        <span>Compatible models</span>
        {expanded ? (
          <ChevronUp className="h-3 w-3" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>
      <p className="text-[10px] text-muted-foreground">
        {counts.ready} ready · {counts.buildable} buildable · {counts.incompatible} not available
      </p>
      {expanded && (
        <div className="rounded-lg border border-border divide-y divide-border">
          {compat.map((c) => {
            const Icon = STATE_ICONS[c.state] ?? Circle
            const color = STATE_COLORS[c.state] ?? "text-muted-foreground"
            const busy = buildMut.isPending && buildMut.variables === c.modelId
            const modelName = modelNameMap.get(c.modelId) ?? c.modelId
            const isPrimary = c.modelId === primaryModelId
            const isRecommended = c.modelId === recommendedModelId && !isPrimary

            return (
              <div
                key={c.modelId}
                className="flex items-center justify-between px-3 py-2.5"
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  <Icon className={cn("h-4 w-4 shrink-0", color)} />
                  <span className="truncate text-sm font-medium">{modelName}</span>
                  {isPrimary && (
                    <span className="shrink-0 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 border border-emerald-500/20">
                      Primary
                    </span>
                  )}
                  {isRecommended && (
                    <span className="shrink-0 rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-medium text-blue-600 border border-blue-500/20">
                      Recommended
                    </span>
                  )}
                </div>

                {c.state === "buildable" && (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="h-7 shrink-0 gap-1.5 text-xs"
                    disabled={busy || buildMut.isPending}
                    onClick={() => buildMut.mutate(c.modelId)}
                  >
                    {busy ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Hammer className="h-3 w-3" />
                    )}
                    Create Variant
                  </Button>
                )}

                {c.state === "ready" && (
                  <span className="inline-flex items-center gap-1 text-xs text-success">
                    Ready
                  </span>
                )}

                {c.state === "incompatible" && (
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    Not available
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Actions                                                                   */
/* -------------------------------------------------------------------------- */

function ActionsSection({
  voice,
  profile,
  isPreset,
  onUseInTts,
  onEdit,
  onDelete,
  onDiscardTemporary,
}: Pick<
  SelectedVoicePanelProps,
  "onUseInTts" | "onEdit" | "onDelete" | "onDiscardTemporary"
> & {
  voice: AnyVoice
  profile: VoiceProfile | null
  isPreset: boolean
}) {
  const handleUse = () => {
    if (profile && onUseInTts) onUseInTts(profile)
  }

  return (
    <div className="space-y-1.5">
      <p className="text-caption uppercase tracking-wide">Actions</p>
      <div className="flex gap-2">
        <Button
          asChild={!onUseInTts || isPreset}
          className="flex-1 gap-2"
          onClick={onUseInTts && !isPreset ? handleUse : undefined}
        >
          {onUseInTts && !isPreset ? (
            <>
              <Wand2 className="h-4 w-4" /> Use in TTS
            </>
          ) : (
            <Link href="/"><Wand2 className="h-4 w-4" /> Use in TTS</Link>
          )}
        </Button>
        {!isPreset && onEdit && profile && (
          <Button variant="outline" size="icon" onClick={() => onEdit(profile)} title="Edit">
            <Pencil className="h-4 w-4" />
          </Button>
        )}
        {!isPreset && onDelete && profile && (
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
        {isPreset && isTemporaryVoice(voice) && onDiscardTemporary && (
          <Button variant="outline" size="sm" onClick={onDiscardTemporary}>
            Clear
          </Button>
        )}
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Helpers                                                                   */
/* -------------------------------------------------------------------------- */

function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  } catch {
    return iso
  }
}

// Re-export the compat getter so tests can introspect.
export { useVoiceModelCompatibility as _internalUseVoiceModelCompatibility }
