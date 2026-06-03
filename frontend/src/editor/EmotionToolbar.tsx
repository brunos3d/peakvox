"use client";

import { useState, useCallback } from "react";
import { Plus } from "lucide-react";
import type { Editor } from "@tiptap/core";
import { EmotionTag } from "@/editor/extensions/EmotionTag";
import { useTagMenuItems } from "@/editor/useTagMenuItems";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

const COMMON_TAG_IDS = [
  "happy",
  "sad",
  "angry",
  "whisper",
  "calm",
  "excited",
  "singing",
  "laughter",
];

function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
    emotion: "Emotions",
    delivery: "Delivery",
    vocal: "Vocal",
    reaction: "Reactions",
    question: "Questions",
    surprise: "Surprise",
  };
  return labels[category] ?? category.charAt(0).toUpperCase() + category.slice(1);
}

interface EmotionToolbarProps {
  editor: Editor | null;
}

export function EmotionToolbar({ editor }: EmotionToolbarProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const { items, grouped } = useTagMenuItems();

  const insertTag = useCallback(
    (tagId: string) => {
      if (!editor) return;
      editor.chain().focus().insertContent({
        type: EmotionTag.name,
        attrs: { tagId, modelId: "omnivoice-base", invalid: false },
      }).run();
      setOpen(false);
      setSearch("");
    },
    [editor],
  );

  const commonChips = COMMON_TAG_IDS
    .map((id) => items.find((i) => i.id === id))
    .filter((item): item is NonNullable<typeof item> => item != null);

  const filtered = search
    ? items.filter(
        (item) =>
          item.label.toLowerCase().includes(search.toLowerCase()) ||
          item.id.toLowerCase().includes(search.toLowerCase()),
      )
    : [];

  const filteredGrouped = search
    ? (() => {
        const map = new Map<string, typeof filtered>();
        for (const item of filtered) {
          const cat = item.category;
          if (!map.has(cat)) map.set(cat, []);
          map.get(cat)!.push(item);
        }
        return Array.from(map.entries()).map(([cat, catItems]) => ({
          label: categoryLabel(cat),
          items: catItems,
        }));
      })()
    : grouped;

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-5 py-2">
      {commonChips.map((item) => (
        <button
          key={item.id}
          type="button"
          className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
          onClick={() => insertTag(item.id)}
          title={item.description}
        >
          <span>{item.emoji}</span>
          <span>{item.label}</span>
        </button>
      ))}

      <Popover open={open} onOpenChange={(next) => { setOpen(next); if (!next) setSearch(""); }}>
        <PopoverAnchor asChild>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            onClick={() => setOpen((o) => !o)}
          >
            <Plus className="h-3 w-3" />
            Insert
          </button>
        </PopoverAnchor>
        <PopoverContent className="w-72 p-0" align="start" sideOffset={5}>
          <Command loop>
            <CommandInput
              placeholder="Search emotions…"
              value={search}
              onValueChange={setSearch}
            />
            <CommandList className="max-h-64">
              <CommandEmpty>No matching emotions.</CommandEmpty>
              {filteredGrouped.map((group) => (
                <CommandGroup key={group.label} heading={group.label}>
                  {group.items.map((item) => (
                    <CommandItem
                      key={item.id}
                      value={item.id}
                      keywords={[item.label, item.id]}
                      onSelect={() => insertTag(item.id)}
                    >
                      <span className="mr-2">{item.emoji}</span>
                      <span className="flex-1">{item.label}</span>
                      <span className="text-[10px] text-muted-foreground">[{item.id}]</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              ))}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}
