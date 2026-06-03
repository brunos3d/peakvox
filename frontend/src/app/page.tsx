"use client";

import { Loader2 } from "lucide-react";
import { PageLayout } from "@/components/shell/PageLayout";
import { PageHeader } from "@/components/shell/PageHeader";
import { GenerationPanel } from "@/components/generation/GenerationPanel";
import { PerformanceEditor } from "@/editor/PerformanceEditor";
import { useAppStore } from "@/store/use-store";
import { useModelStatus } from "@/hooks/use-generation";

export default function TextToSpeechPage() {
  const text = useAppStore((s) => s.ttsText);
  const setText = useAppStore((s) => s.setTtsText);

  const { data: model } = useModelStatus();
  const modelReady = !!model?.loaded;

  return (
    <PageLayout contextPanel={<GenerationPanel />} contextTitle="Settings">
      <div className="mx-auto flex h-full max-w-3xl flex-col">
        <PageHeader
          title="Text to Speech"
          description="Direct a voice performance."
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
          <PerformanceEditor
            value={text}
            onChange={setText}
          />
        </div>
      </div>
    </PageLayout>
  );
}
