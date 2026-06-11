import { Container, HardDrive, Network, Server } from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { OperationsRow } from "@/components/models/OperationsRow"
import { NotMigratedEmptyState } from "@/components/models/NotMigratedEmptyState"
import { VariantsSection } from "@/components/models/VariantsSection"
import type {
  ComposedRuntimeDescriptor,
  ModelWithRuntimesCard,
  RuntimePhase,
  RuntimeStatePayload,
} from "@/types"
import type { RuntimeLifecycleAction } from "@/hooks/use-runtimes"

const RUNTIME_PHASE_LABEL: Record<RuntimePhase, string> = {
  notInstalled: "Not Installed",
  installing: "Installing runtime...",
  pulling: "Pulling image...",
  installed: "Installed (image present, container stopped)",
  starting: "Starting container...",
  active: "Active (container running, /health 200)",
  stopping: "Stopping...",
  stopped: "Stopped",
  failed: "Failed",
  updating: "Updating...",
  removing: "Removing runtime...",
}

const RUNTIME_PHASE_BADGE: Record<RuntimePhase, string> = {
  notInstalled: "bg-muted text-muted-foreground",
  installing: "bg-warning/15 text-warning",
  pulling: "bg-warning/15 text-warning",
  installed: "bg-muted text-muted-foreground",
  starting: "bg-warning/15 text-warning",
  active: "bg-success/15 text-success",
  stopping: "bg-muted text-muted-foreground",
  stopped: "bg-muted text-muted-foreground",
  failed: "bg-error/15 text-error",
  updating: "bg-warning/15 text-warning",
  removing: "bg-warning/15 text-warning",
}

function formatImageSize(sizeMb: number | null | undefined): string {
  if (sizeMb == null || Number.isNaN(sizeMb)) return "n/a"
  if (sizeMb >= 1024) return `${(sizeMb / 1024).toFixed(1)} GB`
  return `${sizeMb.toFixed(0)} MB`
}

function InfoLine({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("max-w-[260px] text-right break-all text-foreground", mono && "font-mono text-xs")}>
        {value}
      </span>
    </div>
  )
}

function CapabilityChip({ name }: { name: string }) {
  return (
    <Badge variant="secondary" className="rounded-md bg-primary/10 text-primary hover:bg-primary/15">
      {name}
    </Badge>
  )
}

// ---------------------------------------------------------------------------
// Runtime identity + state header (T13.4: rendered at the TOP of
// the Runtime Section, immediately above the OperationsRow so the
// action buttons are visible without scrolling).
// ---------------------------------------------------------------------------
function RuntimeHeader({
  descriptor,
  state,
}: {
  descriptor: ComposedRuntimeDescriptor
  state: RuntimeStatePayload
}) {
  const { spec, metadata } = descriptor
  return (
    <div className="rounded-md border border-border bg-surface-2 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1 space-y-0.5">
          <p className="text-sm font-mono break-all">
            {spec.image.repository}:{spec.image.tag}
          </p>
          {spec.image.digest && (
            <p className="text-[10px] text-muted-foreground font-mono break-all">@{spec.image.digest}</p>
          )}
          {metadata.name && metadata.name !== `${spec.image.repository}:${spec.image.tag}` && (
            <p className="text-xs text-muted-foreground">{metadata.name}</p>
          )}
          <p className="text-[10px] text-muted-foreground">
            v{metadata.version} · provider={metadata.provider}
          </p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded px-2 py-1 text-[10px] font-medium",
            RUNTIME_PHASE_BADGE[state.phase],
          )}
        >
          {state.phase}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        {RUNTIME_PHASE_LABEL[state.phase]}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Runtime state details (endpoint, started_at, health). Rendered
