"use client";

import { Cpu, Sparkles, Mic, Music } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Model } from "@/types";

interface ModelCardProps {
  model: Model;
  selected?: boolean;
  onSelect: (model: Model) => void;
}

function CapabilityChip({ label, supported }: { label: string; supported: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
        supported
          ? "bg-primary/10 text-primary"
          : "bg-muted text-muted-foreground line-through",
      )}
    >
      {supported ? "✓" : "✗"} {label}
    </span>
  );
}

export function ModelCard({ model, selected, onSelect }: ModelCardProps) {
  const caps = model.capabilities;

  return (
    <div
      onClick={() => onSelect(model)}
      className={cn(
        "flex flex-col gap-3 rounded-xl border bg-surface p-4 cursor-pointer transition-all hover:bg-surface-2",
        selected
          ? "border-primary ring-1 ring-primary/30"
          : "border-border hover:border-border",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Cpu className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-card-title truncate">{model.name}</p>
            {model.is_default && (
              <span className="shrink-0 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                Default
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
            {model.description}
          </p>
          <div className="mt-2 flex flex-wrap gap-1">
            <CapabilityChip label="Voice cloning" supported={caps.supports_voice_cloning} />
            <CapabilityChip label="Emotions" supported={caps.supports_emotions} />
            <CapabilityChip label="Singing" supported={caps.supports_singing} />
          </div>
        </div>
      </div>
    </div>
  );
}
