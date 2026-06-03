import { useMemo } from "react";
import { useActiveModel } from "@/hooks/use-models";
import type { ModelTagMetadata } from "@/types";

export interface TagMenuItem {
  id: string;
  label: string;
  emoji: string;
  category: string;
  description: string;
}

function toMenuItem(tag: ModelTagMetadata): TagMenuItem {
  return {
    id: tag.id,
    label: tag.label,
    emoji: tag.emoji,
    category: tag.category,
    description: tag.description,
  };
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
  return labels[category] ?? category.charAt(0).toUpperCase() + category.slice(1);
}

export function useTagMenuItems(): {
  items: TagMenuItem[];
  grouped: { label: string; items: TagMenuItem[] }[];
  getFiltered: (query: string) => TagMenuItem[];
} {
  const { tags } = useActiveModel();

  return useMemo(() => {
    const items = tags.map(toMenuItem);

    const groupedMap = new Map<string, TagMenuItem[]>();
    for (const item of items) {
      const cat = item.category;
      if (!groupedMap.has(cat)) groupedMap.set(cat, []);
      groupedMap.get(cat)!.push(item);
    }
    const grouped = Array.from(groupedMap.entries()).map(([cat, catItems]) => ({
      label: categoryLabel(cat),
      items: catItems,
    }));

    const getFiltered = (query: string) => {
      const lower = query.toLowerCase();
      return items.filter(
        (item) =>
          item.label.toLowerCase().includes(lower) ||
          item.id.toLowerCase().includes(lower),
      );
    };

    return { items, grouped, getFiltered };
  }, [tags]);
}
