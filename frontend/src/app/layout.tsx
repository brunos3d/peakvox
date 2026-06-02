import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { Providers } from "@/components/Providers"
import { AppShell } from "@/components/shell/AppShell"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "OmniVoice",
  description: "Voice Cloning and Text-to-Speech Platform powered by OmniVoice",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  )
}
