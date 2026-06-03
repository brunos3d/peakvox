"use client";

import { useMemo } from "react";
import { useTagMenuItems } from "@/editor/useTagMenuItems";
import { useAppStore } from "@/store/use-store";

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

export function EmotionSettings() {
  const { items } = useTagMenuItems();
  const setTtsText = useAppStore((s) => s.setTtsText);
  const ttsText = useAppStore((s) => s.ttsText);

  const groups = useMemo(() => {
    const map = new Map<string, typeof items>();
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

  const addTag = (tagId: string) => {
    const suffix = `[${tagId}]`;
    const separator = ttsText.length > 0 && !ttsText.endsWith(" ") ? " " : "";
    setTtsText(`${ttsText}${separator}${suffix}`);
  };

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <div key={group.category}>
          <h4 className="mb-1.5 text-xs font-medium text-muted-foreground">
            {group.label}
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {group.items.map((item) => (
              <button
                key={item.id}
                type="button"
                className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs transition-colors hover:bg-accent hover:text-accent-foreground"
                onClick={() => addTag(item.id)}
                title={item.description}
              >
                <span>{item.emoji}</span>
                <span>{item.label}</span>
                <span className="text-[10px] text-muted-foreground">[{item.id}]</span>
              </button>
            ))}
          </div>
        </div>
      ))}
      {items.length === 0 && (
        <p className="text-xs text-muted-foreground">No emotions cataloged for this model.</p>
      )}
    </div>
  );
}
