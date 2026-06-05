"use client"

import { useQuery } from "@tanstack/react-query"
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  XCircle,
} from "lucide-react"
import { fetchVariantSummary } from "@/lib/api"

const STATUS_ICONS: Record<string, typeof CheckCircle2> = {
  ready: CheckCircle2,
  building: Loader2,
  pending: Clock,
  failed: XCircle,
  deprecated: AlertCircle,
}

const STATUS_COLORS: Record<string, string> = {
  ready: "text-success",
  building: "text-primary",
  pending: "text-muted-foreground",
  failed: "text-error",
  deprecated: "text-warning",
}

interface VariantDashboardProps {
  onSelectVoice?: (voiceId: string) => void
}

export function VariantDashboard({ onSelectVoice }: VariantDashboardProps) {
  const summaryQ = useQuery({
    queryKey: ["variant-summary"],
    queryFn: fetchVariantSummary,
  })

  if (summaryQ.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const summary = summaryQ.data ?? []

  const allModelIds = [...new Set(summary.flatMap((v) => v.models.map((m) => m.model_id)))]
  const modelNameMap: Record<string, string> = {}
  summary.forEach((v) => v.models.forEach((m) => { modelNameMap[m.model_id] = m.model_name }))

  const totalVoices = summary.length
  const totalReady = summary.reduce((acc, v) => acc + v.models.filter((m) => m.status === "ready").length, 0)
  const totalFailed = summary.reduce((acc, v) => acc + v.models.filter((m) => m.status === "failed").length, 0)
  const totalPending = summary.reduce((acc, v) => acc + v.models.filter((m) => m.status === "pending" || m.status === "building").length, 0)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg border border-border bg-surface p-4 text-center">
          <p className="text-2xl font-bold">{totalVoices}</p>
          <p className="text-xs text-muted-foreground">Voices</p>
        </div>
        <div className="rounded-lg border border-border bg-surface p-4 text-center">
          <p className="text-2xl font-bold text-success">{totalReady}</p>
          <p className="text-xs text-muted-foreground">Ready</p>
        </div>
        <div className="rounded-lg border border-border bg-surface p-4 text-center">
          <p className="text-2xl font-bold text-warning">{totalPending}</p>
          <p className="text-xs text-muted-foreground">Pending</p>
        </div>
        <div className="rounded-lg border border-border bg-surface p-4 text-center">
          <p className="text-2xl font-bold text-error">{totalFailed}</p>
          <p className="text-xs text-muted-foreground">Failed</p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-2">
              <th className="px-4 py-2.5 text-left font-medium">Voice</th>
              {allModelIds.map((mid) => (
                <th key={mid} className="px-3 py-2.5 text-center font-medium text-xs whitespace-nowrap">
                  {modelNameMap[mid] ?? mid}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {summary.map((item) => (
              <tr
                key={item.voice_id}
                className="hover:bg-surface/50 cursor-pointer"
                onClick={() => onSelectVoice?.(item.voice_id)}
              >
                <td className="px-4 py-2.5 font-medium">{item.voice_name}</td>
                {allModelIds.map((mid) => {
                  const vm = item.models.find((m) => m.model_id === mid)
                  const Icon = vm ? STATUS_ICONS[vm.status] ?? Clock : Clock
                  const color = vm ? STATUS_COLORS[vm.status] ?? "text-muted-foreground" : "text-muted-foreground"
                  return (
                    <td key={mid} className="px-3 py-2.5 text-center">
                      <Icon
                        className={`inline-block h-4 w-4 ${color} ${vm?.status === "building" ? "animate-spin" : ""}`}
                        title={vm?.error_message ?? vm?.status ?? "No variant"}
                      />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
