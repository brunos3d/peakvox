"use client"

import { useMemo, useState } from "react"
import { Loader2, Search } from "lucide-react"
import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ModelRow, type ModelFilter, statusClasses } from "@/components/models/ModelRow"
import { ModelSection } from "@/components/models/ModelSection"
import { RuntimeSection } from "@/components/models/RuntimeSection"
import {
  canCancelOperation,
  useCancelRuntimeOperation,
  useModelsWithRuntimes,
  useRuntimeLifecycleAction,
  type RuntimeLifecycleAction,
} from "@/hooks/use-runtimes"
import { cn } from "@/lib/utils"
import type { Model } from "@/types"
import type { ModelWithRuntimesCard } from "@/types"

function isInstalled(model: Model): boolean {
  return model.install_status === "installed"
}

function asLegacyModel(card: ModelWithRuntimesCard): Model {
  const m = card.model as unknown as Model
  const defaultRuntime = card.runtimes.find((r) => r.runtime_id === card.default_runtime_id) ?? card.runtimes[0]
  if (defaultRuntime) {
    const phase = defaultRuntime.state.phase
    const isActive = phase === "active"
    const isInstalled = phase !== "notInstalled" && phase !== "failed"
    return {
      ...m,
      install_status: isInstalled ? "installed" : "not_installed",
      activation_status: isActive ? "active" : "inactive",
      status: isActive ? "loaded" : isInstalled ? "available" : "inactive",
    } as Model
  }
  return m
}

export default function ModelsPage() {
  const { data: composedCards = [], isLoading, error } = useModelsWithRuntimes()
  const runtimeLifecycle = useRuntimeLifecycleAction()
  const cancelOperation = useCancelRuntimeOperation()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<ModelFilter>("all")
  const [query, setQuery] = useState("")

  const models = useMemo<Model[]>(() => composedCards.map(asLegacyModel), [composedCards])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return models
      .filter((model) => {
        if (filter === "installed") return isInstalled(model)
        if (filter === "available") return !isInstalled(model)
        return true
      })
      .filter((model) => {
        if (!q) return true
        return [model.name, model.provider, model.description, model.id].some((v) =>
          v.toLowerCase().includes(q),
        )
      })
  }, [models, filter, query])

  const selected = (selectedId ? models.find((model) => model.id === selectedId) : null) ?? filtered[0] ?? null
  const selectedCard = selected ? composedCards.find((c) => c.model.id === selected.id) ?? null : null
  const installedCount = models.filter(isInstalled).length
  const availableCount = models.length - installedCount

  const contextPanel = selected ? (
    <div className="flex flex-col gap-6 p-6">
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-section-title">{selected.name}</h2>
            <p className="text-caption">
              {selected.provider} · {selected.id}
            </p>
          </div>
          <span
            className={cn(
              "rounded px-2 py-1 text-[11px] font-medium capitalize",
              statusClasses[selected.status],
            )}
          >
            {selected.install_status.replace("_", " ")} / {selected.activation_status}
          </span>
        </div>
      </div>

      <ModelSection model={selected} />

      <RuntimeSection
        card={selectedCard}
        onAction={(runtimeId, action: RuntimeLifecycleAction) =>
          runtimeLifecycle.mutate({ id: runtimeId, action })
        }
        onCancel={(runtimeId, operationId) => {
          cancelOperation.mutate({ runtimeId, operationId })
        }}
        canCancel={(runtimeId) => {
          const card = composedCards.find((c) =>
            c.runtimes.some((runtime) => runtime.runtime_id === runtimeId),
          )
          const runtime = card?.runtimes.find((r) => r.runtime_id === runtimeId)
          return canCancelOperation(runtime?.state.operation)
        }}
        actionPending={runtimeLifecycle.isPending || cancelOperation.isPending}
      />
    </div>
  ) : null

  return (
    <PageLayout contextPanel={contextPanel} contextTitle="Model details">
      <PageHeader
        title="Models"
        description="Registry-driven lifecycle, capabilities, requirements, and edition availability."
      />

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <SummaryStat label="Registered" value={models.length} />
        <SummaryStat label="Installed" value={installedCount} />
        <SummaryStat label="Available" value={availableCount} />
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={filter} onValueChange={(v) => setFilter(v as ModelFilter)}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="installed">Installed</TabsTrigger>
            <TabsTrigger value="available">Available</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search models..."
            className="pl-9"
          />
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 rounded-lg border border-border bg-surface py-12 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading models...
          </div>
        ) : error ? (
          <div className="rounded-lg border border-error/30 bg-error/10 p-4 text-sm text-error">
            Failed to load models.
          </div>
        ) : filtered.length > 0 ? (
          filtered.map((model) => (
            <ModelRow
              key={model.id}
              model={model}
              selected={model.id === selected?.id}
              onSelect={(m) => setSelectedId(m.id)}
            />
          ))
        ) : (
          <div className="rounded-lg border border-dashed border-border bg-surface/40 py-12 text-center text-sm text-muted-foreground">
            No models match this view.
          </div>
        )}
      </div>
    </PageLayout>
  )
}

function SummaryStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-caption uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  )
}
