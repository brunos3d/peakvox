"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2,
  Clock,
  Hammer,
  Loader2,
  MinusCircle,
  XCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { fetchModels, fetchVoiceVariants, ensureVariant } from "@/lib/api"

interface ModelCompatibilitySectionProps {
  publicVoiceId: string
}

const STATUS_ICONS: Record<string, typeof CheckCircle2> = {
  ready: CheckCircle2,
  building: Loader2,
  pending: Clock,
  failed: XCircle,
  missing: MinusCircle,
}

const STATUS_COLORS: Record<string, string> = {
  ready: "text-success",
  building: "text-primary",
  pending: "text-muted-foreground",
  failed: "text-error",
  missing: "text-muted-foreground",
}

const STATUS_LABELS: Record<string, string> = {
  ready: "Ready",
  building: "Building\u2026",
  pending: "Not built",
  failed: "Failed",
  missing: "Create Variant",
}

export function ModelCompatibilitySection({ publicVoiceId }: ModelCompatibilitySectionProps) {
  const queryClient = useQueryClient()

  const modelsQ = useQuery({
    queryKey: ["models"],
    queryFn: fetchModels,
  })

  const variantsQ = useQuery({
    queryKey: ["voice-variants", publicVoiceId],
    queryFn: () => fetchVoiceVariants(publicVoiceId),
  })

  const buildMut = useMutation({
    mutationFn: (modelId: string) => ensureVariant(publicVoiceId, modelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voice-variants", publicVoiceId] })
      queryClient.invalidateQueries({ queryKey: ["variant-summary"] })
    },
  })

  const models = modelsQ.data ?? []
  const variants = variantsQ.data ?? []
  const variantMap = new Map(variants.map((v) => [v.model_id, v]))

  if (modelsQ.isLoading) return null
  if (models.length === 0) return null

  return (
    <div className="space-y-1">
      <p className="text-caption uppercase tracking-wide">Model Compatibility</p>
      <div className="rounded-lg border border-border divide-y divide-border">
        {models.map((model) => {
          const variant = variantMap.get(model.id)
          const status = variant?.status ?? "missing"
          const Icon = STATUS_ICONS[status] ?? MinusCircle
          const color = STATUS_COLORS[status] ?? "text-muted-foreground"
          const busy = buildMut.isPending && buildMut.variables === model.id

          return (
            <div key={model.id} className="flex items-center justify-between px-3 py-2.5">
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon className={`h-4 w-4 shrink-0 ${color} ${status === "building" ? "animate-spin" : ""}`} />
                <span className="text-sm font-medium truncate">{model.name}</span>
              </div>

              {(!variant || status === "missing") && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="h-7 gap-1.5 text-xs shrink-0"
                  disabled={busy || buildMut.isPending}
                  onClick={() => buildMut.mutate(model.id)}
                >
                  {busy
                    ? <Loader2 className="h-3 w-3 animate-spin" />
                    : <Hammer className="h-3 w-3" />}
                  Create Variant
                </Button>
              )}

              {variant && status !== "missing" && (
                <span className={`inline-flex items-center gap-1 text-xs ${color}`}>
                  {STATUS_LABELS[status] ?? status}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
