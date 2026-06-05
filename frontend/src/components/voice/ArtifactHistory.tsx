"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  CheckCircle2,
  Clock,
  History,
  RotateCcw,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  fetchArtifactVersions,
  rollbackVariant,
  fetchVoiceVariants,
} from "@/lib/api"
import type { ArtifactVersionResponse } from "@/types"

interface ArtifactHistoryProps {
  publicVoiceId: string
}

function formatFileSize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB"]
  let size = bytes
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit++
  }
  return `${size.toFixed(1)} ${units[unit]}`
}

export function ArtifactHistory({ publicVoiceId }: ArtifactHistoryProps) {
  const queryClient = useQueryClient()
  const [selectedModel, setSelectedModel] = useState<string | null>(null)

  const variantsQ = useQuery({
    queryKey: ["voice-variants", publicVoiceId],
    queryFn: () => fetchVoiceVariants(publicVoiceId),
  })

  const variantsWithVersions = (variantsQ.data ?? []).filter(
    (v) => (v.active_artifact_version ?? 0) > 0
  )

  const artifactsQ = useQuery({
    queryKey: ["artifact-versions", publicVoiceId, selectedModel],
    queryFn: () => fetchArtifactVersions(publicVoiceId, selectedModel!),
    enabled: !!selectedModel,
  })

  const rollbackMut = useMutation({
    mutationFn: (version: number) =>
      rollbackVariant(publicVoiceId, selectedModel!, version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["artifact-versions", publicVoiceId, selectedModel] })
      queryClient.invalidateQueries({ queryKey: ["voice-variants", publicVoiceId] })
    },
  })

  if (variantsWithVersions.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-surface p-6 text-center">
        <History className="mx-auto h-8 w-8 text-muted-foreground mb-3" />
        <p className="text-sm text-muted-foreground">
          No version history yet. Rebuild a variant to create artifact versions.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {variantsWithVersions.map((v) => (
          <Button
            key={v.model_id}
            variant={selectedModel === v.model_id ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedModel(v.model_id)}
            className="text-xs"
          >
            {v.model_name}
          </Button>
        ))}
      </div>

      {selectedModel && artifactsQ.data && (
        <div className="rounded-lg border border-border divide-y divide-border">
          {artifactsQ.data.map((av: ArtifactVersionResponse) => (
            <div key={av.version} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3 min-w-0">
                {av.is_active ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
                ) : (
                  <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />
                )}
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    v{av.version}
                    {av.is_active && (
                      <span className="ml-2 text-xs text-success font-normal">Active</span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {new Date(av.created_at).toLocaleString()}
                    {av.model_version && ` · ${av.model_version}`}
                    {av.size_bytes != null && ` · ${formatFileSize(av.size_bytes)}`}
                  </p>
                </div>
              </div>

              {!av.is_active && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs gap-1.5 shrink-0"
                  disabled={rollbackMut.isPending}
                  onClick={() => rollbackMut.mutate(av.version)}
                >
                  <RotateCcw className="h-3 w-3" />
                  Rollback
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      {selectedModel && !artifactsQ.data && !artifactsQ.isLoading && (
        <div className="flex items-center justify-center py-8">
          <p className="text-sm text-muted-foreground">No versions found for this model.</p>
        </div>
      )}

      {selectedModel && artifactsQ.isLoading && (
        <div className="flex items-center justify-center py-8">
          <Clock className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      )}
    </div>
  )
}
