"use client";

import { Loader2, Cpu, Mic, Sparkles, Music, Globe, Palette, Repeat } from "lucide-react";
import { cn } from "@/lib/utils";
import { useActiveModel } from "@/hooks/use-models";
import { Badge } from "@/components/ui/badge";

const statusColors: Record<string, string> = {
  available: "bg-muted text-muted-foreground",
  loading: "bg-warning/15 text-warning",
  loaded: "bg-success/15 text-success",
  error: "bg-error/15 text-error",
  disabled: "bg-muted text-muted-foreground",
};

interface CapabilityRowProps {
  icon: typeof Cpu;
  label: string;
  supported: boolean;
}

function CapabilityRow({ icon: Icon, label, supported }: CapabilityRowProps) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon className={cn("h-3.5 w-3.5", supported ? "text-primary" : "text-muted-foreground/50")} />
      <span className={supported ? "text-foreground" : "text-muted-foreground"}>
        {label}
      </span>
      {supported && <span className="ml-auto text-success">✓</span>}
    </div>
  );
}

export function ModelInfoCard() {
  const { activeModel, tags, isLoading } = useActiveModel();

  if (isLoading || !activeModel) {
    return (
      <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        Loading model info…
      </div>
    );
  }

  const caps = activeModel.capabilities;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{activeModel.name}</span>
        <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", statusColors[activeModel.status])}>
          {activeModel.status}
        </span>
      </div>

      <p className="text-xs text-muted-foreground">{activeModel.description}</p>

      <div className="space-y-1.5">
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          Capabilities
        </p>
        <CapabilityRow icon={Mic} label="Voice cloning" supported={caps.supports_voice_cloning} />
        <CapabilityRow icon={Sparkles} label="Emotion tags" supported={caps.supports_emotion_tags ?? caps.supports_emotions} />
        <CapabilityRow icon={Music} label="Singing" supported={caps.supports_singing} />
        {caps.supports_voice_design && (
          <CapabilityRow icon={Palette} label="Voice design" supported={true} />
        )}
        {caps.supports_voice_conversion && (
          <CapabilityRow icon={Repeat} label="Voice conversion" supported={true} />
        )}
        <CapabilityRow icon={Globe} label="Public API" supported={caps.supports_api} />
      </div>

      {tags.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Supported tags ({tags.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <Badge
                key={tag.id}
                variant="secondary"
                className="gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-normal"
                title={tag.description}
              >
                <span>{tag.emoji}</span>
                <span>{tag.label}</span>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {(activeModel.provider || activeModel.license?.code) && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border pt-2 text-[10px] text-muted-foreground">
          <span>Provider: {activeModel.provider}</span>
          {activeModel.license?.code && (
            <span>
              License:{" "}
              {activeModel.license.url ? (
                <a
                  href={activeModel.license.url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline hover:text-foreground"
                >
                  {activeModel.license.code}
                </a>
              ) : (
                activeModel.license.code
              )}
            </span>
          )}
          {activeModel.requirements?.gpu_required && <span>GPU required</span>}
        </div>
      )}
    </div>
  );
}
