"use client"

import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"

export default function HistoryPage() {
  return (
    <PageLayout>
      <PageHeader title="History" description="Your past generations." />
      <p className="mt-8 text-sm text-muted-foreground">Coming up next.</p>
    </PageLayout>
  )
}
