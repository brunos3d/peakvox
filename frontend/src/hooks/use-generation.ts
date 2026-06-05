"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  submitGeneration,
  fetchJob,
  fetchVoices,
  fetchVoicesPage,
  setVoiceFavorite,
  fetchModelStatus,
} from "@/lib/api";
import type {
  GenerationRequest,
  JobResponse,
  VoiceProfile,
  VoiceListPage,
  VoiceScope,
  VoiceQueryFilters,
  ModelStatus,
} from "@/types";
import { useAppStore } from "@/store/use-store";

export function useVoices() {
  const setVoices = useAppStore((s) => s.setVoices);

  return useQuery<VoiceProfile[]>({
    queryKey: ["voices"],
    queryFn: async () => {
      const data = await fetchVoices();
      setVoices(data);
      return data;
    },
    refetchInterval: 10000,
  });
}

/** Paginated/filtered/searchable listing that drives the Voice Library. */
export function useVoicesPage(
  scope: VoiceScope,
  search: string,
  filters: VoiceQueryFilters,
) {
  return useInfiniteQuery<VoiceListPage>({
    queryKey: ["voices-page", scope, search, filters],
    queryFn: ({ pageParam }) =>
      fetchVoicesPage({
        scope,
        search,
        filters,
        cursor: pageParam as string | null,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    enabled: scope === "mine" || scope === "recent" || scope === "preset",
  });
}

export function useToggleFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, value }: { id: string; value: boolean }) =>
      setVoiceFavorite(id, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voices-page"] });
      queryClient.invalidateQueries({ queryKey: ["voices"] });
    },
  });
}

export function useModelStatus() {
  return useQuery<ModelStatus>({
    queryKey: ["model-status"],
    queryFn: fetchModelStatus,
    refetchInterval: 5000,
  });
}

export function useSubmitGeneration() {
  const queryClient = useQueryClient();
  const setActiveJob = useAppStore((s) => s.setActiveJob);
  const setLastRequest = useAppStore((s) => s.setLastRequest);

  return useMutation({
    mutationFn: (data: GenerationRequest) => submitGeneration(data),
    onMutate: (data) => {
      setLastRequest(data);
    },
    onSuccess: (result) => {
      setActiveJob(result.job_id, "pending");
      queryClient.invalidateQueries({ queryKey: ["voices"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useJobStatus(jobId: string | null) {
  const setActiveJobStatus = useAppStore((s) => s.setActiveJobStatus);
  const setActiveJob = useAppStore((s) => s.setActiveJob);

  return useQuery<JobResponse>({
    queryKey: ["job", jobId],
    queryFn: async () => {
      const data = await fetchJob(jobId!);
      setActiveJobStatus(data.status);
      if (data.status === "completed" || data.status === "failed") {
        // Capture the job ID at the time the query resolves. Only clear the
        // active-job state if this job is STILL the active one when the timer
        // fires. Without this guard, starting a new generation within the
        // 3-second window caused the old timer to wipe the new job's ID from
        // the store, stopping its poll and hiding its result.
        const completedJobId = jobId;
        setTimeout(() => {
          if (useAppStore.getState().activeJobId === completedJobId) {
            setActiveJob(null);
          }
        }, 3000);
      }
      return data;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 1000;
      return data.status === "pending" || data.status === "processing"
        ? 1000
        : false;
    },
  });
}
