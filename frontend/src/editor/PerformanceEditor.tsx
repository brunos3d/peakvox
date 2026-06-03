"use client";

import { useEffect, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { EmotionTag } from "@/editor/extensions/EmotionTag";
import { EmotionToolbar } from "@/editor/EmotionToolbar";
import { serializeToOmniVoice } from "@/editor/serialize";
import { TagSuggestionExtension, tagItemsRef } from "@/editor/extensions/tagSuggestionPlugin";
import { useTagMenuItems } from "@/editor/useTagMenuItems";

interface PerformanceEditorProps {
  value: string;
  onChange: (text: string) => void;
  placeholder?: string;
  className?: string;
}

export function PerformanceEditor({
  value,
  onChange,
  placeholder = "Direct a voice performance...",
  className = "",
}: PerformanceEditorProps) {
  const isUpdatingFromOutside = useRef(false);
  const { getFiltered } = useTagMenuItems();

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        bold: false,
        italic: false,
        strike: false,
        code: false,
        heading: false,
        blockquote: false,
        codeBlock: false,
        horizontalRule: false,
        listItem: false,
        bulletList: false,
        orderedList: false,
      }),
      Placeholder.configure({ placeholder }),
      EmotionTag,
      TagSuggestionExtension.configure({
        char: "/",
      }),
      TagSuggestionExtension.configure({
        char: "[",
      }),
    ],
    editorProps: {
      attributes: {
        class: "focus:outline-none",
      },
    },
    onUpdate: ({ editor: ed }) => {
      if (isUpdatingFromOutside.current) return;
      const doc = ed.state.doc.toJSON() as Parameters<typeof serializeToOmniVoice>[0];
      const text = serializeToOmniVoice(doc);
      onChange(text);
    },
    immediatelyRender: false,
  });

  // Keep the shared tagItemsRef in sync so the suggestion plugin always has
  // the latest items from the active model's tag catalog.
  useEffect(() => {
    tagItemsRef.current = getFiltered;
  }, [getFiltered]);

  // Sync external value to editor when it changes (e.g., Regenerate prefill)
  useEffect(() => {
    if (!editor) return;
    const currentText = serializeToOmniVoice(editor.state.doc.toJSON() as Parameters<typeof serializeToOmniVoice>[0]);
    if (value !== currentText) {
      isUpdatingFromOutside.current = true;
      editor.commands.setContent(
        [
          {
            type: "paragraph",
            content: [{ type: "text", text: value }],
          },
        ],
        { emitUpdate: true },
      );
      isUpdatingFromOutside.current = false;
    }
  }, [value, editor]);

  const charCount = value.length;

  return (
    <div className={className}>
      {editor && <EmotionToolbar editor={editor} />}
      <EditorContent editor={editor} />
      <div className="flex items-center justify-between px-5 py-2 text-xs text-muted-foreground">
        <span>{charCount} character{charCount !== 1 ? "s" : ""}</span>
      </div>
    </div>
  );
}
