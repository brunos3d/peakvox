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
import type { ParameterSchema, SettingsSchema } from "@/types"

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
        const onParamChange = (v: unknown) => onChange(key, v)

        switch (param.type) {
          case "number":
            if (param.nullable && param.ui_widget === "input") {
              return (
                <NullableNumberInput
                  key={key}
                  param={param}
                  value={value}
                  onChange={onParamChange}
                />
              )
            }
            if (param.nullable) {
              return (
                <NullableNumberSlider
                  key={key}
                  param={param}
                  value={value}
                  onChange={onParamChange}
                />
              )
            }
            return (
              <NumberSlider
                key={key}
                param={param}
                value={value}
                onChange={onParamChange}
              />
            )

          case "boolean":
            return (
              <BooleanSwitch
                key={key}
                param={param}
                value={value}
                onChange={onParamChange}
              />
            )

          case "select":
            return (
              <SelectField
                key={key}
                param={param}
                value={value}
                onChange={onParamChange}
              />
            )

          case "string":
            return (
              <StringField
                key={key}
                param={param}
                value={value}
                onChange={onParamChange}
              />
            )

          default:
            return null
        }
      })}
    </div>
  )
}

/**
 * Resolve the slider position that maps to `null` (the "Auto" position).
 * Priority: explicit `auto_value` → `default` if it lies in range → midpoint
 * of `minimum`/`maximum` → 0.
 */
function resolveAutoValue(param: ParameterSchema): number {
  if (param.auto_value != null) return param.auto_value
  if (
    typeof param.default === "number" &&
    param.minimum != null &&
    param.maximum != null &&
    param.default >= param.minimum &&
    param.default <= param.maximum
  ) {
    return param.default
  }
  if (param.minimum != null && param.maximum != null) {
    return (param.minimum + param.maximum) / 2
  }
  return 0
}

function isAutoValue(value: unknown, autoValue: number): boolean {
  if (value == null) return true
  const n = Number(value)
  if (Number.isNaN(n)) return true
  // Slider snaps to step multiples, so the only "Auto" position is exactly autoValue.
  return Math.abs(n - autoValue) < 1e-9
}

function formatHeaderValue(value: unknown): string {
  if (value == null) return "Auto"
  return String(value)
}

function NumberSlider({
  param,
  value,
  onChange,
}: {
  param: ParameterSchema
  value: unknown
  onChange: (v: number) => void
}) {
  const numeric = typeof value === "number" ? value : (param.default as number) ?? 0
  return (
    <div className="space-y-2">
      <div className="flex justify-between">
        <Label className="text-xs">{param.label}</Label>
        <span className="text-xs text-muted-foreground">{String(numeric)}</span>
      </div>
      <Slider
        value={[numeric]}
        onValueChange={([v]) => onChange(v)}
        min={param.minimum ?? 0}
        max={param.maximum ?? 100}
        step={param.step ?? 1}
      />
      {param.description && (
        <p className="text-[10px] text-muted-foreground">{param.description}</p>
      )}
    </div>
  )
}

function NullableNumberSlider({
  param,
  value,
  onChange,
}: {
  param: ParameterSchema
  value: unknown
  onChange: (v: number | null) => void
}) {
  const autoValue = resolveAutoValue(param)
  const step = param.step ?? 0.01
  const sliderPosition = isAutoValue(value, autoValue)
    ? autoValue
    : Number(value)
  const showAsAuto = isAutoValue(value, autoValue)

  return (
    <div className="space-y-2">
      <div className="flex justify-between">
        <Label className="text-xs">{param.label}</Label>
        <span className="text-xs text-muted-foreground">
          {formatHeaderValue(value)}
        </span>
      </div>
      <Slider
        value={[sliderPosition]}
        onValueChange={([v]) => {
          if (isAutoValue(v, autoValue)) {
            onChange(null)
          } else {
            onChange(v)
          }
        }}
        min={param.minimum ?? 0}
        max={param.maximum ?? 100}
        step={step}
      />
      <NullableSliderHints
        min={param.minimum ?? 0}
        max={param.maximum ?? 100}
        autoValue={autoValue}
        showAsAuto={showAsAuto}
      />
      {param.description && (
        <p className="text-[10px] text-muted-foreground">{param.description}</p>
      )}
    </div>
  )
}

function NullableSliderHints({
  min,
  max,
  autoValue,
  showAsAuto,
}: {
  min: number
  max: number
  autoValue: number
  showAsAuto: boolean
}) {
  if (max <= min) return null
  const leftLabel = min < 1 ? "slower" : "min"
  const rightLabel = max > 1 ? "faster" : "max"
  return (
    <div className="flex justify-between text-[9px] text-muted-foreground/70">
      <span>{min} · {leftLabel}</span>
      <span className={showAsAuto ? "text-foreground/80 font-medium" : ""}>
        {autoValue} · Auto
      </span>
      <span>{max} · {rightLabel}</span>
    </div>
  )
}

function NullableNumberInput({
  param,
  value,
  onChange,
}: {
  param: ParameterSchema
  value: unknown
  onChange: (v: number | null) => void
}) {
  const isEmpty = value == null
  const numeric = typeof value === "number" ? value : null

  return (
    <div className="space-y-2">
      <div className="flex justify-between">
        <Label className="text-xs">{param.label}</Label>
        <span className="text-xs text-muted-foreground">
          {isEmpty ? "Auto" : String(numeric)}
        </span>
      </div>
      <Input
        type="number"
        inputMode="numeric"
        min={param.minimum ?? undefined}
        max={param.maximum ?? undefined}
        step={param.step ?? undefined}
        value={isEmpty ? "" : String(numeric)}
        placeholder="Auto"
        onChange={(e) => {
          const raw = e.target.value.trim()
          if (raw === "") {
            onChange(null)
            return
          }
          const n = Number(raw)
          if (!Number.isNaN(n)) {
            onChange(n)
          }
        }}
        className="h-8 text-xs"
      />
      {param.description && (
        <p className="text-[10px] text-muted-foreground">{param.description}</p>
      )}
    </div>
  )
}

function BooleanSwitch({
  param,
  value,
  onChange,
}: {
  param: ParameterSchema
  value: unknown
  onChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <Label className="text-xs">{param.label}</Label>
        {param.description && (
          <p className="text-[10px] text-muted-foreground">{param.description}</p>
        )}
      </div>
      <Switch
        checked={!!value}
        onCheckedChange={(v) => onChange(v)}
      />
    </div>
  )
}

function SelectField({
  param,
  value,
  onChange,
}: {
  param: ParameterSchema
  value: unknown
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{param.label}</Label>
      <Select
        value={String(value ?? "")}
        onValueChange={(v) => onChange(v)}
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
        <p className="text-[10px] text-muted-foreground">{param.description}</p>
      )}
    </div>
  )
}

function StringField({
  param,
  value,
  onChange,
}: {
  param: ParameterSchema
  value: unknown
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{param.label}</Label>
      <Input
        className="h-8 text-xs"
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
        placeholder={param.description}
      />
    </div>
  )
}
