import { PageContainer } from "@/components/shell/PageContainer"
import { PageHeader } from "@/components/shell/PageHeader"
import { VoiceWizard } from "@/components/wizard/VoiceWizard"

export default function VoiceClonePage() {
  return (
    <PageContainer>
      <PageHeader title="Voice Clone" description="Create a new voice from a short audio sample." />
      <div className="mt-8">
        <VoiceWizard />
      </div>
    </PageContainer>
  )
}
