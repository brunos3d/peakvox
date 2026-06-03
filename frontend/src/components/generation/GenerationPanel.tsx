"use client";

import { VoiceSelector } from "@/components/voice/VoiceSelector";
import { ModelSelector } from "@/components/generation/ModelSelector";
import { OutputFormatSelector } from "@/components/generation/OutputFormatSelector";
import { GenerationSettings } from "@/components/GenerationSettings";

/**
 * The Text-to-Speech context panel: voice + model selection, the (collapsible)
 * generation settings with per-voice save, and output format. Reuses the
 * existing GenerationSettings so the voice-defaults save/dirty behavior is
 * preserved exactly.
 */
export function GenerationPanel() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h2 className="text-section-title">Settings</h2>
        <p className="text-caption mt-0.5">Tune the voice and how it speaks.</p>
      </div>

      <VoiceSelector />
      <ModelSelector />
      <GenerationSettings />
      <OutputFormatSelector />
    </div>
  );
}
