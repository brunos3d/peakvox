"use client";

import { useState } from "react";
import {
  AlertTriangle,
  BadgeCheck,
  Check,
  CheckCircle2,
  Download,
  Layers,
  Loader2,
  Plus,
  Sparkles,
  Star,
  X,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { validateVariantImport } from "@/lib/api";
import type {
  ComposedRuntimeVariant,
  RuntimeVariantTrust,
  VariantImportValidation,
} from "@/types";

// The platform's closed RuntimeVariant capability vocabulary — mirrors the
// backend `RUNTIME_CAPABILITY_VOCABULARY` (app/services/runtime_types.py).
// Users pick from these; custom entries are still allowed (future-proof) and
// the backend validate gate is the final authority.
const RUNTIME_CAPABILITY_VOCABULARY = [
  "tts",
  "voice_cloning",
  "multilingual",
  "voice_conversion",
  "emotion_tags",
  "voice_design",
  "reference_audio",
  "batch_generation",
  "speaker_embeddings",
  "custom_training",
  "singing",
  "streaming",
  "emotions",
] as const;

// ---------------------------------------------------------------------------
// RuntimeVariant presentation (ADR-0018 Phase 3; Task 27 Phase C).
//
// A runtime exposes one-or-more variants (checkpoints / specializations) under
// a single runtime image. This section lets the user *view* installed variants,
// see which is the default, inspect declared capabilities, distinguish
// Verified from Community provenance, and start a Hugging Face import (which is
// validate-only today — the safe foundation of the full import flow).
//
// It NEVER surfaces checkpoint internals (paths/formats/digests) — ADR-0004 §6.
// ---------------------------------------------------------------------------

const SOURCE_LABEL: Record<ComposedRuntimeVariant["source_type"], string> = {
  bundled: "Bundled with runtime",
  hf: "Hugging Face",
  url: "URL",
  local: "Local",
};

function TrustBadge({ trust }: { trust: RuntimeVariantTrust }) {
  if (trust === "verified") {
    return (
      <Badge
        variant="secondary"
        className="gap-1 rounded-md bg-success/15 text-success hover:bg-success/20"
        title="Curated by PeakVox: tested end-to-end with a known checkpoint source."
      >
        <BadgeCheck className="h-3 w-3" /> Verified
      </Badge>
    );
  }
  return (
    <Badge
      variant="secondary"
      className="gap-1 rounded-md bg-warning/15 text-warning hover:bg-warning/20"
      title="User-imported: compatibility was checked but PeakVox has not validated this model. Use at your own risk."
    >
      <AlertTriangle className="h-3 w-3" /> Community
    </Badge>
  );
}

function VariantCard({ variant }: { variant: ComposedRuntimeVariant }) {
  return (
    <div className="rounded-md border border-border bg-surface-2 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center gap-1.5">
            <p className="text-sm font-medium truncate">{variant.name}</p>
            {variant.is_default && (
              <span title="Default variant — used when no other is selected.">
                <Star className="h-3.5 w-3.5 text-primary fill-primary" />
              </span>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground font-mono">
            {variant.id}
          </p>
        </div>
        <TrustBadge trust={variant.trust} />
      </div>

      {variant.description && (
        <p className="text-xs text-muted-foreground">{variant.description}</p>
      )}

      <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span>{SOURCE_LABEL[variant.source_type]}</span>
        {variant.source_url && (
          <a
            href={variant.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline truncate max-w-[180px]"
          >
            {variant.source_url.replace(/^https?:\/\//, "")}
          </a>
        )}
      </div>

      {variant.capabilities.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {variant.capabilities.map((c) => (
            <Badge
              key={c}
              variant="secondary"
              className="rounded bg-primary/10 text-primary text-[10px] hover:bg-primary/15"
            >
              {c}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Capability picker — searchable, multi-select, removable tags, keyboard
// friendly. Options come from the platform vocabulary; custom capabilities are
// allowed (type + Enter / "Add"). Pre-populated with the runtime's capabilities.
// ---------------------------------------------------------------------------
function CapabilityPicker({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  function toggle(cap: string) {
    onChange(
      selected.includes(cap)
        ? selected.filter((c) => c !== cap)
        : [...selected, cap],
    );
  }

  function remove(cap: string) {
    onChange(selected.filter((c) => c !== cap));
  }

  const normalizedQuery = query.trim().toLowerCase();
  const options = RUNTIME_CAPABILITY_VOCABULARY.filter((c) =>
    c.includes(normalizedQuery),
  );
  // Offer a custom entry when the typed value is novel (not a vocabulary
  // member and not already selected).
  const canAddCustom =
    normalizedQuery.length > 0 &&
    !RUNTIME_CAPABILITY_VOCABULARY.includes(
      normalizedQuery as (typeof RUNTIME_CAPABILITY_VOCABULARY)[number],
    ) &&
    !selected.includes(normalizedQuery);

  function addCustom() {
    if (!canAddCustom) return;
    onChange([...selected, normalizedQuery]);
    setQuery("");
  }

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1 rounded-md border border-border bg-surface-2 p-1.5 min-h-9">
        {selected.length === 0 && (
          <span className="px-1 py-0.5 text-xs text-muted-foreground">
            No capabilities selected
          </span>
        )}
        {selected.map((cap) => (
          <Badge
            key={cap}
            variant="secondary"
            className="gap-1 rounded text-[11px] hover:bg-primary/15 cursor-pointer"
            onClick={() => remove(cap)}
          >
            {cap}
            <button
              type="button"
              aria-label={`Remove ${cap}`}
              className="rounded-sm hover:bg-primary/20"
              onClick={() => remove(cap)}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 w-full justify-start gap-1.5 text-muted-foreground"
          >
            <Plus className="h-3.5 w-3.5" /> Add capability
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-[var(--radix-popover-trigger-width)] p-0"
          align="start"
        >
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search or type a custom capability…"
              value={query}
              onValueChange={setQuery}
              onKeyDown={(e) => {
                if (e.key === "Enter" && canAddCustom) {
                  e.preventDefault();
                  addCustom();
                }
              }}
            />
            <CommandList>
              {options.length === 0 && !canAddCustom && (
                <CommandEmpty>No capabilities found.</CommandEmpty>
              )}
              {options.length > 0 && (
                <CommandGroup heading="Platform capabilities">
                  {options.map((cap) => {
                    const isSelected = selected.includes(cap);
                    return (
                      <CommandItem
                        key={cap}
                        value={cap}
                        onSelect={() => toggle(cap)}
                      >
                        <Check
                          className={cn(
                            "h-3.5 w-3.5",
                            isSelected ? "opacity-100" : "opacity-0",
                          )}
                        />
                        {cap}
                      </CommandItem>
                    );
                  })}
                </CommandGroup>
              )}
              {canAddCustom && (
                <CommandGroup heading="Custom">
                  <CommandItem
                    value={`__add__${normalizedQuery}`}
                    onSelect={addCustom}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Add &ldquo;{normalizedQuery}&rdquo;
                  </CommandItem>
                </CommandGroup>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Import dialog — validate-only (Phase 6 foundation). Download + register are
// a follow-up phase; the dialog is explicit that it checks compatibility only.
//
// The runtime context (provider + declared capabilities) is already known from
// the card the dialog was opened on, so provider is read-only and capabilities
// are pre-selected from the runtime — the user never re-types them.
// ---------------------------------------------------------------------------
function ImportVariantDialog({
  runtimeId,
  runtimeProvider,
  runtimeName,
  runtimeCapabilities,
}: {
  runtimeId: string;
  runtimeProvider: string;
  runtimeName: string;
  runtimeCapabilities: string[];
}) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  // Capabilities default to the runtime's declared set; the user may adjust.
  const [capabilities, setCapabilities] =
    useState<string[]>(runtimeCapabilities);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VariantImportValidation | null>(null);

  async function onValidate() {
    setPending(true);
    setError(null);
    setResult(null);
    try {
      const res = await validateVariantImport(runtimeId, {
        // Provider is derived from the runtime the dialog was opened on.
        url,
        declared_provider: runtimeProvider || undefined,
        declared_capabilities: capabilities.length ? capabilities : undefined,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Validation failed");
    } finally {
      setPending(false);
    }
  }

  function reset() {
    setUrl("");
    setCapabilities(runtimeCapabilities);
    setResult(null);
    setError(null);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Sparkles className="h-3.5 w-3.5" /> Add variant from Hugging Face
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import a community variant</DialogTitle>
          <DialogDescription>
            Attach a Hugging Face checkpoint to this runtime as a new variant —
            no new image, no rebuild. This step{" "}
            <strong>validates compatibility only</strong>; download and
            registration come next.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="variant-url">Hugging Face URL or repo id</Label>
            <Input
              id="variant-url"
              placeholder="https://huggingface.co/firstpixel/F5-TTS-pt-br"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="variant-provider">Provider</Label>
            <Input
              id="variant-provider"
              value={runtimeName || runtimeProvider}
              readOnly
              disabled
              className="text-muted-foreground"
            />
            <p className="text-[11px] text-muted-foreground">
              Derived from the runtime (
              <span className="font-mono">{runtimeProvider}</span>).
            </p>
          </div>
          <div className="space-y-1.5">
            <Label>Capabilities</Label>
            <CapabilityPicker
              selected={capabilities}
              onChange={setCapabilities}
            />
            <p className="text-[11px] text-muted-foreground">
              Pre-filled from the runtime. A variant may declare a subset; it
              can never exceed the runtime&apos;s capabilities.
            </p>
          </div>

          {error && <p className="text-xs text-error">{error}</p>}

          {result && (
            <div
              className={cn(
                "rounded-md border p-3 space-y-2 text-sm",
                result.compatible
                  ? "border-success/40 bg-success/10"
                  : "border-error/40 bg-error/10",
              )}
            >
              <div className="flex items-center gap-1.5 font-medium">
                {result.compatible ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-success" />
                    <span className="text-success">Compatible</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-error" />
                    <span className="text-error">Not compatible</span>
                  </>
                )}
                <TrustBadge trust={result.trust} />
              </div>
              <p className="text-xs text-muted-foreground">
                Repo <span className="font-mono">{result.repo_id}</span> →
                variant{" "}
                <span className="font-mono">{result.proposed_variant_id}</span>
              </p>
              {result.reasons.length > 0 && (
                <ul className="list-disc pl-4 text-xs text-error space-y-0.5">
                  {result.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
              {result.warnings.length > 0 && (
                <ul className="list-disc pl-4 text-xs text-warning space-y-0.5">
                  {result.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              )}
              {result.compatible && (
                <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Download className="h-3 w-3" /> Download &amp; register is
                  coming in a follow-up — the checkpoint passes the
                  compatibility gates.
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
            Close
          </Button>
          <Button
            size="sm"
            onClick={onValidate}
            disabled={pending || !url.trim()}
          >
            {pending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Validate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function VariantsSection({
  runtimeId,
  runtimeProvider,
  runtimeName,
  runtimeCapabilities,
  variants,
}: {
  runtimeId: string;
  runtimeProvider: string;
  runtimeName: string;
  runtimeCapabilities: string[];
  variants: ComposedRuntimeVariant[] | undefined;
}) {
  // A runtime with no explicit variants is a valid single-`base` runtime; the
  // runtime card already represents it. Only show the section when there is
  // something variant-specific to manage.
  const list = variants ?? [];

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-2">
        <p className="text-caption uppercase tracking-wide flex items-center gap-1.5">
          <Layers className="h-3 w-3" /> Variants
          {list.length > 0 && (
            <span className="text-muted-foreground normal-case">
              ({list.length})
            </span>
          )}
        </p>
        <ImportVariantDialog
          runtimeId={runtimeId}
          runtimeProvider={runtimeProvider}
          runtimeName={runtimeName}
          runtimeCapabilities={runtimeCapabilities}
        />
      </div>

      {list.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          Single base runtime — no additional variants installed. Import a
          Hugging Face checkpoint to add a specialization (e.g. a language or
          style) without a new image.
        </p>
      ) : (
        <div className="space-y-2">
          {list.map((v) => (
            <VariantCard key={v.id} variant={v} />
          ))}
        </div>
      )}
    </div>
  );
}
