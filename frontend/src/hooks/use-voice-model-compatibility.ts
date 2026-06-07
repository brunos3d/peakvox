"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchVoiceVariants } from "@/lib/api"
import { useModels } from "@/hooks/use-models"
import type { AnyVoice, VoiceModelCompatibility, RealizationState, VariantListItem } from "@/types"

/**
 * Pure function: compute three-state compatibility from raw data sources.
 * No side effects, no hooks — testable in isolation.
 */
export function computeVoiceModelCompatibility(
  compatibleModels: string[],
  variants: VariantListItem[],
  modelIds: string[],
): VoiceModelCompatibility[] {
  const variantMap = new Map(variants.map((v) => [v.model_id, v]))

  return modelIds.map((modelId) => {
    const isCompatible = compatibleModels.includes(modelId)
    const variant = variantMap.get(modelId)
    const isReady = variant?.status === "ready"

    let state: RealizationState
    if (isCompatible && isReady) {
      state = "ready"
    } else if (isCompatible) {
      state = "buildable"
    } else {
      state = "incompatible"
    }

    return {
      modelId,
      state,
      variantStatus: variant?.status,
    }
  })
}

/**
 * Hook: merges compatible_models with variant state to produce three-state
 * compatibility for a single voice against all active models.
 *
 * Single source of truth — no component should perform its own compatibility
 * calculation.
 */
export function useVoiceModelCompatibility(
  voice: AnyVoice | null,
): {
  loading: boolean
  compat: VoiceModelCompatibility[]
  getState: (modelId: string) => RealizationState
} {
  const { data: models } = useModels()

  const publicVoiceId =
    voice && "public_voice_id" in voice ? voice.public_voice_id : null
  const compatibleModels = voice?.compatible_models ?? []

  const variantsQ = useQuery({
    queryKey: ["voice-variants", publicVoiceId],
    queryFn: () => fetchVoiceVariants(publicVoiceId!),
    enabled: !!publicVoiceId,
  })

  const modelIds = (models ?? [])
    .filter((m) => m.activation_status === "active")
    .map((m) => m.id)

  const variants = variantsQ.data ?? []
  const compat = computeVoiceModelCompatibility(compatibleModels, variants, modelIds)

  const compatMap = new Map(compat.map((c) => [c.modelId, c]))
  const getState = (modelId: string): RealizationState =>
    compatMap.get(modelId)?.state ?? "incompatible"

  return {
    loading: variantsQ.isLoading,
    compat,
    getState,
  }
}
