"use client";

import { Cpu, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/use-store";
import { useModels } from "@/hooks/use-models";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function CapabilityBadge({ label, supported }: { label: string; supported: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium",
        supported
          ? "bg-primary/10 text-primary"
          : "bg-muted text-muted-foreground line-through",
      )}
    >
      {supported ? "✓" : "✗"} {label}
    </span>
  );
}

export function ModelSelector() {
  const selectedModelId = useAppStore((s) => s.selectedModelId);
  const setSelectedModelId = useAppStore((s) => s.setSelectedModelId);
  const { data: models, isLoading, error } = useModels();

  if (isLoading) {
    return (
      <div className="flex h-10 items-center rounded-md border border-border bg-surface px-3 text-sm text-muted-foreground">
        Loading models…
      </div>
    );
  }

  if (error || !models?.length) {
    return (
      <div className="flex h-10 items-center rounded-md border border-border bg-surface px-3 text-sm text-muted-foreground">
        OmniVoice Base
      </div>
    );
  }

  const active = selectedModelId
    ? models.find((m) => m.id === selectedModelId)
    : models.find((m) => m.is_default);

  return (
    <Select
      value={active?.id ?? models[0].id}
      onValueChange={(val) => setSelectedModelId(val === models.find((m) => m.is_default)?.id ? null : val)}
    >
      <SelectTrigger className="gap-2">
        <Cpu className="h-4 w-4 shrink-0 text-primary" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {models
          .filter((m) => m.status !== "disabled")
          .map((model) => {
            const isActive = model.id === active?.id;
            return (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex flex-col gap-1.5 py-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{model.name}</span>
                    {model.is_default && (
                      <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                        Default
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-1">
                    {model.description}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    <CapabilityBadge
                      label="Voice cloning"
                      supported={model.capabilities.supports_voice_cloning}
                    />
                    <CapabilityBadge
                      label="Emotions"
                      supported={model.capabilities.supports_emotions}
                    />
                    <CapabilityBadge
                      label="Singing"
                      supported={model.capabilities.supports_singing}
                    />
                  </div>
                </div>
              </SelectItem>
            );
          })}
      </SelectContent>
    </Select>
  );
}
