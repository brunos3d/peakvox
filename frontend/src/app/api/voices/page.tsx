"use client"

import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CodeTabs } from "@/components/api/CodeTabs"
import { listVoicesExamples, ttsExamples } from "@/lib/api-examples"

const ENDPOINTS = [
  { method: "GET", path: "/api/v1/voices", desc: "List voices (paginated via cursor)." },
  { method: "GET", path: "/api/v1/voices/{voiceId}", desc: "Get a voice by its public Voice ID." },
  { method: "POST", path: "/api/v1/voices", desc: "Create a voice (multipart; ≤10s reference audio)." },
  { method: "DELETE", path: "/api/v1/voices/{voiceId}", desc: "Delete a voice." },
  { method: "POST", path: "/api/v1/text-to-speech", desc: "Synthesize speech; returns audio or a download URL." },
]

const METHOD_TONE: Record<string, string> = {
  GET: "text-success",
  POST: "text-primary",
  DELETE: "text-error",
}

export default function VoiceApiDocsPage() {
  return (
    <PageLayout>
      <div className="mx-auto max-w-4xl">
        <PageHeader title="Voice API" description="REST endpoints for managing voices and generating speech." />

        <div className="mt-6 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Endpoints</CardTitle>
              <CardDescription>All requests require an API key. Voices are addressed by their public Voice ID.</CardDescription>
            </CardHeader>
            <CardContent className="divide-y divide-border">
              {ENDPOINTS.map((e) => (
                <div key={`${e.method} ${e.path}`} className="flex items-center gap-3 py-2 text-sm">
                  <span className={`w-16 shrink-0 font-mono text-xs font-semibold ${METHOD_TONE[e.method]}`}>{e.method}</span>
                  <code className="font-mono text-xs">{e.path}</code>
                  <span className="ml-auto hidden text-caption sm:block">{e.desc}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Authentication</CardTitle>
              <CardDescription>Send your key as a bearer token or an X-API-Key header.</CardDescription>
            </CardHeader>
            <CardContent>
              <code className="block rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm font-mono">
                Authorization: Bearer ov_live_…
              </code>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">List voices <Badge variant="secondary">GET</Badge></CardTitle>
            </CardHeader>
            <CardContent>
              <CodeTabs examples={listVoicesExamples()} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">Text to speech <Badge variant="secondary">POST</Badge></CardTitle>
              <CardDescription>Pass any voiceId from the list endpoint. Formats: wav, mp3.</CardDescription>
            </CardHeader>
            <CardContent>
              <CodeTabs examples={ttsExamples("voice_XXXXXXXXXX")} />
            </CardContent>
          </Card>
        </div>
      </div>
    </PageLayout>
  )
}
