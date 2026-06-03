import { TagSuggestionExtension } from "./tagSuggestionPlugin";
import type { TagMenuItem } from "@/editor/useTagMenuItems";

export interface SlashMenuOptions {
  getItems: (query: string) => TagMenuItem[];
}

export const SlashMenu = TagSuggestionExtension.extend<SlashMenuOptions>({
  name: "slashMenu",

  addOptions() {
    return {
      ...this.parent?.(),
      char: "/",
      pluginKey: "slash-menu",
      getItems: (query: string) => {
        return this.options.getItems(query);
      },
    };
  },
});
