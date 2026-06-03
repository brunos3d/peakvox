import Link from "next/link"
import { KeyRound, Code2, BarChart3, ArrowRight } from "lucide-react"
import { PageHeader } from "@/components/shell/PageHeader"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { getApiBaseUrl } from "@/lib/api"

const STEPS = [
  { n: 1, title: "Create an API key", body: "Generate a key on the API Keys page. The full key is shown once — store it securely." },
  { n: 2, title: "Call the API", body: "Authenticate with Authorization: Bearer ov_live_… against the /api/v1 endpoints." },
  { n: 3, title: "Generate speech", body: "POST /api/v1/text-to-speech with a voiceId and text to synthesize audio." },
]

const LINKS = [
  { href: "/api/keys", title: "API Keys", body: "Create and revoke keys.", icon: KeyRound },
  { href: "/api/voices", title: "Voice API", body: "Endpoint reference + examples.", icon: Code2 },
  { href: "/api/usage", title: "Usage", body: "Track API consumption.", icon: BarChart3 },
]

export default function ApiOverviewPage() {
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="API" description="Build with OmniVoice over a REST API addressed by stable Voice IDs." />

      <div className="mt-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Quick start</CardTitle>
            <CardDescription>Three steps to your first request.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            {STEPS.map((s) => (
              <div key={s.n} className="space-y-1.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary">{s.n}</div>
                <p className="text-sm font-medium">{s.title}</p>
                <p className="text-caption">{s.body}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Base URL</CardTitle>
            <CardDescription>All public endpoints live under /api/v1.</CardDescription>
          </CardHeader>
          <CardContent>
            <code className="block rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm font-mono">
              {getApiBaseUrl()}/api/v1
            </code>
          </CardContent>
        </Card>

        <div className="grid gap-4 sm:grid-cols-3">
          {LINKS.map((l) => {
            const Icon = l.icon
            return (
              <Link key={l.href} href={l.href}>
                <Card className="h-full transition-colors hover:border-primary/40">
                  <CardHeader>
                    <Icon className="h-5 w-5 text-primary" />
                    <CardTitle className="flex items-center justify-between text-base">
                      {l.title} <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </CardTitle>
                    <CardDescription>{l.body}</CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            )
          })}
        </div>

        <p className="text-caption">
          Community Edition runs unauthenticated locally; API keys scope every request and are
          forward-compatible with future Cloud and Enterprise editions.
        </p>
      </div>
    </div>
  )
}
