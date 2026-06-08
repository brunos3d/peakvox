"use client"

import { useMemo, useState } from "react"
import {
  CheckCircle2,
  Cpu,
  Download,
  HardDrive,
  Loader2,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  Search,
  Server,
  Trash2,
} from "lucide-react"
import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useModelLifecycleAction, useModels, type ModelLifecycleAction } from "@/hooks/use-models"
import { useModelsWithRuntimes, useRuntimeLifecycleAction, type RuntimeLifecycleAction } from "@/hooks/use-runtimes"
import { cn } from "@/lib/utils"
import type { Model, ModelCapabilities } from "@/types"
import type { ModelWithRuntimesCard, RuntimeCard, RuntimePhase } from "@/types"

type ModelFilter = "all" | "installed" | "available"

const statusClasses: Record<Model["status"], string> = {
  available: "bg-success/15 text-success",
  loaded: "bg-primary/15 text-primary",
  loading: "bg-warning/15 text-warning",
  error: "bg-error/15 text-error",
  disabled: "bg-muted text-muted-foreground",
  inactive: "bg-muted text-muted-foreground",
  deprecated: "bg-warning/15 text-warning",
}

const capabilityLabels: Array<[keyof ModelCapabilities, string]> = [
  ["supports_tts", "TTS"],
  ["supports_voice_cloning", "Voice cloning"],
  ["supports_voice_design", "Voice design"],
  ["supports_emotion_tags", "Emotion tags"],
  ["supports_singing", "Singing"],
  ["supports_multilingual", "Multilingual"],
  ["supports_reference_audio", "Reference audio"],
  ["supports_voice_conversion", "Voice conversion"],
  ["supports_streaming", "Streaming"],
  ["supports_api", "API"],
]

function isInstalled(model: Model): boolean {
  return model.install_status === "installed"
}

function formatMemory(model: Model): string {
  return model.memory_requirements.min_vram_gb == null
    ? "Unknown"
    : `${model.memory_requirements.min_vram_gb} GB VRAM`
}

function lifecycleLabel(action: ModelLifecycleAction): string {
  return action[0].toUpperCase() + action.slice(1)
}

function metadataString(value: string | string[] | undefined, fallback: string): string {
  if (Array.isArray(value)) return value.join(", ")
  return value ?? fallback
}

function CapabilityBadge({ supported, label }: { supported: boolean; label: string }) {
  return (
    <Badge
      variant={supported ? "default" : "secondary"}
      className={cn(
        "rounded-md px-2 py-0.5 text-[11px] font-normal",
        supported ? "bg-primary/15 text-primary hover:bg-primary/20" : "text-muted-foreground",
      )}
    >
      {supported ? "✓" : "−"} {label}
    </Badge>
  )
}

const RUNTIME_PHASE_LABEL: Record<RuntimePhase, string> = {
  NotInstalled: "Not Installed",
  Pulling: "Pulling image...",
  Installed: "Installed (image present, container stopped)",
  Starting: "Starting container...",
  Active: "Active (container running, /ready 200)",
  Stopping: "Stopping...",
  Stopped: "Stopped",
  Failed: "Failed",
  Updating: "Updating...",
}

const RUNTIME_PHASE_BADGE: Record<RuntimePhase, string> = {
  NotInstalled: "bg-muted text-muted-foreground",
  Pulling: "bg-warning/15 text-warning",
  Installed: "bg-muted text-muted-foreground",
  Starting: "bg-warning/15 text-warning",
  Active: "bg-success/15 text-success",
  Stopping: "bg-muted text-muted-foreground",
  Stopped: "bg-muted text-muted-foreground",
  Failed: "bg-error/15 text-error",
  Updating: "bg-warning/15 text-warning",
}

