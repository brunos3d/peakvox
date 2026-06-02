"use client"

import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"

export default function VoiceClonePage() {
  return (
    <PageLayout>
      <PageHeader title="Voice Clone" description="Create a new voice from an audio sample." />
      <p className="mt-8 text-sm text-muted-foreground">Coming up next.</p>
    </PageLayout>
  )
}
