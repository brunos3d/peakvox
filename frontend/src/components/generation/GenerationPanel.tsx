"use client";

import { Wand2, Loader2, AlertCircle, Cpu, Mic } from "lucide-react";
import { cn } from "@/lib/utils";
import { VoiceSelector } from "@/components/voice/VoiceSelector";
import { ModelSelector } from "@/components/generation/ModelSelector";
import { OutputFormatSelector } from "@/components/generation/OutputFormatSelector";
import { GenerationSettings } from "@/components/GenerationSettings";
import { LanguageCombobox } from "@/components/common/LanguageCombobox";
import { VoiceDesignBuilder } from "@/components/generation/VoiceDesignBuilder";
import { ModelInfoCard } from "@/components/generation/ModelInfoCard";
import { EmotionSettings } from "@/components/generation/EmotionSettings";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import { useAppStore } from "@/store/use-store";
import { useSubmitGeneration, useModelStatus } from "@/hooks/use-generation";
import { useActiveModel } from "@/hooks/use-models";
import { buildInstruct } from "@/config/voice-design";
import { validateTags } from "@/editor/validate";

/**
 * The Text-to-Speech context panel: accordion sections for voice, model,
 * generation settings, output format, language, voice design, emotion,
 * model info, and a pinned Generate button at the bottom.
 */
export function GenerationPanel() {
  const text = useAppStore((s) => s.ttsText);
  const selectedProfile = useAppStore((s) => s.selectedProfile);
  const generationSettings = useAppStore((s) => s.generationSettings);
  const voiceDesign = useAppStore((s) => s.voiceDesign);
  const setVoiceDesign = useAppStore((s) => s.setVoiceDesign);
  const activeJobId = useAppStore((s) => s.activeJobId);
  const language = useAppStore((s) => s.ttsLanguage);
  const setLanguage = useAppStore((s) => s.setTtsLanguage);
  const { data: model } = useModelStatus();
  const { activeModel } = useActiveModel();
  const generate = useSubmitGeneration();

  const modelReady = !!model?.loaded;
  const isGenerating = generate.isPending || !!activeJobId;

  const tagIssues = activeModel ? validateTags(text, activeModel.supported_tags) : [];
  const hasTagIssues = tagIssues.length > 0;
  const canGenerate = !!text.trim() && !!selectedProfile && modelReady && !isGenerating && !hasTagIssues;

  const handleGenerate = () => {
    if (!canGenerate) return;
    generate.mutate({
      text: text.trim(),
      voice_profile_id: selectedProfile?.id ?? null,
      language: language,
      ref_text: selectedProfile?.transcript || null,
      instruct: voiceDesign.length ? buildInstruct(voiceDesign) : null,
      ...generationSettings,
    });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-1">
        <h2 className="text-section-title mb-1 mt-4 px-5">Settings</h2>
        <p className="text-caption mb-3 px-5">Tune the voice and how it speaks.</p>

        <Accordion type="multiple" defaultValue={["voice", "model", "language", "voice-design"]}>
          {/* 1. Voice */}
          <AccordionItem value="voice">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <Mic className="h-4 w-4 text-primary" />
                Voice
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <VoiceSelector />
            </AccordionContent>
          </AccordionItem>

          {/* 2. Model */}
          <AccordionItem value="model">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" />
                Model
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <ModelSelector />
            </AccordionContent>
          </AccordionItem>

          {/* 3. Generation Settings */}
          <AccordionItem value="settings">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
                Generation Settings
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <GenerationSettings />
            </AccordionContent>
          </AccordionItem>

          {/* 4. Output Format */}
          <AccordionItem value="output-format">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                Output Format
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <OutputFormatSelector />
            </AccordionContent>
          </AccordionItem>

          {/* 5. Language */}
          <AccordionItem value="language">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                Language
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <LanguageCombobox
                value={language}
                onChange={(lang) => setLanguage(lang?.id ?? null)}
              />
            </AccordionContent>
          </AccordionItem>

          {/* 6. Voice Design */}
          <AccordionItem value="voice-design">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                Voice Design
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <VoiceDesignBuilder value={voiceDesign} onChange={setVoiceDesign} />
            </AccordionContent>
          </AccordionItem>

          {/* 7. Emotion Settings */}
          <AccordionItem value="emotion">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
                Emotion Settings
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <EmotionSettings />
            </AccordionContent>
          </AccordionItem>

          {/* 8. Model Information */}
          <AccordionItem value="model-info">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                Model Information
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5">
              <ModelInfoCard />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>

      {/* 9. Generate Speech — pinned at bottom */}
      <div className={cn("shrink-0 border-t border-border p-5", "flex flex-col gap-3")}>
        {generate.isError && (
          <p className="flex items-center gap-2 rounded-lg bg-error/10 px-3 py-2 text-xs text-error">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {(generate.error as Error)?.message ?? "Generation failed. Please try again."}
          </p>
        )}

        {hasTagIssues && (
          <div className="rounded-lg bg-warning/10 px-3 py-2">
            <p className="flex items-center gap-2 text-xs text-warning">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {tagIssues.length} unsupported tag{tagIssues.length !== 1 ? "s" : ""}:
            </p>
            <ul className="mt-1 space-y-0.5 pl-6">
              {tagIssues.map((issue) => (
                <li key={issue.tagId} className="text-xs text-warning/80">
                  [{issue.tagId}] &mdash; not supported by {activeModel?.name ?? "this model"}
                </li>
              ))}
            </ul>
          </div>
        )}

        {!selectedProfile && (
          <p className="text-xs text-muted-foreground">
            Select a voice above to get started.
          </p>
        )}

        <Button
          className="h-11 w-full gap-2 text-base"
          onClick={handleGenerate}
          disabled={!canGenerate}
        >
          {isGenerating ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Generating…
            </span>
          ) : (
            <>
              <Wand2 className="h-5 w-5" /> Generate speech
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
