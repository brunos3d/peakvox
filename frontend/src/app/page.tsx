"use client";

import { useRef, useState } from "react";
import { Wand2, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageLayout } from "@/components/shell/PageLayout";
import { PageHeader } from "@/components/shell/PageHeader";
import { GenerationPanel } from "@/components/generation/GenerationPanel";
import { QuickPrompts } from "@/components/generation/QuickPrompts";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAppStore } from "@/store/use-store";
import { useSubmitGeneration, useModelStatus } from "@/hooks/use-generation";
import { VoiceDesignBuilder } from "@/components/generation/VoiceDesignBuilder";
import { buildInstruct } from "@/config/voice-design";

const LANGUAGES = [
  "Auto",
  "English",
  "Portuguese",
  "Spanish",
  "French",
  "German",
  "Chinese",
  "Japanese",
];
export default function TextToSpeechPage() {
  const text = useAppStore((s) => s.ttsText);
  const setText = useAppStore((s) => s.setTtsText);
  const selectedProfile = useAppStore((s) => s.selectedProfile);
  const generationSettings = useAppStore((s) => s.generationSettings);
  const voiceDesign = useAppStore((s) => s.voiceDesign);
  const setVoiceDesign = useAppStore((s) => s.setVoiceDesign);
  const activeJobId = useAppStore((s) => s.activeJobId);

  const [language, setLanguage] = useState("Auto");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const showPrompts = text.length === 0;

  const { data: model } = useModelStatus();
  const generate = useSubmitGeneration();

  const modelReady = !!model?.loaded;
  const isGenerating = generate.isPending || !!activeJobId;
  const canGenerate =
    !!text.trim() && !!selectedProfile && modelReady && !isGenerating;

  const handleGenerate = () => {
    if (!canGenerate) return;
    generate.mutate({
      text: text.trim(),
      voice_profile_id: selectedProfile?.id ?? null,
      language: language === "Auto" ? null : language,
      ref_text: selectedProfile?.transcript || null,
      instruct: voiceDesign.length ? buildInstruct(voiceDesign) : null,
      ...generationSettings,
    });
  };

  const insertPrompt = (prompt: string) => {
    const el = textareaRef.current;
    if (el) {
      // Quick prompts only appear when the field is empty, so this "fills"
      // rather than appends. Using the native insertText command keeps the
      // browser's undo history intact and lets onChange sync the store.
      el.focus();
      el.setSelectionRange(0, el.value.length);
      const inserted = document.execCommand("insertText", false, prompt);
      if (inserted) {
        el.setSelectionRange(el.value.length, el.value.length);
        return;
      }
    }
    // Fallback for environments without execCommand support.
    setText(prompt);
    requestAnimationFrame(() => {
      const node = textareaRef.current;
      if (node) {
        node.focus();
        node.setSelectionRange(node.value.length, node.value.length);
      }
    });
  };

  return (
    <PageLayout contextPanel={<GenerationPanel />} contextTitle="Settings">
      <div className="mx-auto flex h-full max-w-3xl flex-col">
        <PageHeader
          title="Text to Speech"
          description="Type or paste text and generate speech with your voices."
        />

        {!modelReady && (
          <div className="mt-5 flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
            <Loader2 className="h-4 w-4 animate-spin" />
            {model?.loading
              ? "Loading the voice model — this can take a few minutes on first run."
              : "Model is offline."}
          </div>
        )}

        <div className="mt-6 flex flex-1 flex-col">
          <Textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type or paste text to generate speech..."
            className="min-h-[260px] flex-1 resize-none rounded-xl border-border bg-surface p-5 text-base leading-relaxed"
          />

          {/* Quick prompts appear only when the textarea is empty, fading and
              collapsing out the moment the user types (and back in when cleared). */}
          <div
            aria-hidden={!showPrompts}
            className={cn(
              "grid transition-all duration-200 ease-out",
              showPrompts
                ? "mt-4 grid-rows-[1fr] opacity-100"
                : "pointer-events-none mt-0 grid-rows-[0fr] opacity-0",
            )}
          >
            <div className="overflow-hidden">
              <p className="text-caption mb-2">Quick prompts</p>
              <QuickPrompts language={language} onSelect={insertPrompt} />
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <div className="space-y-2 sm:max-w-xs">
              <Label className="text-xs">Language</Label>
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LANGUAGES.map((lang) => (
                    <SelectItem key={lang} value={lang}>
                      {lang}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">
                Voice design{" "}
                <span className="font-normal text-muted-foreground">(optional)</span>
              </Label>
              <VoiceDesignBuilder value={voiceDesign} onChange={setVoiceDesign} />
            </div>
          </div>

          {generate.isError && (
            <p className="mt-4 flex items-center gap-2 rounded-lg bg-error/10 px-3 py-2 text-xs text-error">
              <AlertCircle className="h-4 w-4" />
              {(generate.error as Error)?.message ??
                "Generation failed. Please try again."}
            </p>
          )}

          {!selectedProfile && (
            <p className="mt-4 text-sm text-muted-foreground">
              Select a voice in the Settings panel to get started.
            </p>
          )}

          <div className="mt-6 pb-2">
            <Button
              className="h-11 w-full gap-2 text-base"
              onClick={handleGenerate}
              disabled={!canGenerate}
            >
              {isGenerating ? (
                <span className="animate-pulse">Generating…</span>
              ) : (
                <>
                  <Wand2 className="h-5 w-5" /> Generate speech
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
