"use client"

import { useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2,
  Circle,
  Hammer,
  Loader2,
  MinusCircle,
  XCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAppStore } from "@/store/use-store"
import { computeVoiceModelCompatibility } from "@/hooks/use-voice-model-compatibility"
import { fetchVariantSummary, backfillMissingVariants } from "@/lib/api"
import type { RealizationState, VoiceModelCompatibility } from "@/types"

interface VariantDashboardProps {
  onSelectVoice?: (voiceId: string) => void
}

const CELL_ICONS: Record<RealizationState, typeof CheckCircle2> = {
  ready: CheckCircle2,
  buildable: Circle,
  incompatible: XCircle,
}

const CELL_COLORS: Record<RealizationState, string> = {
  ready: "text-success",
  buildable: "text-warning",
  incompatible: "text-destructive",
}

interface CellState {
  state: RealizationState
  error?: string
}

function computeCell(
  compatibleModels: string[],
  modelId: string,
  variantStatus: string | undefined,
): CellState {
  const isCompatible = compatibleModels.includes(modelId)
  const isReady = variantStatus === "ready"
  if (isCompatible && isReady) return { state: "ready" }
  if (isCompatible) return { state: "buildable" }
  return { state: "incompatible" }
}

export function VariantDashboard({ onSelectVoice }: VariantDashboardProps) {
  const voices = useAppStore((s) => s.voices)
  const voiceMap = useMemo(
    () => new Map(voices.map((v) => [v.id, v])),
    [voices],
  )

  const summaryQ = useQuery({
    queryKey: ["variant-summary"],
    queryFn: fetchVariantSummary,
  })

  const queryClient = useQueryClient()

  const backfillMut = useMutation({
    mutationFn: () => backfillMissingVariants(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["variant-summary"] })
    },
  })

  if (summaryQ.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const summary = summaryQ.data ?? []

  const allModelIds = [
    ...new Set(summary.flatMap((v) => v.models.map((m) => m.model_id))),
  ]
  const modelNameMap: Record<string, string> = {}
  summary.forEach((v) =>
    v.models.forEach((m) => {
      modelNameMap[m.model_id] = m.model_name
    }),
  )

  // Compute three-state stats
  let totalReady = 0
  let totalBuildable = 0
  let totalIncompatible = 0

  const cells: Record<string, Record<string, CellState>> = {}
  for (const item of summary) {
    const profile = voiceMap.get(item.voice_id)
    const compatibleModels = profile?.compatible_models ?? []
    const rowCells: Record<string, CellState> = {}
    for (const mid of allModelIds) {
      const vm = item.models.find((m) => m.model_id === mid)
      const cell = computeCell(compatibleModels, mid, vm?.status)
      rowCells[mid] = cell
      if (cell.state === "ready") totalReady++
      else if (cell.state === "buildable") totalBuildable++
      else totalIncompatible++
    }
    cells[item.voice_id] = rowCells
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="grid grid-cols-5 gap-4 flex-1">
          <div className="rounded-lg border border-border bg-surface p-4 text-center">
            <p className="text-2xl font-bold">{summary.length}</p>
            <p className="text-xs text-muted-foreground">Voices</p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4 text-center">
            <p className="text-2xl font-bold text-success">{totalReady}</p>
            <p className="text-xs text-muted-foreground">Ready</p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4 text-center">
            <p className="text-2xl font-bold text-amber-600">{totalBuildable}</p>
            <p className="text-xs text-muted-foreground">Buildable</p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4 text-center">
            <p className="text-2xl font-bold text-destructive">
              {totalIncompatible}
            </p>
            <p className="text-xs text-muted-foreground">Incompatible</p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4 text-center">
            <p className="text-2xl font-bold">
              {summary.reduce(
                (acc, v) => acc + v.models.filter((m) => m.status === "failed").length,
                0,
              )}
            </p>
            <p className="text-xs text-muted-foreground">Failed</p>
          </div>
        </div>
        <div className="ml-4">
          <Button
            variant="secondary"
            size="sm"
            className="gap-1.5 text-xs shrink-0"
            disabled={backfillMut.isPending}
            onClick={() => backfillMut.mutate()}
          >
            {backfillMut.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Hammer className="h-3.5 w-3.5" />
            )}
            Backfill Missing
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-2">
              <th className="px-4 py-2.5 text-left font-medium">Voice</th>
              {allModelIds.map((mid) => (
                <th
                  key={mid}
                  className="px-3 py-2.5 text-center font-medium text-xs whitespace-nowrap"
                >
                  {modelNameMap[mid] ?? mid}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {summary.map((item) => {
              const row = cells[item.voice_id] ?? {}
              return (
                <tr
                  key={item.voice_id}
                  className="hover:bg-surface/50 cursor-pointer"
                  onClick={() => onSelectVoice?.(item.voice_id)}
                >
                  <td className="px-4 py-2.5 font-medium">
                    {item.voice_name}
                  </td>
                  {allModelIds.map((mid) => {
                    const cell = row[mid]
                    if (!cell) return <td key={mid} />
                    const Icon = CELL_ICONS[cell.state]
                    const color = CELL_COLORS[cell.state]
                    return (
                      <td key={mid} className="px-3 py-2.5 text-center">
                        <Icon
                          className={`inline-block h-4 w-4 ${color}`}
                          aria-label={cell.state}
                        />
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
