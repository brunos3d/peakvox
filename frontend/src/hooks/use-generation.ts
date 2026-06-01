"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  submitGeneration,
  fetchJob,
  fetchVoices,
  fetchModelStatus,
} from "@/lib/api";
import type {
  GenerationRequest,
  JobResponse,
  VoiceProfile,
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

  return useMutation({
    mutationFn: (data: GenerationRequest) => submitGeneration(data),
    onSuccess: (result) => {
      setActiveJob(result.job_id, "pending");
      queryClient.invalidateQueries({ queryKey: ["voices"] });
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
        setTimeout(() => setActiveJob(null), 3000); // Clear active job after 3 seconds
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
