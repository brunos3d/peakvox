"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2,
  Circle,
  Hammer,
  Loader2,
  XCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { ensureVariant } from "@/lib/api"
import { useVoiceModelCompatibility } from "@/hooks/use-voice-model-compatibility"
import { useModels } from "@/hooks/use-models"
import type { AnyVoice } from "@/types"

interface ModelCompatibilitySectionProps {
  voice: AnyVoice
  primaryModelId?: string | null
  recommendedModelId?: string | null
}

const STATE_ICONS: Record<string, typeof CheckCircle2> = {
  ready: CheckCircle2,
  buildable: Circle,
  incompatible: XCircle,
}

const STATE_COLORS: Record<string, string> = {
  ready: "text-success",
  buildable: "text-muted-foreground",
  incompatible: "text-muted-foreground",
}

export function ModelCompatibilitySection({
  voice,
  primaryModelId,
  recommendedModelId,
}: ModelCompatibilitySectionProps) {
  const queryClient = useQueryClient()
  const { compat, loading } = useVoiceModelCompatibility(voice)
  const { data: models } = useModels()

  const modelNameMap = new Map(
    (models ?? []).map((m) => [m.id, m.name]),
  )

  const buildMut = useMutation({
    mutationFn: (modelId: string) =>
      ensureVariant(
        "public_voice_id" in voice ? voice.public_voice_id : voice.id,
        modelId,
      ),
    onSuccess: () => {
      const voiceId =
        "public_voice_id" in voice ? voice.public_voice_id : voice.id
      queryClient.invalidateQueries({
        queryKey: ["voice-variants", voiceId],
      })
      queryClient.invalidateQueries({ queryKey: ["variant-summary"] })
    },
  })

  if (loading) return null
  if (compat.length === 0) return null

  return (
    <div className="space-y-1">
      <p className="text-caption uppercase tracking-wide">
        Model Compatibility
      </p>
      <div className="rounded-lg border border-border divide-y divide-border">
        {compat.map((c) => {
          const Icon = STATE_ICONS[c.state] ?? Circle
          const color = STATE_COLORS[c.state] ?? "text-muted-foreground"
          const busy = buildMut.isPending && buildMut.variables === c.modelId
          const modelName = modelNameMap.get(c.modelId) ?? c.modelId

          return (
            <div
              key={c.modelId}
              className="flex items-center justify-between px-3 py-2.5"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon className={`h-4 w-4 shrink-0 ${color}`} />
                <span className="text-sm font-medium truncate">
                  {modelName}
                </span>
                {c.modelId === primaryModelId && (
                  <span className="shrink-0 rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 border border-emerald-500/20">
                    Primary
                  </span>
                )}
                {c.modelId === recommendedModelId &&
                  c.modelId !== primaryModelId && (
                    <span className="shrink-0 rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-medium text-blue-600 border border-blue-500/20">
                      Recommended
                    </span>
                  )}
              </div>

              {c.state === "buildable" && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-7 gap-1.5 text-xs shrink-0"
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
    </div>
  )
}
