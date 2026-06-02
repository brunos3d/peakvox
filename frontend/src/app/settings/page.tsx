"use client"

import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"

export default function SettingsPage() {
  return (
    <PageLayout>
      <PageHeader title="Settings" description="Configure device and output preferences." />
      <p className="mt-8 text-sm text-muted-foreground">Coming up next.</p>
    </PageLayout>
  )
}
