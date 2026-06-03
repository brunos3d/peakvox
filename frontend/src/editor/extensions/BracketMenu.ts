import { TagSuggestionExtension } from "./tagSuggestionPlugin";
import type { TagMenuItem } from "@/editor/useTagMenuItems";

export interface BracketMenuOptions {
  getItems: (query: string) => TagMenuItem[];
}

export const BracketMenu = TagSuggestionExtension.extend<BracketMenuOptions>({
  name: "bracketMenu",

  addOptions() {
    return {
      ...this.parent?.(),
      char: "[",
      pluginKey: "bracket-menu",
      getItems: (query: string) => {
        return this.options.getItems(query);
      },
    };
  },
});
