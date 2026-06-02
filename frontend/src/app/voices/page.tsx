"use client"

import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"

export default function VoiceLibraryPage() {
  return (
    <PageLayout>
      <PageHeader title="Voice Library" description="Browse, preview and manage your voices." />
      <p className="mt-8 text-sm text-muted-foreground">Coming up next.</p>
    </PageLayout>
  )
}
