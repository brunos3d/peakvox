"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageLayout } from "@/components/shell/PageLayout";
import { PageHeader } from "@/components/shell/PageHeader";
import { GenerationPanel } from "@/components/generation/GenerationPanel";
import { QuickPrompts } from "@/components/generation/QuickPrompts";
import { PerformanceEditor } from "@/editor/PerformanceEditor";
import { getLanguageLabel } from "@/lib/languages";
import { useAppStore } from "@/store/use-store";
import { useActiveModel } from "@/hooks/use-models";

export default function TextToSpeechPage() {
  const text = useAppStore((s) => s.ttsText);
  const setText = useAppStore((s) => s.setTtsText);
  const language = useAppStore((s) => s.ttsLanguage);

  const showPrompts = text.length === 0;

  const { activeModel } = useActiveModel();
  const modelReady = activeModel?.activation_status === "active";

  const insertPrompt = (prompt: string) => {
    setText(prompt);
  };

  return (
    <PageLayout contextPanel={<GenerationPanel />} contextTitle="Settings">
      <div className="mx-auto flex h-full max-w-3xl flex-col">
        <PageHeader
          title="Text to Speech"
          description="Direct a voice performance."
        />

        {activeModel && !modelReady && (
          <div className="mt-5 flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
            <Loader2 className="h-4 w-4 animate-spin" />
            Model is offline. Start it from the Models page.
          </div>
        )}

        <div className="mt-6 flex flex-1 flex-col">
          <PerformanceEditor
            value={text}
            onChange={setText}
            className="flex flex-col flex-1"
          />

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
              <QuickPrompts
                language={getLanguageLabel(language)}
                onSelect={insertPrompt}
              />
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
