"use client"

import { PageLayout } from "@/components/shell/PageLayout"
import { PageHeader } from "@/components/shell/PageHeader"
import { SettingsPanel } from "@/components/settings/SettingsPanel"

export default function SettingsPage() {
  return (
    <PageLayout>
      <div className="mx-auto max-w-2xl">
        <PageHeader title="Settings" description="Configure device and output preferences." />
        <div className="mt-6">
          <SettingsPanel />
        </div>
      </div>
    </PageLayout>
  )
}
