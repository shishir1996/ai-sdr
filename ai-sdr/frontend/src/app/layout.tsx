import type { Metadata } from "next"
import "@/styles/globals.css"

export const metadata: Metadata = {
  title: "AI SDR - Sales Development Platform",
  description: "AI-powered sales development platform",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">{children}</body>
    </html>
  )
}
