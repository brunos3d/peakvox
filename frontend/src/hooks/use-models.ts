import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "@/store/use-store";
import {
  activateModel,
  deactivateModel,
  fetchModel,
  fetchModels,
  fetchModelTags,
  installModel,
  removeModel,
  updateModel,
} from "@/lib/api";
import type { ModelTagMetadata, TemporaryVoice, VoiceProfile } from "@/types";
import { FALLBACK_TAGS } from "@/editor/tags";

export type ModelLifecycleAction = "install" | "update" | "remove" | "activate" | "deactivate";
type ModelLifecycleResult =
  | { id: string; status: string }
  | { id: string; removed: boolean };

const lifecycleFns: Record<ModelLifecycleAction, (id: string) => Promise<ModelLifecycleResult>> = {
  install: installModel,
  update: updateModel,
  remove: removeModel,
  activate: activateModel,
  deactivate: deactivateModel,
};

export function useModels() {
  return useQuery({
    queryKey: ["models"],
    queryFn: fetchModels,
    staleTime: 10_000,
    refetchInterval: 15_000,
  });
}

export function useModel(id: string | null) {
  return useQuery({
    queryKey: ["model", id],
    queryFn: () => fetchModel(id!),
    enabled: !!id,
  });
}

export function useModelTags(modelId: string | null) {
  return useQuery({
    queryKey: ["model-tags", modelId],
    queryFn: async (): Promise<ModelTagMetadata[]> => {
      if (!modelId) return [];
      const data = await fetchModelTags(modelId);
      return data.tags;
    },
    enabled: !!modelId,
    staleTime: 120_000,
    placeholderData: FALLBACK_TAGS,
  });
}

export function useModelLifecycleAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: ModelLifecycleAction }) =>
      lifecycleFns[action](id),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: ["model", variables.id] });
      queryClient.invalidateQueries({ queryKey: ["model-status"] });
    },
  });
}

/** Returns the recommended model ID for a given voice following the selection
 *  priority: primary_model_id → recommended_model_id → first compatible_models → null.
 *  Only returns IDs that exist in the registry. */
export function useRecommendedModelId(voice: VoiceProfile | TemporaryVoice | null): string | null {
  const { data: models } = useModels();

  if (!voice || !models) return null;

  if (voice.primary_model_id && models.some((m) => m.id === voice.primary_model_id)) {
    return voice.primary_model_id;
  }
  if (voice.recommended_model_id && models.some((m) => m.id === voice.recommended_model_id)) {
    return voice.recommended_model_id;
  }
  if (voice.compatible_models && voice.compatible_models.length > 0) {
    const first = voice.compatible_models[0];
    if (models.some((m) => m.id === first)) {
      return first;
    }
  }
  return null;
}

export function useActiveModel() {
  const selectedModelId = useAppStore((s) => s.selectedModelId);
  const { data: models } = useModels();

  const activeId =
    selectedModelId ??
    models?.find((m) => m.activation_status === "active")?.id ??
    models?.find((m) => m.is_default)?.id ??
    null;
  const activeModel = models?.find((m) => m.id === activeId) ?? null;

  const { data: tags } = useModelTags(activeId);

  return {
    activeModel,
    activeModelId: activeId,
    tags: tags ?? FALLBACK_TAGS,
    isLoading: false,
  };
}