// below the OperationsRow so the user can see the current
// state details AFTER the actions they may want to take.
// ---------------------------------------------------------------------------
function RuntimeStateDetails({ state }: { state: RuntimeStatePayload }) {
  if (
    !state.endpoint &&
    !(state.phase === "active" && state.started_at) &&
    !state.last_health_at &&
    !state.health_state
  ) {
    return null
  }
  return (
    <div className="rounded-md border border-border bg-surface-2 p-3 space-y-2">
      {state.endpoint && <InfoLine label="Endpoint" value={state.endpoint} mono />}
      {state.phase === "active" && state.started_at && (
        <InfoLine label="Started" value={new Date(state.started_at).toLocaleString()} />
      )}
      {state.last_health_at && (
        <InfoLine label="Last health" value={new Date(state.last_health_at).toLocaleString()} />
      )}
      {state.health_state && <InfoLine label="Health" value={state.health_state} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Descriptor details (service contract, requirements, capabilities).
// All values are derived from the descriptor; the UI never
// hardcodes per-runtime metadata (T13.3).
// ---------------------------------------------------------------------------
function RuntimeDescriptorDetails({ descriptor }: { descriptor: ComposedRuntimeDescriptor }) {
  const { spec } = descriptor
  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-surface-2 p-3 space-y-2">
        <p className="text-caption uppercase tracking-wide flex items-center gap-1.5">
          <Network className="h-3 w-3" /> Service
        </p>
        <InfoLine label="Protocol" value={spec.service.protocol} />
        <InfoLine label="Port" value={String(spec.service.port)} />
        <InfoLine label="Health" value={spec.service.health_path} mono />
        <InfoLine label="Ready" value={spec.service.readiness_path} mono />
        <InfoLine label="Generate" value={spec.service.generate_path} mono />
        <InfoLine label="Build" value={spec.service.build_path} mono />
        <InfoLine label="Metadata" value={spec.service.metadata_path} mono />
      </div>

      <div className="rounded-md border border-border bg-surface-2 p-3 space-y-2">
        <p className="text-caption uppercase tracking-wide flex items-center gap-1.5">
          <HardDrive className="h-3 w-3" /> Requirements
        </p>
        <InfoLine label="Image size" value={formatImageSize(spec.image.image_size_mb)} />
        <InfoLine label="GPU" value={spec.requirements.gpu} />
        <InfoLine
          label="Min VRAM"
          value={spec.requirements.min_vram_gb == null ? "n/a" : `${spec.requirements.min_vram_gb} GB`}
        />
        <InfoLine
          label="CPU cores"
          value={spec.requirements.cpu_cores == null ? "n/a" : String(spec.requirements.cpu_cores)}
        />
        <InfoLine
          label="Memory"
          value={spec.requirements.memory_gb == null ? "n/a" : `${spec.requirements.memory_gb} GB`}
        />
        <InfoLine label="Edition" value={spec.requirements.edition.join(", ")} />
        <InfoLine
          label="Install source"
          value={spec.build ? "Download image (fallback to platform build)" : "Download image"}
        />
        {spec.build && (
          <InfoLine
            label="Build source"
            value={`${spec.build.build_context}/${spec.build.dockerfile}`}
            mono
          />
        )}
      </div>

      <div className="rounded-md border border-border bg-surface-2 p-3 space-y-2">
        <p className="text-caption uppercase tracking-wide flex items-center gap-1.5">
          <Container className="h-3 w-3" /> Capabilities
        </p>
        {spec.capabilities.length === 0 ? (
          <p className="text-xs text-muted-foreground">None declared</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {spec.capabilities.map((c) => (
              <CapabilityChip key={c} name={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function RuntimeSection({
  card,
  onAction,
  actionPending,
  onCancel,
  canCancel,
}: {
  card: ModelWithRuntimesCard | null | undefined
  onAction: (runtimeId: string, action: RuntimeLifecycleAction) => void
  actionPending: boolean
  onCancel?: (runtimeId: string, operationId: string) => void
  canCancel?: (runtimeId: string) => boolean
}) {
  if (!card) return null
  const defaultRuntime = card.runtimes.find((r) => r.runtime_id === card.default_runtime_id) ?? card.runtimes[0]

  return (
    <div className="space-y-3">
      <p className="text-caption uppercase tracking-wide flex items-center gap-1.5">
        <Server className="h-3 w-3" /> Runtime
      </p>
      {defaultRuntime && defaultRuntime.descriptor ? (
        // T13.4: OperationsRow is rendered at the TOP of the
        // runtime section, immediately after the identity
        // header. The user and audits can see the action
        // buttons without scrolling.
        <div className="space-y-3">
          <RuntimeHeader descriptor={defaultRuntime.descriptor} state={defaultRuntime.state} />
          <OperationsRow
            phase={defaultRuntime.state.phase}
            pending={actionPending}
            operation={defaultRuntime.state.operation}
            canCancel={
              !!defaultRuntime.state.operation &&
              !!onCancel &&
              !!canCancel?.(defaultRuntime.runtime_id)
            }
            onCancel={() => {
              const operation = defaultRuntime.state.operation
              if (operation && onCancel) {
                onCancel(defaultRuntime.runtime_id, operation.id)
              }
            }}
            onAction={(action) => onAction(defaultRuntime.runtime_id, action)}
          />
          {defaultRuntime.state.operation?.status === "failed" && (
            <p className="text-xs text-error">
              {defaultRuntime.state.operation.error || defaultRuntime.state.operation.message}
            </p>
          )}
          <RuntimeStateDetails state={defaultRuntime.state} />
          <VariantsSection
            runtimeId={defaultRuntime.runtime_id}
            variants={defaultRuntime.variants}
          />
          <RuntimeDescriptorDetails descriptor={defaultRuntime.descriptor} />
        </div>
      ) : (
        <NotMigratedEmptyState modelId={card.model.id as string} />
      )}
    </div>
  )
}
