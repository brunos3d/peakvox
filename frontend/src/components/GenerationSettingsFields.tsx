"use client"

import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { DynamicSettingsForm } from "@/components/DynamicSettingsForm"
import type { VoiceGenerationDefaults, SettingsSchema } from "@/types"

interface GenerationSettingsFieldsProps {
  value: VoiceGenerationDefaults
  onChange: (next: VoiceGenerationDefaults) => void
  cudaAvailable?: boolean
  gpuLoading?: boolean
  settingsSchema?: SettingsSchema | null
}

function patch(
  current: VoiceGenerationDefaults,
  update: Partial<VoiceGenerationDefaults>,
): VoiceGenerationDefaults {
  return { ...current, ...update }
}

export function GenerationSettingsFields({
  value,
  onChange,
  cudaAvailable,
  gpuLoading,
  settingsSchema,
}: GenerationSettingsFieldsProps) {
  return (
    <div className="space-y-4">
      {settingsSchema ? (
        <DynamicSettingsForm
          schema={settingsSchema}
          values={value as unknown as Record<string, unknown>}
          onChange={(key, val) => onChange(patch(value, { [key]: val as never }))}
        />
      ) : (
        <>
          <div className="space-y-2">
            <div className="flex justify-between">
              <Label className="text-xs">Inference Steps</Label>
              <span className="text-xs text-muted-foreground">{value.num_step}</span>
            </div>
            <Slider
              value={[value.num_step]}
              onValueChange={([v]) => onChange(patch(value, { num_step: v }))}
              min={4}
              max={64}
              step={1}
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <Label className="text-xs">Guidance Scale</Label>
              <span className="text-xs text-muted-foreground">{value.guidance_scale.toFixed(1)}</span>
            </div>
            <Slider
              value={[value.guidance_scale]}
              onValueChange={([v]) => onChange(patch(value, { guidance_scale: v }))}
              min={0}
              max={4}
              step={0.1}
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <Label className="text-xs">Speed</Label>
              <span className="text-xs text-muted-foreground">
                {value.speed ? `${value.speed.toFixed(2)}x` : "Auto"}
              </span>
            </div>
            <Slider
              value={[value.speed ?? 1.0]}
              onValueChange={([v]) => onChange(patch(value, { speed: v === 1.0 ? null : v }))}
              min={0.5}
              max={1.5}
              step={0.05}
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <Label className="text-xs">Duration (seconds)</Label>
              <span className="text-xs text-muted-foreground">
                {value.duration ? `${value.duration}s` : "Auto"}
              </span>
            </div>
            <Input
              type="number"
              placeholder="Auto"
              min={1}
              max={120}
              value={value.duration ?? ""}
              onChange={(e) =>
                onChange(patch(value, { duration: e.target.value ? Number(e.target.value) : null }))
              }
              className="h-8 text-xs"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <Label className="text-xs">Time Shift</Label>
              <span className="text-xs text-muted-foreground">{value.t_shift.toFixed(2)}</span>
            </div>
            <Slider
              value={[value.t_shift]}
              onValueChange={([v]) => onChange(patch(value, { t_shift: v }))}
              min={0}
              max={1}
              step={0.01}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label className="text-xs">Denoise</Label>
            <Switch
              checked={value.denoise}
              onCheckedChange={(v) => onChange(patch(value, { denoise: v }))}
            />
          </div>
        </>
      )}

      <Separator className="my-2" />

      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label className="text-xs">Use GPU (CUDA)</Label>
          {cudaAvailable !== undefined && (
            <p className="text-[10px] text-muted-foreground">
              {gpuLoading ? "Checking…" : cudaAvailable ? "GPU available" : "No GPU detected"}
            </p>
          )}
        </div>
        <Switch
          checked={value.use_gpu}
          onCheckedChange={(v) => onChange(patch(value, { use_gpu: v }))}
          disabled={cudaAvailable !== undefined && !cudaAvailable}
        />
      </div>
    </div>
  )
}
