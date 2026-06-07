"use client";

import { useEffect, useState, useCallback } from "react";
import { Wand2, Loader2, AlertCircle, Cpu, Mic, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { VoiceSelector } from "@/components/voice/VoiceSelector";
import { ModelSelector } from "@/components/generation/ModelSelector";
import { OutputFormatSelector } from "@/components/generation/OutputFormatSelector";
import { ModelSettingsForm } from "@/components/generation/ModelSettingsForm";
import { LanguageCombobox } from "@/components/common/LanguageCombobox";
import { VoiceDesignBuilder } from "@/components/generation/VoiceDesignBuilder";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import { useAppStore, useActiveVoice } from "@/store/use-store";
import { useSubmitGeneration, useModelStatus } from "@/hooks/use-generation";
import { useActiveModel, useRecommendedModelId, useModels } from "@/hooks/use-models";
import { filterSettingsForModel } from "@/hooks/use-generation";
import { useVoiceModelCompatibility } from "@/hooks/use-voice-model-compatibility";
import { useQueryClient } from "@tanstack/react-query";
import { buildInstruct } from "@/config/voice-design";
import { validateTags } from "@/editor/validate";
import { importVoiceResource } from "@/lib/api";

export function GenerationPanel() {
  const text = useAppStore((s) => s.ttsText);
  const selectedProfile = useAppStore((s) => s.selectedProfile);
  const temporaryVoice = useAppStore((s) => s.temporaryVoice);
  const promoteTemporaryToPersisted = useAppStore((s) => s.promoteTemporaryToPersisted);
  const modelSettings = useAppStore((s) => s.modelSettings);
  const voiceDesign = useAppStore((s) => s.voiceDesign);
  const setVoiceDesign = useAppStore((s) => s.setVoiceDesign);
  const activeJobId = useAppStore((s) => s.activeJobId);
  const language = useAppStore((s) => s.ttsLanguage);
  const setLanguage = useAppStore((s) => s.setTtsLanguage);
  const selectedModelId = useAppStore((s) => s.selectedModelId);
  const setSelectedModelId = useAppStore((s) => s.setSelectedModelId);
  const { data: model } = useModelStatus();
  const { activeModel } = useActiveModel();
  const { data: allModels } = useModels();
  const generate = useSubmitGeneration();
  const activeVoice = useActiveVoice();
  const queryClient = useQueryClient();
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isImportingLibrary, setIsImportingLibrary] = useState(false);

  const modelReady = !!model?.loaded;
  const isGenerating = generate.isPending || !!activeJobId;

  const { getState: getModelState } = useVoiceModelCompatibility(activeVoice);
  const modelState = selectedModelId && activeModel ? getModelState(selectedModelId) : null;
  const selectedModelIncompatible = modelState === "incompatible";
  const selectedModelBuildable = modelState === "buildable";

  const recommendedModelId = useRecommendedModelId(activeVoice);

  useEffect(() => {
    if (!activeVoice || !activeVoice.compatible_models?.length) return;
    if (!selectedModelId) return;

    // If current model is already compatible, no action needed
    const cur = getModelState(selectedModelId);
    if (cur === "ready" || cur === "buildable") return;

    // Current model is incompatible — find a better match:
    // ready > buildable > recommended > first compatible
    const compatModels = allModels?.filter(
      (m) => activeVoice.compatible_models.includes(m.id),
    ) ?? [];

    for (const m of compatModels) {
      const state = getModelState(m.id);
      if (state === "ready") {
        setSelectedModelId(m.id);
        return;
      }
    }

    for (const m of compatModels) {
      const state = getModelState(m.id);
      if (state === "buildable") {
        setSelectedModelId(m.id);
        return;
      }
    }

    if (recommendedModelId && recommendedModelId !== selectedModelId) {
      setSelectedModelId(recommendedModelId);
    }
  }, [activeVoice?.id, selectedModelId, getModelState, allModels, recommendedModelId]);

  const tagIssues = activeModel
    ? validateTags(text, activeModel.supported_tags)
    : [];
  const hasTagIssues = tagIssues.length > 0;
  const canGenerate =
    !!text.trim() &&
    !!activeVoice &&
    modelReady &&
    !isGenerating &&
    !isImporting &&
    !hasTagIssues &&
    !selectedModelIncompatible && !selectedModelBuildable;

  const handleImportToLibrary = useCallback(async () => {
    if (!temporaryVoice) return;
    setIsImportingLibrary(true);
    setGenerationError(null);
    try {
      const profile = await importVoiceResource(temporaryVoice.source_resource_id);
      promoteTemporaryToPersisted(profile);
      queryClient.invalidateQueries({ queryKey: ["voices-page"] });
      queryClient.invalidateQueries({ queryKey: ["voices"] });
    } catch (e) {
      setGenerationError(
        e instanceof Error ? e.message : "Failed to import voice to library.",
      );
    } finally {
      setIsImportingLibrary(false);
    }
  }, [temporaryVoice, promoteTemporaryToPersisted, queryClient]);

  const handleGenerate = useCallback(async () => {
    if (!canGenerate) return;

    setGenerationError(null);

    let voiceProfileId = selectedProfile?.id ?? null;
    let transcript = selectedProfile?.transcript ?? null;

    if (!selectedProfile && temporaryVoice) {
      setIsImporting(true);
      try {
        const profile = await importVoiceResource(temporaryVoice.source_resource_id);
        promoteTemporaryToPersisted(profile);
        voiceProfileId = profile.id;
        transcript = profile.transcript;
      } catch (e) {
        setGenerationError(
          e instanceof Error ? e.message : "Failed to import voice for generation.",
        );
        setIsImporting(false);
        return;
      }
      setIsImporting(false);
    }

    const currentModel = allModels?.find((m) => m.id === selectedModelId);
    const filteredParams = filterSettingsForModel(
      modelSettings[selectedModelId ?? "__default__"] ?? {},
      currentModel?.settings_schema,
    );

    generate.mutate({
      text: text.trim(),
      model_id: selectedModelId,
      voice_profile_id: voiceProfileId,
      language: language,
      ref_text: transcript || null,
      instruct: voiceDesign.length ? buildInstruct(voiceDesign) : null,
      params: filteredParams,
    });
  }, [
    canGenerate, selectedProfile, temporaryVoice, promoteTemporaryToPersisted,
    text, selectedModelId, language, voiceDesign, modelSettings, generate, allModels,
  ]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-1">
        <h2 className="text-section-title mb-1 mt-4 px-5">Settings</h2>
        <p className="text-caption mb-3 px-5">
          Tune the voice and how it speaks.
        </p>

        <Accordion
          type="multiple"
          defaultValue={["voice", "model", "language", "voice-design"]}
        >
          {/* 1. Voice */}
          <AccordionItem value="voice">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <Mic className="h-4 w-4 text-primary" />
                Voice
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5 py-1 mb-4">
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
            <AccordionContent className="px-5 py-1 mb-4">
              <ModelSelector />
            </AccordionContent>
          </AccordionItem>

          {/* 3. Generation Settings */}
          <AccordionItem value="settings">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg
                  className="h-4 w-4 text-primary"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="3" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                </svg>
                Generation Settings
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5 py-1 mb-4">
              <ModelSettingsForm />
            </AccordionContent>
          </AccordionItem>

          {/* 4. Output Format */}
          <AccordionItem value="output-format">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg
                  className="h-4 w-4 text-primary"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M9 18V5l12-2v13" />
                  <circle cx="6" cy="18" r="3" />
                  <circle cx="18" cy="16" r="3" />
                </svg>
                Output Format
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5 py-1 mb-4">
              <OutputFormatSelector />
            </AccordionContent>
          </AccordionItem>

          {/* 5. Language */}
          <AccordionItem value="language">
            <AccordionTrigger className="px-5 text-sm font-medium">
              <span className="flex items-center gap-2">
                <svg
                  className="h-4 w-4 text-primary"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="10" />
                  <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                </svg>
                Language
              </span>
            </AccordionTrigger>
            <AccordionContent className="px-5 py-1 mb-4">
              <LanguageCombobox
                value={language}
                onChange={(lang) => setLanguage(lang?.id ?? null)}
                availableLanguageIds={
                  activeModel?.supported_languages?.length
                    ? activeModel.supported_languages
                    : undefined
                }
              />
            </AccordionContent>
          </AccordionItem>

          {/* 6. Voice Design — shown only when the selected model declares the capability.
                Capability-driven (ADR-0003): no model-name branching. */}
          {(activeModel?.capabilities?.supports_voice_design ?? true) && (
            <AccordionItem value="voice-design">
              <AccordionTrigger className="px-5 text-sm font-medium">
                <span className="flex items-center gap-2">
                  <svg
                    className="h-4 w-4 text-primary"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                  </svg>
                  Voice Design
                </span>
              </AccordionTrigger>
              <AccordionContent className="px-5 py-1 mb-4">
                <VoiceDesignBuilder
                  value={voiceDesign}
                  onChange={setVoiceDesign}
                />
              </AccordionContent>
            </AccordionItem>
          )}
        </Accordion>
      </div>

      {/* Generate Speech — pinned at bottom */}
      <div
        className={cn(
          "shrink-0 border-t border-border p-5",
          "flex flex-col gap-3",
        )}
      >
        {generate.isError && (
          <p className="flex items-center gap-2 rounded-lg bg-error/10 px-3 py-2 text-xs text-error">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {(generate.error as Error)?.message ??
              "Generation failed. Please try again."}
          </p>
        )}

        {selectedModelIncompatible && (
          <p className="flex items-center gap-2 rounded-lg bg-warning/10 px-3 py-2 text-xs text-warning">
            <AlertCircle className="h-4 w-4 shrink-0" />
            This voice is not compatible with{" "}
            <span className="font-medium">{activeModel?.name}</span>.
            Select a different model or voice.
          </p>
        )}

        {selectedModelBuildable && !selectedModelIncompatible && (
          <p className="flex items-center gap-2 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            Build a variant for{" "}
            <span className="font-medium">{activeModel?.name}</span>{" "}
            before generating. Use Model Compatibility section.
          </p>
        )}

        {hasTagIssues && (
          <div className="rounded-lg bg-warning/10 px-3 py-2">
            <p className="flex items-center gap-2 text-xs text-warning">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {tagIssues.length} unsupported tag
              {tagIssues.length !== 1 ? "s" : ""}:
            </p>
            <ul className="mt-1 space-y-0.5 pl-6">
              {tagIssues.map((issue) => (
                <li key={issue.tagId} className="text-xs text-warning/80">
                  [{issue.tagId}] &mdash; not supported by{" "}
                  {activeModel?.name ?? "this model"}
                </li>
              ))}
            </ul>
          </div>
        )}

        {!activeVoice && (
          <p className="text-xs text-muted-foreground">
            Select a voice above to get started.
          </p>
        )}

        {generationError && (
          <p className="flex items-center gap-2 rounded-lg bg-error/10 px-3 py-2 text-xs text-error">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {generationError}
          </p>
        )}

        {temporaryVoice && (
          <Button
            className="h-10 w-full gap-2 text-sm"
            variant="outline"
            onClick={handleImportToLibrary}
            disabled={isImportingLibrary || isGenerating}
          >
            {isImportingLibrary ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Importing to Library…
              </span>
            ) : (
              <>
                <Plus className="h-4 w-4" />
                Import <span className="font-medium">{temporaryVoice.name}</span> to Library
              </>
            )}
          </Button>
        )}

        <Button
          className="h-11 w-full gap-2 text-base"
          onClick={handleGenerate}
          disabled={!canGenerate}
        >
          {isImporting ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Importing voice…
            </span>
          ) : isGenerating ? (
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
