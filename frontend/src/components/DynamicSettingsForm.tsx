"use client"

import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { SettingsSchema } from "@/types"

interface DynamicSettingsFormProps {
  schema: SettingsSchema
  values: Record<string, unknown>
  onChange: (key: string, value: unknown) => void
}

export function DynamicSettingsForm({
  schema,
  values,
  onChange,
}: DynamicSettingsFormProps) {
  return (
    <div className="space-y-4">
      {Object.entries(schema.properties).map(([key, param]) => {
        const value = values[key] ?? param.default ?? null

        switch (param.type) {
          case "number":
            return (
              <div key={key} className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs">{param.label}</Label>
                  <span className="text-xs text-muted-foreground">
                    {value != null ? String(value) : "Auto"}
                  </span>
                </div>
                <Slider
                  value={[Number(value ?? param.minimum ?? 0)]}
                  onValueChange={([v]) => onChange(key, v)}
                  min={param.minimum ?? 0}
                  max={param.maximum ?? 100}
                  step={param.step ?? 1}
                />
                {param.description && (
                  <p className="text-[10px] text-muted-foreground">
                    {param.description}
                  </p>
                )}
              </div>
            )

          case "boolean":
            return (
              <div key={key} className="flex items-center justify-between">
                <div>
                  <Label className="text-xs">{param.label}</Label>
                  {param.description && (
                    <p className="text-[10px] text-muted-foreground">
                      {param.description}
                    </p>
                  )}
                </div>
                <Switch
                  checked={!!value}
                  onCheckedChange={(v) => onChange(key, v)}
                />
              </div>
            )

          case "select":
            return (
              <div key={key} className="space-y-1.5">
                <Label className="text-xs">{param.label}</Label>
                <Select
                  value={String(value ?? "")}
                  onValueChange={(v) => onChange(key, v)}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder={param.label} />
                  </SelectTrigger>
                  <SelectContent>
                    {param.options?.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value} className="text-xs">
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {param.description && (
                  <p className="text-[10px] text-muted-foreground">
                    {param.description}
                  </p>
                )}
              </div>
            )

          case "string":
            return (
              <div key={key} className="space-y-1.5">
                <Label className="text-xs">{param.label}</Label>
                <Input
                  className="h-8 text-xs"
                  value={String(value ?? "")}
                  onChange={(e) => onChange(key, e.target.value)}
                  placeholder={param.description}
                />
              </div>
            )

          default:
            return null
        }
      })}
    </div>
  )
}
