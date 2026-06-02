"use client";

import { useState, useEffect, useRef } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { RotateCcw, Save, CheckCircle } from "lucide-react";
import { GenerationSettingsFields } from "@/components/GenerationSettingsFields";
import { useAppStore, SYSTEM_DEFAULTS } from "@/store/use-store";
import {
  saveVoiceGenerationDefaults,
  fetchDeviceSettings,
  updateDeviceSettings,
} from "@/lib/api";
import type { VoiceGenerationDefaults } from "@/types";

function settingsEqual(
  a: VoiceGenerationDefaults,
  b: VoiceGenerationDefaults,
): boolean {
  return (
    a.num_step === b.num_step &&
    Math.abs(a.guidance_scale - b.guidance_scale) < 0.001 &&
    a.speed === b.speed &&
    a.duration === b.duration &&
    Math.abs(a.t_shift - b.t_shift) < 0.001 &&
    a.denoise === b.denoise &&
    a.use_gpu === b.use_gpu &&
    a.voice_design.length === b.voice_design.length &&
    a.voice_design.every((v, i) => v === b.voice_design[i])
  );
}

export function GenerationSettings() {
  const generationSettings = useAppStore((s) => s.generationSettings);
  const voiceDesign = useAppStore((s) => s.voiceDesign);
  const useGpu = useAppStore((s) => s.useGpu);
  const updateGenerationSettings = useAppStore(
    (s) => s.updateGenerationSettings,
  );
  const setUseGpu = useAppStore((s) => s.setUseGpu);
  const activeVoiceDefaults = useAppStore((s) => s.activeVoiceDefaults);
  const selectedProfile = useAppStore((s) => s.selectedProfile);
  const setActiveVoiceDefaults = useAppStore((s) => s.setActiveVoiceDefaults);
  const resetSettings = useAppStore((s) => s.resetSettings);
  const updateVoice = useAppStore((s) => s.updateVoice);

  const [cudaAvailable, setCudaAvailable] = useState(false);
  const [gpuLoading, setGpuLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Fetch server GPU state on mount and sync into store
  useEffect(() => {
    fetchDeviceSettings()
      .then((res) => {
        // Only update if no voice-profile defaults have already been loaded;
        // that way a freshly-selected voice always wins over the server state.
        if (!useAppStore.getState().activeVoiceDefaults) {
          setUseGpu(res.use_gpu);
        }
        setCudaAvailable(res.cuda_available);
      })
      .catch(() => {})
      .finally(() => setGpuLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // When the selected profile changes, sync use_gpu to the server so the
  // backend immediately reflects the loaded voice's GPU preference.
  const prevProfileIdRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    const currentId = selectedProfile?.id;
    if (currentId !== prevProfileIdRef.current) {
      prevProfileIdRef.current = currentId;
      if (activeVoiceDefaults !== null) {
        updateDeviceSettings(activeVoiceDefaults.use_gpu).catch(() => {});
      }
    }
  }, [selectedProfile?.id, activeVoiceDefaults]);

  // Build the combined current state for comparison. voice_design is edited via
  // the builder on the TTS canvas; folding it in here keeps the dirty indicator
  // and "Save to Voice Profile" in sync with the canvas selection.
  const current: VoiceGenerationDefaults = {
    ...generationSettings,
    voice_design: voiceDesign,
    use_gpu: useGpu,
  };

  const reference = activeVoiceDefaults ?? SYSTEM_DEFAULTS;
  const isDirty = !settingsEqual(current, reference);

  const handleFieldChange = (next: VoiceGenerationDefaults) => {
    updateGenerationSettings({
      num_step: next.num_step,
      guidance_scale: next.guidance_scale,
      speed: next.speed,
      duration: next.duration,
      t_shift: next.t_shift,
      denoise: next.denoise,
    });
    if (next.use_gpu !== useGpu) {
      setUseGpu(next.use_gpu);
      updateDeviceSettings(next.use_gpu).catch(() => {});
    }
  };

  const handleSave = async () => {
    if (!selectedProfile || !isDirty) return;
    setSaving(true);
    try {
      const updated = await saveVoiceGenerationDefaults(
        selectedProfile.id,
        current,
      );
      // Sync the store so the dirty indicator clears
      setActiveVoiceDefaults(current);
      updateVoice(selectedProfile.id, {
        generation_defaults: updated.generation_defaults,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    } catch {
      // Silently fail — the button state remains dirty
    } finally {
      setSaving(false);
    }
  };

  const triggerLabel = (
    <span className="flex items-center gap-2">
      Generation Settings
      {isDirty && selectedProfile && (
        <span className="text-[10px] font-medium text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">
          Modified
        </span>
      )}
      {!isDirty && selectedProfile && activeVoiceDefaults && (
        <span className="text-[10px] font-medium text-primary/70 bg-primary/10 px-1.5 py-0.5 rounded">
          Voice preset
        </span>
      )}
    </span>
  );

  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="settings">
        <AccordionTrigger className="text-sm">{triggerLabel}</AccordionTrigger>
        <AccordionContent className="px-2">
          <div className="space-y-4 pt-2">
            {selectedProfile && activeVoiceDefaults && !isDirty && (
              <p className="text-[11px] text-muted-foreground">
                Using defaults from{" "}
                <span className="font-medium text-foreground">
                  {selectedProfile.name}
                </span>
              </p>
            )}

            <GenerationSettingsFields
              value={current}
              onChange={handleFieldChange}
              cudaAvailable={cudaAvailable}
              gpuLoading={gpuLoading}
            />

            {/* Reset / Save actions — only shown when dirty */}
            {isDirty && (
              <div className="flex gap-2 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1.5 flex-1"
                  onClick={resetSettings}
                >
                  <RotateCcw className="h-3 w-3" />
                  Reset
                </Button>

                {selectedProfile && (
                  <Button
                    type="button"
                    size="sm"
                    className="gap-1.5 flex-1"
                    onClick={handleSave}
                    disabled={saving}
                  >
                    <Save className="h-3 w-3" />
                    {saving ? "Saving…" : "Save to Voice Profile"}
                  </Button>
                )}
              </div>
            )}

            {saveSuccess && (
              <div className="flex items-center gap-1.5 text-xs text-green-600">
                <CheckCircle className="h-3.5 w-3.5" />
                Voice profile updated
              </div>
            )}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
