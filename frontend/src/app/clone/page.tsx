"use client"

import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { VoiceWizard } from "@/components/wizard/VoiceWizard"

export default function VoiceClonePage() {
  return (
    <PageLayout>
      <PageHeader title="Voice Clone" description="Create a new voice from a short audio sample." />
      <div className="mt-8">
        <VoiceWizard />
      </div>
    </PageLayout>
  )
}
