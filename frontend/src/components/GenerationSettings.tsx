"use client"

import { useState, useEffect } from "react"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { useAppStore } from "@/store/use-store"
import { fetchDeviceSettings, updateDeviceSettings } from "@/lib/api"
import { Loader2 } from "lucide-react"

export function GenerationSettings() {
  const settings = useAppStore((s) => s.generationSettings)
  const update = useAppStore((s) => s.updateGenerationSettings)
  const [useGpu, setUseGpu] = useState(true)
  const [cudaAvailable, setCudaAvailable] = useState(false)
  const [settingsLoading, setSettingsLoading] = useState(true)

  useEffect(() => {
    fetchDeviceSettings()
      .then((res) => {
        setUseGpu(res.use_gpu)
        setCudaAvailable(res.cuda_available)
      })
      .catch(() => {})
      .finally(() => setSettingsLoading(false))
  }, [])

  const handleGpuToggle = async (v: boolean) => {
    setUseGpu(v)
    try {
      await updateDeviceSettings(v)
    } catch {
      setUseGpu(!v)
    }
  }

  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="settings">
        <AccordionTrigger className="text-sm">Generation Settings</AccordionTrigger>
        <AccordionContent>
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label className="text-xs">Inference Steps</Label>
                <span className="text-xs text-muted-foreground">{settings.num_step}</span>
              </div>
              <Slider
                value={[settings.num_step]}
                onValueChange={([v]) => update({ num_step: v })}
                min={4}
                max={64}
                step={1}
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <Label className="text-xs">Guidance Scale</Label>
                <span className="text-xs text-muted-foreground">{settings.guidance_scale.toFixed(1)}</span>
              </div>
              <Slider
                value={[settings.guidance_scale]}
                onValueChange={([v]) => update({ guidance_scale: v })}
                min={0}
                max={4}
                step={0.1}
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <Label className="text-xs">Speed</Label>
                <span className="text-xs text-muted-foreground">
                  {settings.speed ? `${settings.speed.toFixed(2)}x` : "Auto"}
                </span>
              </div>
              <Slider
                value={[settings.speed ?? 1.0]}
                onValueChange={([v]) => update({ speed: v === 1.0 ? null : v })}
                min={0.5}
                max={1.5}
                step={0.05}
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <Label className="text-xs">Duration (seconds)</Label>
                <span className="text-xs text-muted-foreground">
                  {settings.duration ? `${settings.duration}s` : "Auto"}
                </span>
              </div>
              <div className="flex gap-2">
                <Input
                  type="number"
                  placeholder="Auto"
                  min={1}
                  max={120}
                  value={settings.duration ?? ""}
                  onChange={(e) => update({ duration: e.target.value ? Number(e.target.value) : null })}
                  className="h-8 text-xs"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <Label className="text-xs">Time Shift</Label>
                <span className="text-xs text-muted-foreground">{settings.t_shift.toFixed(2)}</span>
              </div>
              <Slider
                value={[settings.t_shift]}
                onValueChange={([v]) => update({ t_shift: v })}
                min={0}
                max={1}
                step={0.01}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label className="text-xs">Denoise</Label>
              <Switch
                checked={settings.denoise}
                onCheckedChange={(v) => update({ denoise: v })}
              />
            </div>

            <Separator className="my-2" />

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs">Use GPU (CUDA)</Label>
                <p className="text-[10px] text-muted-foreground">
                  {settingsLoading ? "Checking..." : cudaAvailable ? "GPU available" : "No GPU detected"}
                </p>
              </div>
              {settingsLoading ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : (
                <Switch
                  checked={useGpu}
                  onCheckedChange={handleGpuToggle}
                  disabled={!cudaAvailable}
                />
              )}
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