function RuntimeSection({
  card,
  onAction,
  actionPending,
}: {
  card: ModelWithRuntimesCard | null | undefined
  onAction: (runtimeId: string, action: RuntimeLifecycleAction) => void
  actionPending: boolean
}) {
  if (!card) return null
  const defaultRuntime = card.runtimes.find((r) => r.runtime_id === card.default_runtime_id) ?? card.runtimes[0]

  return (
    <div className="space-y-2">
      <p className="text-caption uppercase tracking-wide">Runtime</p>
      {defaultRuntime ? (
        <div className="rounded-md border border-border bg-surface-2 p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-mono">
                {defaultRuntime.descriptor?.spec?.image?.repository}:{defaultRuntime.descriptor?.spec?.image?.tag}
              </p>
              {defaultRuntime.state.endpoint && (
                <p className="text-xs text-muted-foreground font-mono break-all">
                  {defaultRuntime.state.endpoint}
                </p>
              )}
            </div>
            <span className={cn("rounded px-2 py-1 text-[10px] font-medium", RUNTIME_PHASE_BADGE[defaultRuntime.state.phase])}>
              {defaultRuntime.state.phase}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {RUNTIME_PHASE_LABEL[defaultRuntime.state.phase]}
          </p>
          {defaultRuntime.state.phase === "Active" && defaultRuntime.state.started_at && (
            <p className="text-xs text-muted-foreground">
              Started {new Date(defaultRuntime.state.started_at).toLocaleString()}
            </p>
          )}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {defaultRuntime.state.phase === "NotInstalled" && (
              <Button
                size="sm"
                variant="default"
                disabled={actionPending}
                onClick={() => onAction(defaultRuntime.runtime_id, "install")}
              >
                <Download className="mr-1 h-3 w-3" /> Install
              </Button>
            )}
            {defaultRuntime.state.phase === "Installed" && (
              <Button
                size="sm"
                variant="default"
                disabled={actionPending}
                onClick={() => onAction(defaultRuntime.runtime_id, "start")}
              >
                <PlayCircle className="mr-1 h-3 w-3" /> Start
              </Button>
            )}
            {defaultRuntime.state.phase === "Active" && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={actionPending}
                  onClick={() => onAction(defaultRuntime.runtime_id, "stop")}
                >
                  <PauseCircle className="mr-1 h-3 w-3" /> Stop
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={actionPending}
                  onClick={() => onAction(defaultRuntime.runtime_id, "update")}
                >
                  <RefreshCw className="mr-1 h-3 w-3" /> Update
                </Button>
              </>
            )}
            <Button
              size="sm"
              variant="destructive"
              disabled={actionPending || defaultRuntime.state.phase === "Active"}
              onClick={() => onAction(defaultRuntime.runtime_id, "remove")}
            >
              <Trash2 className="mr-1 h-3 w-3" /> Remove
            </Button>
          </div>
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-border bg-surface-2 p-3">
          <p className="text-sm font-medium text-muted-foreground">Not Available</p>
          <p className="text-xs text-muted-foreground mt-1">
            This model has no runtime descriptor yet. Migration is scheduled
            (OmniVoice: Phase 6; F5-TTS: Phase 4; XTTS / OpenVoice / Fish Audio: future).
          </p>
        </div>
      )}
    </div>
  )
}

