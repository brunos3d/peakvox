import { Extension, type Editor, type Range } from "@tiptap/core";
import Suggestion from "@tiptap/suggestion";
import { ReactRenderer } from "@tiptap/react";
import tippy, { type Instance as TippyInstance } from "tippy.js";
import "tippy.js/dist/tippy.css";
import SuggestionMenu, { type SuggestionMenuItem } from "./SuggestionMenu";
import { type TagMenuItem } from "@/editor/useTagMenuItems";
import { tagById } from "@/editor/tags";
import { EmotionTag } from "./EmotionTag";

export interface TagSuggestionOptions {
  char: string;
  pluginKey?: string;
}

/**
 * Shared mutable reference updated by the React component whenever the
 * tag catalog changes. The Suggestion plugin reads this each time the
 * popup opens, so it always has the latest items.
 */
export const tagItemsRef: { current: (query: string) => TagMenuItem[] } = {
  current: () => [],
};

export const TagSuggestionExtension = Extension.create<TagSuggestionOptions>({
  name: "tagSuggestion",

  addOptions() {
    return {
      char: "/",
      pluginKey: "tag-suggestion",
    };
  },

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        char: this.options.char,
        pluginKey: this.options.pluginKey ?? `tag-suggestion-${this.options.char}`,
        command: ({ editor, range, props }) => {
          const item = props as SuggestionMenuItem;
          editor
            .chain()
            .focus()
            .deleteRange(range)
            .insertContent({
              type: EmotionTag.name,
              attrs: {
                tagId: item.id,
                modelId: "omnivoice-base",
                invalid: false,
              },
            })
            .run();
        },
        items: ({ query }) => {
          return tagItemsRef.current(query);
        },
        render: () => {
          let component: ReactRenderer<SuggestionMenu>;
          let popup: TippyInstance[];

          return {
            onStart: (props) => {
              component = new ReactRenderer(SuggestionMenu, {
                editor: props.editor as Editor,
                props: props,
              });

              if (!props.clientRect) return;

              popup = tippy("body", {
                getReferenceClientRect: props.clientRect as () => DOMRect,
                appendTo: () => document.body,
                content: component.element,
                showOnCreate: true,
                interactive: true,
                trigger: "manual",
                placement: "bottom-start",
                maxWidth: 300,
              });
            },

            onUpdate: (props) => {
              component.updateProps(props);

              popup[0]?.setProps({
                getReferenceClientRect: props.clientRect as () => DOMRect,
              });
            },

            onKeyDown: (props) => {
              if (props.event.key === "Escape") {
                popup[0]?.hide();
                return true;
              }
              if (props.event.key === "Enter" || props.event.key === "Tab") {
                if (props.event.key === "Tab" && !props.event.shiftKey) {
                  popup[0]?.hide();
                  return false;
                }
              }
              return component.ref?.onKeyDown(props) ?? false;
            },

            onExit: () => {
              popup[0]?.destroy();
              component.destroy();
            },
          };
        },
      }),
    ];
  },
});
