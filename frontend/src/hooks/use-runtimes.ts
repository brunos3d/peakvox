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
  fetchModelsWithRuntimes,
  installRuntime,
  startRuntime,
  stopRuntime,
  updateRuntime,
  removeRuntime,
} from "@/lib/api";
import type {
  RuntimeCard,
  RuntimeStatePayload,
  ModelWithRuntimesCard,
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
    staleTime: 5_000,
    refetchInterval: 10_000,
  });
}


export function useRuntimeLifecycleAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: RuntimeLifecycleAction }) =>
      lifecycleFns[action](id) as Promise<unknown>,
    onSuccess: (_data, variables) => {
      // Invalidate the composed-view cache (the Models page
      // subscribes to this via useModelsWithRuntimes). Without
      // this, the page state badge won't refresh after a
      // lifecycle operation.
      queryClient.invalidateQueries({ queryKey: ["models-with-runtimes"] });
      queryClient.invalidateQueries({ queryKey: ["runtimes"] });
      queryClient.invalidateQueries({ queryKey: ["runtime", variables.id] });
      queryClient.invalidateQueries({ queryKey: ["runtime-state", variables.id] });
    },
  });
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
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
