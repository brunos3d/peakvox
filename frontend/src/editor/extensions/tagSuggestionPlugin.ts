import { Extension, type Editor } from "@tiptap/core";
import { PluginKey } from "@tiptap/pm/state";
import Suggestion from "@tiptap/suggestion";
import { ReactRenderer } from "@tiptap/react";
import tippy, { type Instance as TippyInstance } from "tippy.js";
import "tippy.js/dist/tippy.css";
import { EmotionPicker, type EmotionPickerRef } from "@/editor/emotion-picker";
import { type TagMenuItem } from "@/editor/useTagMenuItems";
import { EmotionTag } from "./EmotionTag";

export interface TagSuggestionOptions {
  char: string;
  pluginKey?: PluginKey;
}

export const tagItemsRef: { current: (query: string) => TagMenuItem[] } = {
  current: () => [],
};

export const TagSuggestionExtension = Extension.create<TagSuggestionOptions>({
  name: "tagSuggestion",

  addOptions() {
    return {
      char: "/",
      pluginKey: undefined as PluginKey | undefined,
    };
  },

  addProseMirrorPlugins() {
    const pluginKey = this.options.pluginKey ?? new PluginKey(`tag-suggestion-${this.options.char}`);

    return [
      Suggestion({
        editor: this.editor,
        char: this.options.char,
        pluginKey,
        command: ({ editor, range, props }) => {
          const item = props as TagMenuItem;
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
          let component: ReactRenderer<EmotionPickerRef>;
          let popup: TippyInstance[];

          return {
            onStart: (props) => {
              component = new ReactRenderer(EmotionPicker, {
                editor: props.editor as Editor,
                props: {
                  items: props.items as TagMenuItem[],
                  onSelect: (tagId: string) => {
                    const item = (props.items as TagMenuItem[]).find((i) => i.id === tagId);
                    if (item) props.command(item);
                  },
                },
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
              component.updateProps({
                items: props.items as TagMenuItem[],
                onSelect: (tagId: string) => {
                  const item = (props.items as TagMenuItem[]).find((i) => i.id === tagId);
                  if (item) props.command(item);
                },
              });

              popup[0]?.setProps({
                getReferenceClientRect: props.clientRect as () => DOMRect,
              });
            },

            onKeyDown: (props) => {
              if (props.event.key === "Escape") {
                popup[0]?.hide();
                return true;
              }
              if (props.event.key === "Tab") {
                if (!props.event.shiftKey) {
                  popup[0]?.hide();
                  return false;
                }
              }
              return component.ref?.onKeyDown(props.event) ?? false;
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
