"use client";

import { useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { RotateCcw, SlidersHorizontal } from "lucide-react";
import { DynamicSettingsForm } from "@/components/DynamicSettingsForm";
import { useAppStore } from "@/store/use-store";
import { useActiveModel } from "@/hooks/use-models";
import { filterSettingsForModel, initializeSettingsFromSchema } from "@/hooks/use-generation";

export function ModelSettingsForm() {
  const modelSettings = useAppStore((s) => s.modelSettings);
  const selectedModelId = useAppStore((s) => s.selectedModelId);
  const updateModelSetting = useAppStore((s) => s.updateModelSetting);
  const initModelSettings = useAppStore((s) => s.initModelSettings);
  const { activeModel } = useActiveModel();

  const modelKey = selectedModelId ?? "__default__";
  const schema = activeModel?.settings_schema ?? null;

  // Lazy-init model settings from schema defaults when first selecting a model
  useEffect(() => {
    if (schema && !modelSettings[modelKey]) {
      const defaults = initializeSettingsFromSchema(schema)
      initModelSettings(modelKey, defaults)
    }
  }, [modelKey, schema, modelSettings[modelKey]])

  const currentSettings = modelSettings[modelKey] ?? {};
  const displaySettings = schema
    ? filterSettingsForModel(currentSettings, schema)
    : {};

  const handleChange = useCallback((key: string, value: unknown) => {
    updateModelSetting(key, value)
  }, [updateModelSetting])

  const handleReset = useCallback(() => {
    const defaults = initializeSettingsFromSchema(schema)
    initModelSettings(modelKey, defaults)
  }, [schema, modelKey, initModelSettings])

  if (!schema) {
    return (
      <EmptyState
        icon={SlidersHorizontal}
        title="No configurable settings"
        description={
          activeModel
            ? `${activeModel.name} uses built-in defaults — no knobs to turn.`
            : "This model uses built-in defaults — no knobs to turn."
        }
        className="py-4"
      />
    )
  }

  const defaults = initializeSettingsFromSchema(schema)
  const hasChanged = Object.keys(displaySettings).some(
    (key) => displaySettings[key] !== defaults[key]
  )

  return (
    <div className="space-y-4 pt-2">
      <DynamicSettingsForm
        schema={schema}
        values={displaySettings}
        onChange={handleChange}
      />

      {hasChanged && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-1.5 w-full"
          onClick={handleReset}
        >
          <RotateCcw className="h-3 w-3" />
          Reset
        </Button>
      )}
    </div>
  )
}
