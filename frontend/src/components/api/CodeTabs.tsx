"use client"

import { useState } from "react"
import { Copy, Check } from "lucide-react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import type { CodeExample } from "@/lib/api-examples"

/** Tabbed, copy-to-clipboard code samples (cURL / JavaScript / Python). */
export function CodeTabs({ examples }: { examples: CodeExample[] }) {
  const [copied, setCopied] = useState<string | null>(null)

  const copy = (code: string, lang: string) => {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(lang)
      setTimeout(() => setCopied((c) => (c === lang ? null : c)), 1500)
    })
  }

  return (
    <Tabs defaultValue={examples[0]?.language}>
      <TabsList>
        {examples.map((ex) => (
          <TabsTrigger key={ex.language} value={ex.language}>{ex.language}</TabsTrigger>
        ))}
      </TabsList>
      {examples.map((ex) => (
        <TabsContent key={ex.language} value={ex.language} className="relative">
          <Button
            variant="secondary"
            size="icon"
            className="absolute right-2 top-2 h-7 w-7"
            onClick={() => copy(ex.code, ex.language)}
            title="Copy"
          >
            {copied === ex.language ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
          <pre className="overflow-x-auto rounded-lg border border-border bg-surface-2 p-4 pr-12 text-xs leading-relaxed">
            <code>{ex.code}</code>
          </pre>
        </TabsContent>
      ))}
    </Tabs>
  )
}
