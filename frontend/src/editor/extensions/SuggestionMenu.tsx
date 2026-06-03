"use client";

import { forwardRef, useEffect, useImperativeHandle, useState, useCallback } from "react";
import { cn } from "@/lib/utils";

export interface SuggestionMenuItem {
  id: string;
  label: string;
  emoji: string;
  description: string;
}

interface SuggestionMenuRef {
  onKeyDown: (props: { event: KeyboardEvent }) => boolean;
}

interface SuggestionMenuProps {
  items: SuggestionMenuItem[];
  command: (item: SuggestionMenuItem) => void;
}

const SuggestionMenu = forwardRef<SuggestionMenuRef, SuggestionMenuProps>(
  ({ items, command }, ref) => {
    const [selectedIndex, setSelectedIndex] = useState(0);

    useEffect(() => {
      setSelectedIndex(0);
    }, [items]);

    const selectItem = useCallback(
      (index: number) => {
        const item = items[index];
        if (item) command(item);
      },
      [items, command],
    );

    useImperativeHandle(ref, () => ({
      onKeyDown: ({ event }) => {
        if (event.key === "ArrowUp") {
          setSelectedIndex((i) => (i + items.length - 1) % items.length);
          return true;
        }
        if (event.key === "ArrowDown") {
          setSelectedIndex((i) => (i + 1) % items.length);
          return true;
        }
        if (event.key === "Enter") {
          selectItem(selectedIndex);
          return true;
        }
        if (event.key === "Tab") {
          selectItem(selectedIndex);
          return true;
        }
        if (event.key === "Escape") {
          return false;
        }
        return false;
      },
    }));

    if (items.length === 0) return null;

    return (
      <div className="w-64 rounded-lg border border-border bg-popover p-1 shadow-lg">
        {items.map((item, index) => (
          <button
            key={item.id}
            className={cn(
              "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors",
              index === selectedIndex
                ? "bg-accent text-accent-foreground"
                : "text-popover-foreground hover:bg-accent/50",
            )}
            onClick={() => selectItem(index)}
            onMouseEnter={() => setSelectedIndex(index)}
          >
            <span className="shrink-0 text-base">{item.emoji}</span>
            <span className="flex-1 truncate">{item.label}</span>
            <span className="shrink-0 text-[10px] text-muted-foreground">
              [{item.id}]
            </span>
          </button>
        ))}
      </div>
    );
  },
);

SuggestionMenu.displayName = "SuggestionMenu";

export default SuggestionMenu;
