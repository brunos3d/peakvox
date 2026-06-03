"use client"

import { useQuery } from "@tanstack/react-query"
import { KeyRound, Activity, Clock } from "lucide-react"
import { PageHeader } from "@/components/shell/PageHeader"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { fetchApiKeys } from "@/lib/api"

export default function ApiUsagePage() {
  const { data: keys = [] } = useQuery({ queryKey: ["api-keys"], queryFn: fetchApiKeys })
  const active = keys.filter((k) => k.status === "active").length
  const lastUsed = keys
    .map((k) => k.last_used_at)
    .filter(Boolean)
    .sort()
    .at(-1)

  const stats = [
    { label: "Active keys", value: String(active), icon: KeyRound },
    { label: "Total keys", value: String(keys.length), icon: Activity },
    { label: "Last API call", value: lastUsed ? new Date(lastUsed).toLocaleString() : "Never", icon: Clock },
  ]

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="Usage" description="API activity at a glance." />

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {stats.map((s) => {
          const Icon = s.icon
          return (
            <Card key={s.label}>
              <CardContent className="pt-6">
                <Icon className="h-5 w-5 text-muted-foreground" />
                <p className="mt-3 text-2xl font-semibold">{s.value}</p>
                <p className="text-caption">{s.label}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Detailed metering</CardTitle>
          <CardDescription>Per-request analytics and quotas</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Per-key request counts, character/usage metering, and rate-limit dashboards arrive
            with the Cloud Edition. The Community Edition tracks key activity (last used) and is
            architected so a usage-metering backend can be added without breaking changes.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
