"use client";

import { useEffect, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { EmotionTag } from "@/editor/extensions/EmotionTag";
import { EmotionToolbar } from "@/editor/EmotionToolbar";
import { serializeToOmniVoice } from "@/editor/serialize";
import {
  TagSuggestionExtension,
  tagItemsRef,
} from "@/editor/extensions/tagSuggestionPlugin";
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
  placeholder = "Type or paste text to generate speech…",
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
      Placeholder.configure({
        placeholder,
      }),
      EmotionTag,
      TagSuggestionExtension.configure({ char: "/" }),
      TagSuggestionExtension.configure({ char: "[" }),
    ],
    editorProps: {
      attributes: {
        class: "focus:outline-none",
      },
    },
    onUpdate: ({ editor: ed }) => {
      if (isUpdatingFromOutside.current) return;
      const doc = ed.state.doc.toJSON() as Parameters<
        typeof serializeToOmniVoice
      >[0];
      onChange(serializeToOmniVoice(doc));
    },
    immediatelyRender: false,
  });

  useEffect(() => {
    tagItemsRef.current = getFiltered;
  }, [getFiltered]);

  useEffect(() => {
    if (!editor) return;
    const currentText = serializeToOmniVoice(
      editor.state.doc.toJSON() as Parameters<typeof serializeToOmniVoice>[0],
    );
    if (value !== currentText) {
      isUpdatingFromOutside.current = true;
      editor.commands.setContent(
        [{ type: "paragraph", content: [{ type: "text", text: value }] }],
        { emitUpdate: true },
      );
      isUpdatingFromOutside.current = false;
    }
  }, [value, editor]);

  const charCount = value.length;

  return (
    <div className={className}>
      {/* Editor is the primary surface */}
      <EditorContent editor={editor} className="flex flex-col flex-1 h-max" />

      {/* Character count + emotion toolbar live below the editor */}
      <div className="mt-3 flex items-center justify-between">
        <div className="mt-4 text-xs leading-relaxed text-muted-foreground/50">
          Type naturally. Use{" "}
          <kbd className="rounded border border-border bg-surface px-1 font-mono text-[11px]">
            /
          </kbd>{" "}
          or{" "}
          <kbd className="rounded border border-border bg-surface px-1 font-mono text-[11px]">
            [
          </kbd>{" "}
          to insert reactions and emotions.
        </div>
        <span className="text-xs text-muted-foreground">
          {charCount} character{charCount !== 1 ? "s" : ""}
        </span>
      </div>

      {editor && (
        <div className="mt-3">
          <EmotionToolbar editor={editor} />
        </div>
      )}
    </div>
  );
}
