"use client";

import { useState } from "react";
import { Cpu, ChevronRight, Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ModelCard } from "@/components/generation/ModelCard";
import { useAppStore } from "@/store/use-store";
import { useModels } from "@/hooks/use-models";

export function ModelSelector() {
  const selectedModelId = useAppStore((s) => s.selectedModelId);
  const setSelectedModelId = useAppStore((s) => s.setSelectedModelId);
  const { data: models, isLoading } = useModels();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const active = selectedModelId
    ? models?.find((m) => m.id === selectedModelId)
    : models?.find((m) => m.is_default);

  const filtered = (models ?? [])
    .filter((m) => m.activation_status === "active")
    .filter(
      (m) =>
        m.name.toLowerCase().includes(query.toLowerCase()) ||
        m.description.toLowerCase().includes(query.toLowerCase()),
    );

  const statusLabel = active?.status === "loaded" || active?.status === "available"
    ? undefined
    : active?.status === "loading"
      ? "Loading"
      : active?.status === "error"
        ? "Error"
        : undefined;

  return (
    <div className="space-y-2">
      <p className="text-caption uppercase tracking-wide">Model</p>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <button className="flex w-full items-center gap-3 rounded-xl border border-border bg-surface p-3 text-left transition-colors hover:bg-surface-2">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
              <Cpu className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-card-title truncate">
                {active ? active.name : "Select a model"}
              </p>
              <p className="text-caption truncate">
                {active?.is_default
                  ? "Default"
                  : statusLabel
                    ? statusLabel
                    : active?.description
                      ? active.description
                      : "Choose a model"}
              </p>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          </button>
        </SheetTrigger>
        <SheetContent side="right" className="w-full sm:max-w-md p-0">
          <SheetHeader className="border-b border-border">
            <SheetTitle>Select a model</SheetTitle>
          </SheetHeader>
          <div className="border-b border-border p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search models…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {isLoading ? (
              <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground justify-center">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading models…
              </div>
            ) : filtered.length > 0 ? (
              filtered.map((model) => (
                <ModelCard
                  key={model.id}
                  model={model}
                  selected={model.id === active?.id}
                  onSelect={(m) => {
                    setSelectedModelId(m.is_default ? null : m.id);
                    setOpen(false);
                    setQuery("");
                  }}
                />
              ))
            ) : (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No models match your search.
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
