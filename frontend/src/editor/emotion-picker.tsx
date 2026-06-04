"use client";

import { forwardRef, useImperativeHandle, useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { CommandGroup, CommandItem } from "@/components/ui/command";
import type { TagMenuItem } from "@/editor/useTagMenuItems";

export interface EmotionPickerRef {
  onKeyDown: (event: KeyboardEvent) => boolean;
}

interface GroupedItemListProps {
  items: TagMenuItem[];
  onSelect: (tagId: string) => void;
  selectedIndex: number;
  onSelectedIndexChange: (index: number) => void;
}

function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
    emotion: "Emotions",
    delivery: "Delivery",
    vocal: "Vocal",
    reaction: "Reactions",
    question: "Questions",
    surprise: "Surprise",
  };
  return (
    labels[category] ?? category.charAt(0).toUpperCase() + category.slice(1)
  );
}

function GroupedItemList({
  items,
  onSelect,
  selectedIndex,
  onSelectedIndexChange,
}: GroupedItemListProps) {
  const groups = useMemo(() => {
    const map = new Map<string, TagMenuItem[]>();
    for (const item of items) {
      const cat = item.category;
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(item);
    }
    return Array.from(map.entries()).map(([cat, catItems]) => ({
      category: cat,
      label: categoryLabel(cat),
      items: catItems,
    }));
  }, [items]);

  if (items.length === 0) return null;

  let globalIndex = 0;

  return (
    <div className="w-64">
      {groups.map((group) => (
        <div key={group.category}>
          <div className="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {group.label}
          </div>
          {group.items.map((item) => {
            const idx = globalIndex++;
            return (
              <button
                key={item.id}
                type="button"
                className={cn(
                  "flex w-full cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors",
                  idx === selectedIndex
                    ? "bg-background text-foreground"
                    : "text-popover-foreground hover:bg-accent",
                )}
                onClick={() => onSelect(item.id)}
                onMouseEnter={() => onSelectedIndexChange(idx)}
              >
                <span className="shrink-0 text-base">{item.emoji}</span>
                <span className="flex-1 truncate">{item.label}</span>
                <span className="shrink-0 text-[10px] text-muted-foreground">
                  [{item.id}]
                </span>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/**
 * Unified emotion picker that renders a grouped, keyboard-navigable list of emotion tags.
 *
 * Can be used in two contexts:
 * - **Popover context (EmotionToolbar):** wrap in `<Popover>` + `<Command>`.
 *    The `CommandInput` provides search filtering, and the picker receives
 *    the pre-filtered `items` array. `Command` handles keyboard natively.
 * - **Tippy context (slash commands):** render inside a `ReactRenderer`.
 *    The `onKeyDown` imperative ref integrates with `@tiptap/suggestion`'s
 *    keyboard handling. No search input needed — the plugin's query text
 *    provides the filter.
 */
export const EmotionPicker = forwardRef<
  EmotionPickerRef,
  {
    items: TagMenuItem[];
    onSelect: (tagId: string) => void;
  }
>(({ items, onSelect }, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useImperativeHandle(ref, () => ({
    onKeyDown: (event: KeyboardEvent) => {
      if (event.key === "ArrowUp") {
        setSelectedIndex((i) => (i + items.length - 1) % items.length);
        return true;
      }
      if (event.key === "ArrowDown") {
        setSelectedIndex((i) => (i + 1) % items.length);
        return true;
      }
      if (event.key === "Enter") {
        const item = items[selectedIndex];
        if (item) onSelect(item.id);
        return true;
      }
      if (event.key === "Tab") {
        const item = items[selectedIndex];
        if (item) onSelect(item.id);
        return true;
      }
      return false;
    },
  }));

  return (
    <GroupedItemList
      items={items}
      onSelect={onSelect}
      selectedIndex={selectedIndex}
      onSelectedIndexChange={setSelectedIndex}
    />
  );
});

EmotionPicker.displayName = "EmotionPicker";

/**
 * Command-item variant of the picker — for use inside shadcn `<Command>`.
 * Renders grouped `CommandGroup` + `CommandItem` entries directly in the
 * Command list, leveraging Command's built-in keyboard navigation.
 */
export function EmotionPickerItems({
  items,
  onSelect,
}: {
  items: TagMenuItem[];
  onSelect: (tagId: string) => void;
}) {
  const groups = useMemo(() => {
    const map = new Map<string, TagMenuItem[]>();
    for (const item of items) {
      const cat = item.category;
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(item);
    }
    return Array.from(map.entries()).map(([cat, catItems]) => ({
      category: cat,
      label: categoryLabel(cat),
      items: catItems,
    }));
  }, [items]);

  if (items.length === 0) return null;

  return (
    <>
      {groups.map((group) => (
        <CommandGroup key={group.category} heading={group.label}>
          {group.items.map((item) => (
            <CommandItem
              key={item.id}
              value={item.id}
              keywords={[item.label, item.id]}
              onSelect={() => onSelect(item.id)}
            >
              <span className="mr-2">{item.emoji}</span>
              <span className="flex-1">{item.label}</span>
              <span className="text-[10px] text-muted-foreground">
                [{item.id}]
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
      ))}
    </>
  );
}
