"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Cpu, FileAudio, Info } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { OutputFormatSelector } from "@/components/generation/OutputFormatSelector"
import { fetchDeviceSettings, updateDeviceSettings } from "@/lib/api"
import { useActiveModel } from "@/hooks/use-models"
import { HuggingFaceSettingsCard } from "@/components/settings/HuggingFaceSettingsCard"

export function SettingsCard({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof Cpu
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <h3 className="text-card-title">{title}</h3>
          {description && <p className="text-caption mt-0.5">{description}</p>}
          <div className="mt-4">{children}</div>
        </div>
      </div>
    </div>
  )
}

export function SettingsPanel() {
  const queryClient = useQueryClient()
  const { data: device } = useQuery({ queryKey: ["device-settings"], queryFn: fetchDeviceSettings })
  const { activeModel } = useActiveModel()

  const mutation = useMutation({
    mutationFn: (useGpu: boolean) => updateDeviceSettings(useGpu),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["device-settings"] }),
  })

  return (
    <div className="space-y-5">
      <SettingsCard icon={Cpu} title="Compute device" description="Choose whether generation runs on the GPU.">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label className="text-sm">Use GPU (CUDA)</Label>
            <p className="text-caption">
              {device === undefined ? "Checking…" : device.cuda_available ? "GPU available" : "No GPU detected — running on CPU"}
            </p>
          </div>
          <Switch
            checked={!!device?.use_gpu}
            disabled={!device?.cuda_available || mutation.isPending}
            onCheckedChange={(v) => mutation.mutate(v)}
          />
        </div>
      </SettingsCard>

      <HuggingFaceSettingsCard />

      <SettingsCard icon={FileAudio} title="Output" description="Default format used for downloads.">
        <OutputFormatSelector />
      </SettingsCard>

      <SettingsCard icon={Info} title="About">
        <div className="divide-y divide-border text-sm">
          <div className="flex items-center justify-between py-2">
            <span className="text-muted-foreground">Model</span>
            <span className="text-foreground/90">{activeModel?.name ?? "—"}</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-muted-foreground">Model status</span>
            <span className="text-foreground/90">
              {activeModel?.activation_status === "active" ? "Ready" : activeModel ? "Offline" : "—"}
            </span>
          </div>
        </div>
      </SettingsCard>
    </div>
  )
}
