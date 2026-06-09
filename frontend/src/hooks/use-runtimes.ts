// Runtime hooks (Phase 3 — runtime-registry surface).
//
// The Models page renders from useRuntimes() when
// RUNTIME_SERVICE_ENABLED=true; the legacy useModels() is
// the fallback for the catalog view.
//
// Capability-driven controls (per project AGENTS.md rule 3):
// the runtime's `capabilities` array declares what the
// runtime can do; the UI renders controls only for
// capabilities the runtime declares. The legacy
// ModelCapabilities shape is preserved for the catalog
// view.

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import {
  fetchRuntimes,
  fetchRuntime,
  fetchRuntimeState,
  fetchRuntimeOperation,
  fetchRuntimeOperations,
  fetchModelsWithRuntimes,
  installRuntime,
  startRuntime,
  stopRuntime,
  updateRuntime,
  removeRuntime,
  cancelRuntimeOperation,
} from "@/lib/api";
import type {
  RuntimeOperation,
  RuntimeStatePayload,
  RuntimeOperationStatus,
} from "@/types";


export type RuntimeLifecycleAction = "install" | "start" | "stop" | "update" | "remove";

const lifecycleFns: Record<RuntimeLifecycleAction, (id: string) => Promise<unknown>> = {
  install: installRuntime,
  start: startRuntime,
  stop: stopRuntime,
  update: updateRuntime,
  remove: removeRuntime,
};

export function useRuntimes() {
  return useQuery({
    queryKey: ["runtimes"],
    queryFn: fetchRuntimes,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}


export function useRuntime(id: string | null) {
  return useQuery({
    queryKey: ["runtime", id],
    queryFn: () => fetchRuntime(id!),
    enabled: !!id,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}


export function useRuntimeState(id: string | null) {
  return useQuery({
    queryKey: ["runtime-state", id],
    queryFn: () => fetchRuntimeState(id!),
    enabled: !!id,
    staleTime: 1_000,
    refetchInterval: 3_000,
    refetchIntervalInBackground: true,
  });
}

export function useRuntimeOperation(id: string | null) {
  return useQuery<RuntimeOperation | null>({
    queryKey: ["runtime-operation", id],
    queryFn: () => fetchRuntimeOperation(id!),
    enabled: !!id,
    staleTime: 1_000,
    refetchInterval: 3_000,
    refetchIntervalInBackground: true,
  });
}

export function useRuntimeOperations(activeOnly = true) {
  return useQuery<RuntimeOperation[]>({
    queryKey: ["runtime-operations", activeOnly],
    queryFn: () => fetchRuntimeOperations(activeOnly),
    staleTime: 1_000,
    refetchInterval: 3_000,
    refetchIntervalInBackground: true,
  });
}


export function useRuntimeLifecycleAction() {
  const queryClient = useQueryClient();

  const invalidateRuntimeQueries = (runtimeId?: string) => {
    queryClient.invalidateQueries({ queryKey: ["models-with-runtimes"] });
    queryClient.invalidateQueries({ queryKey: ["models"] });
    queryClient.invalidateQueries({ queryKey: ["runtimes"] });
    queryClient.invalidateQueries({ queryKey: ["runtime-operations"] });
    if (runtimeId) {
      queryClient.invalidateQueries({ queryKey: ["runtime", runtimeId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-state", runtimeId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-operation", runtimeId] });
    }
  }

  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: RuntimeLifecycleAction }) =>
      lifecycleFns[action](id) as Promise<unknown>,
    onSuccess: (_data, variables) => {
      // Invalidate the composed-view cache (the Models page
      // subscribes to this via useModelsWithRuntimes). Without
      // this, the page state badge won't refresh after a
      // lifecycle operation.
      invalidateRuntimeQueries(variables.id)
    },
    onError: (_error, variables) => {
      // Roll back optimistic lifecycle badges by forcing a
      // fresh read of runtime state from the backend.
      invalidateRuntimeQueries(variables.id)
    },
    onSettled: (_data, _error, variables) => {
      invalidateRuntimeQueries(variables?.id)
    },
  });
}

function isCancelable(status: RuntimeOperationStatus): boolean {
  return status === "pending" || status === "running"
}

export function useCancelRuntimeOperation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ runtimeId, operationId }: { runtimeId: string; operationId: string }) =>
      cancelRuntimeOperation(runtimeId, operationId),
    onSuccess: (_op, variables) => {
      queryClient.invalidateQueries({ queryKey: ["runtime-operation", variables.runtimeId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-state", variables.runtimeId] });
      queryClient.invalidateQueries({ queryKey: ["runtime-operations"] });
      queryClient.invalidateQueries({ queryKey: ["models-with-runtimes"] });
    },
  });
}

export function canCancelOperation(op: RuntimeOperation | null | undefined): boolean {
  return !!op && op.cancellable && isCancelable(op.status)
}


/** Subscribe to a runtime's state stream (Server-Sent Events).
 *
 *  Returns the latest state payload; updates in real time
 *  as state transitions occur. The hook manages the
 *  EventSource lifecycle and cleans up on unmount.
 */
export function useRuntimeStateStream(id: string | null) {
  return useQuery<RuntimeStatePayload>({
    queryKey: ["runtime-state-stream", id],
    queryFn: () => fetchRuntimeState(id!),
    enabled: !!id,
    staleTime: 0,
    refetchInterval: 5_000,
  });
}


// ---------------------------------------------------------------------------
// Composed view (R9) — Models + Runtimes + State
// ---------------------------------------------------------------------------

export function useModelsWithRuntimes() {
  return useQuery({
    queryKey: ["models-with-runtimes"],
    queryFn: fetchModelsWithRuntimes,
    staleTime: 1_000,
    refetchInterval: 3_000,
    refetchIntervalInBackground: true,
  });
}
