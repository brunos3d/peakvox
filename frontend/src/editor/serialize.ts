export type DocNode = {
  type: string;
  text?: string;
  attrs?: Record<string, unknown>;
  content?: DocNode[];
};

export function serializeToOmniVoice(doc: DocNode): string {
  const paragraphs = (doc.content ?? []).map(serializeBlock);
  return paragraphs.join("\n");
}

function serializeBlock(node: DocNode): string {
  return (node.content ?? []).map(serializeInline).join("");
}

function serializeInline(node: DocNode): string {
  if (node.type === "text") return node.text ?? "";
  if (node.type === "emotionTag") return `[${String(node.attrs?.tagId ?? "")}]`;
  if (node.type === "hardBreak") return "\n";
  return "";
}
