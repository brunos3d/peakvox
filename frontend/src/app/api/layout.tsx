import { PageContainer } from "@/components/shell/PageContainer"

/**
 * Server Component layout shared by every page under `/api`. Owns the scrollable
 * content column so the individual API pages only render their own centered
 * content (and their `max-w` wrapper). Native App Router nested layout replacing
 * the per-page custom wrapper.
 */
export default function ApiLayout({ children }: { children: React.ReactNode }) {
  return <PageContainer>{children}</PageContainer>
}
