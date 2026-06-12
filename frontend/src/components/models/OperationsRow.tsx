import { useState } from "react"
import { Download, PauseCircle, PlayCircle, RefreshCw, Trash2, Loader2, ScrollText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { InstallLogsDialog } from "@/components/models/InstallLogsDialog"
import type { RuntimeOperation, RuntimePhase } from "@/types"
import type { RuntimeLifecycleAction } from "@/hooks/use-runtimes"

// Phases that run a docker build/pull whose terminal output the "Check Logs"
// dialog can show. Other pending phases (starting/stopping/removing) produce no
// image build output, so the button is hidden for them.
const BUILD_PHASES: ReadonlySet<RuntimePhase> = new Set<RuntimePhase>([
  "installing",
  "pulling",
  "updating",
])

type PendingPhase = "installing" | "pulling" | "starting" | "stopping" | "updating" | "removing"

const OPERATIONS_BY_PHASE: Record<RuntimePhase, RuntimeLifecycleAction[]> = {
  notInstalled: ["install"],
  installing: [],
  pulling: [],
  installed: ["start", "remove"],
  starting: [],
  active: ["stop", "update", "remove"],
  stopping: [],
  stopped: ["start", "remove"],
  failed: ["remove"],
  updating: [],
  removing: [],
}

const PENDING_LABELS: Record<PendingPhase, string> = {
  installing: "Installing runtime...",
  pulling: "Pulling image...",
  starting: "Starting container...",
  stopping: "Stopping container...",
  updating: "Updating image...",
  removing: "Removing runtime...",
}

const ACTION_ICON: Record<RuntimeLifecycleAction, typeof Download> = {
  install: Download,
  start: PlayCircle,
  stop: PauseCircle,
  update: RefreshCw,
  remove: Trash2,
}

const ACTION_VARIANT: Record<RuntimeLifecycleAction, "default" | "outline" | "destructive"> = {
  install: "default",
  start: "default",
  stop: "outline",
  update: "outline",
  remove: "destructive",
}

function isPendingPhase(phase: RuntimePhase): phase is PendingPhase {
  return (
    phase === "installing" ||
    phase === "pulling" ||
    phase === "starting" ||
    phase === "stopping" ||
    phase === "updating" ||
    phase === "removing"
  )
}

export function OperationsRow({
  phase,
  pending,
  onAction,
  operation,
  canCancel,
  onCancel,
  runtimeId,
  imageRef,
}: {
  phase: RuntimePhase
  pending: boolean
  onAction: (action: RuntimeLifecycleAction) => void
  operation?: RuntimeOperation | null
  canCancel?: boolean
  onCancel?: () => void
  runtimeId?: string
  imageRef?: string
}) {
  const [logsOpen, setLogsOpen] = useState(false)

  if (isPendingPhase(phase)) {
    const canShowLogs = !!runtimeId && BUILD_PHASES.has(phase)
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          {operation?.message || PENDING_LABELS[phase]}
          {typeof operation?.progress === "number" && (
            <span className="text-[10px]">({operation.progress}%)</span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {canCancel && onCancel && (
            <Button size="sm" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          {canShowLogs && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setLogsOpen(true)}
              className="gap-1"
            >
              <ScrollText className="h-3 w-3" />
              Check Logs
            </Button>
          )}
        </div>
        {runtimeId && (
          <InstallLogsDialog
            runtimeId={runtimeId}
            imageRef={imageRef}
            open={logsOpen}
            onOpenChange={setLogsOpen}
          />
        )}
      </div>
    )
  }

  const actions = OPERATIONS_BY_PHASE[phase]
  if (!actions || actions.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5 pt-1">
      {actions.map((action) => {
        const Icon = ACTION_ICON[action]
        const variant = ACTION_VARIANT[action]
        const isRemoveBlockedDuringActive = action === "remove" && phase === "active"
        return (
          <Button
            key={action}
            size="sm"
            variant={variant}
            disabled={pending || isRemoveBlockedDuringActive}
            onClick={() => onAction(action)}
            className={cn(action === "remove" && "gap-1")}
          >
            <Icon className="mr-1 h-3 w-3" />
            {action[0].toUpperCase() + action.slice(1)}
          </Button>
        )
      })}
    </div>
  )
}
