const TAG_RE = /\[([a-z0-9][a-z0-9-]*)\]/g;

export type ModelInfo = { id: string; supported_tags: string[] };

export type EditorDoc = {
  type: "doc";
  content: EditorBlock[];
};

type EditorBlock = {
  type: "paragraph";
  content: EditorInline[];
};

type EditorInline =
  | { type: "text"; text: string }
  | { type: "emotionTag"; attrs: { tagId: string; modelId: string; invalid: boolean } };

export function parseOmniVoiceText(text: string, model: ModelInfo): EditorDoc {
  const lines = text.split("\n");
  return {
    type: "doc",
    content: lines.map((line) => ({ type: "paragraph", content: parseInline(line, model) })),
  };
}

function parseInline(line: string, model: ModelInfo): EditorInline[] {
  const out: EditorInline[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  TAG_RE.lastIndex = 0;
  while ((m = TAG_RE.exec(line)) !== null) {
    if (m.index > last) out.push({ type: "text", text: line.slice(last, m.index) });
    const tagId = m[1];
    out.push({
      type: "emotionTag",
      attrs: {
        tagId,
        modelId: model.id,
        invalid: !model.supported_tags.includes(tagId),
      },
    });
    last = m.index + m[0].length;
  }
  if (last < line.length) out.push({ type: "text", text: line.slice(last) });
  return out;
}