function ModelRow({
  model,
  selected,
  onSelect,
}: {
  model: Model
  selected: boolean
  onSelect: (model: Model) => void
}) {
  const caps = model.capabilities

  return (
    <button
      type="button"
      onClick={() => onSelect(model)}
      className={cn(
        "w-full rounded-lg border bg-surface p-4 text-left transition-colors hover:bg-surface-2",
        selected ? "border-primary ring-1 ring-primary/30" : "border-border",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Cpu className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-card-title">{model.name}</h2>
            {model.is_default && <Badge className="rounded-md bg-primary/15 text-primary">Default</Badge>}
            <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-medium capitalize", statusClasses[model.status])}>
              {model.install_status.replace("_", " ")} / {model.activation_status}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {model.provider} · v{model.version} · {model.license_name ?? model.license?.code ?? "License unknown"}
          </p>
          <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{model.description}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <CapabilityBadge label="TTS" supported={caps.supports_tts} />
            <CapabilityBadge label="Clone" supported={caps.supports_voice_cloning} />
            <CapabilityBadge label="Design" supported={caps.supports_voice_design ?? false} />
            <CapabilityBadge label="Singing" supported={caps.supports_singing} />
          </div>
        </div>
      </div>
    </button>
  )
}

export default function ModelsPage() {
  // R9: The Models page renders a composed view from
  // useModelsWithRuntimes() — Catalog + Runtime Registry + State.
  // The catalog portion is always present; the runtime portion
  // augments the card when a RuntimeManager is attached and a
  // RuntimeDescriptor exists for the model.
  const { data: composedCards = [], isLoading, error } = useModelsWithRuntimes()
  const { data: legacyModels = [] } = useModels()  // legacy catalog (BUILTIN_MODELS) for backward compat
  const lifecycle = useModelLifecycleAction()
  const runtimeLifecycle = useRuntimeLifecycleAction()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<ModelFilter>("all")
  const [query, setQuery] = useState("")

  // R9: derive the legacy Model[] from the composed view so the
  // rest of the page can keep using the existing render path.
  // Each composed card's `model` is the catalog ModelDescriptor;
  // we map it to the legacy Model shape for the existing UI.
  const models = useMemo<Model[]>(
    () =>
      composedCards.map((c) => {
        const m = c.model as unknown as Model
        // Override the legacy status with the runtime state
        // when a runtime exists.
        const defaultRuntime = c.runtimes.find((r) => r.runtime_id === c.default_runtime_id) ?? c.runtimes[0]
        if (defaultRuntime) {
          const phase = defaultRuntime.state.phase
          const isActive = phase === "Active"
          const isInstalled = phase !== "NotInstalled" && phase !== "Failed"
          return {
            ...m,
            install_status: isInstalled ? "installed" : "not_installed",
            activation_status: isActive ? "active" : "inactive",
            status: isActive ? "loaded" : isInstalled ? "available" : "inactive",
          } as Model
        }
        return m
      }),
    [composedCards],
  )

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
  const installedCount = models.filter(isInstalled).length
  const availableCount = models.length - installedCount

  const runAction = (id: string, action: ModelLifecycleAction) => {
    lifecycle.mutate({ id, action })
  }

  const contextPanel = selected ? (
    <div className="flex flex-col gap-6 p-6">
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-section-title">{selected.name}</h2>
            <p className="text-caption">{selected.provider} · {selected.id}</p>
          </div>
          <span className={cn("rounded px-2 py-1 text-[11px] font-medium capitalize", statusClasses[selected.status])}>
            {selected.install_status.replace("_", " ")} / {selected.activation_status}
          </span>
        </div>
        <p className="text-sm text-muted-foreground">{selected.description}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <Metric icon={Server} label="Runtime" value={selected.runtime_requirements.runtime ?? "Unknown"} />
        <Metric icon={HardDrive} label="Memory" value={formatMemory(selected)} />
        <Metric icon={Cpu} label="GPU" value={selected.gpu_requirements.required ? "Required" : "Optional"} />
        <Metric icon={CheckCircle2} label="Edition" value={[selected.available_in_ce && "CE", selected.available_in_cloud && "Cloud"].filter(Boolean).join(" + ")} />
      </div>

      <RuntimeSection
        card={composedCards.find((c) => c.model.id === selected.id) ?? null}
        onAction={(runtimeId, action) => runtimeLifecycle.mutate({ id: runtimeId, action })}
        actionPending={runtimeLifecycle.isPending}
      />

      <div className="space-y-2">
        <p className="text-caption uppercase tracking-wide">Sources</p>
        <InfoLink label="Provider" href={selected.provider_url} fallback={selected.provider} />
        <InfoLink label="Repository" href={selected.repository_url} fallback="Unknown" />
        <InfoLink label="Model page" href={selected.homepage_url} fallback="Unknown" />
        <InfoLink label="License" href={selected.license_url} fallback={selected.license_name ?? "Unknown"} />
      </div>

      <div className="space-y-2">
        <p className="text-caption uppercase tracking-wide">Capabilities</p>
        <div className="flex flex-wrap gap-1.5">
          {capabilityLabels.map(([key, label]) => (
            <CapabilityBadge key={key} label={label} supported={!!selected.capabilities[key]} />
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-caption uppercase tracking-wide">Languages and tags</p>
        <InfoLine label="Languages" value={selected.supported_languages.length > 0 ? selected.supported_languages.join(", ") : metadataString(selected.provider_metadata?.languages_summary, "Unknown")} />
        <InfoLine label="Tags" value={selected.supported_tags.length > 0 ? selected.supported_tags.join(", ") : "None declared"} />
        <InfoLine label="Voice design" value={selected.supported_voice_design.length > 0 ? `${selected.supported_voice_design.length} attributes` : "Not supported"} />
        <InfoLine label="Memory source" value={selected.memory_requirements.source} />
        <InfoLine label="Edition basis" value={selected.edition_availability.basis} />
      </div>

      <div className="space-y-2 border-t border-border pt-4">
        <p className="text-caption uppercase tracking-wide">Lifecycle</p>
        <div className="grid grid-cols-2 gap-2">
          {!isInstalled(selected) ? (
            <ActionButton action="install" icon={Download} pending={lifecycle.isPending} onClick={() => runAction(selected.id, "install")} />
          ) : (
            <>
              <ActionButton action="update" icon={RefreshCw} pending={lifecycle.isPending} onClick={() => runAction(selected.id, "update")} />
              <ActionButton action="remove" icon={Trash2} pending={lifecycle.isPending} onClick={() => runAction(selected.id, "remove")} />
              <ActionButton action="activate" icon={PlayCircle} pending={lifecycle.isPending} disabled={selected.activation_status === "active"} onClick={() => runAction(selected.id, "activate")} />
              <ActionButton action="deactivate" icon={PauseCircle} pending={lifecycle.isPending} disabled={selected.activation_status === "inactive"} onClick={() => runAction(selected.id, "deactivate")} />
            </>
          )}
        </div>
        {lifecycle.error && <p className="text-xs text-error">{lifecycle.error.message}</p>}
      </div>
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

function Metric({ icon: Icon, label, value }: { icon: typeof Cpu; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center gap-2 text-caption">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="mt-1 text-sm font-medium">{value || "Not specified"}</p>
    </div>
  )
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="max-w-[220px] text-right text-foreground">{value}</span>
    </div>
  )
}

function InfoLink({ label, href, fallback }: { label: string; href: string | null; fallback: string }) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="max-w-[220px] truncate text-right text-primary underline-offset-2 hover:underline"
          title={href}
        >
          {fallback === "Unknown" ? href : fallback}
        </a>
      ) : (
        <span className="max-w-[220px] text-right text-foreground">{fallback}</span>
      )}
    </div>
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

function ActionButton({
  action,
  icon: Icon,
  pending,
  disabled,
  onClick,
}: {
  action: ModelLifecycleAction
  icon: typeof Cpu
  pending: boolean
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <Button
      type="button"
      variant={action === "remove" ? "outline" : "secondary"}
      size="sm"
      className={cn("gap-2", action === "remove" && "text-error hover:text-error")}
      disabled={disabled || pending}
      onClick={onClick}
    >
      {pending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Icon className="h-3.5 w-3.5" />}
      {lifecycleLabel(action)}
    </Button>
  )
}
