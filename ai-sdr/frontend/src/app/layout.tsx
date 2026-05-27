import type { Metadata } from "next"
import "@/styles/globals.css"

export const metadata: Metadata = {
  title: "OutreachAI - AI-Powered Sales Development Platform | Automate Outreach & Close More Deals",
  description: "OutreachAI is the #1 AI SDR platform that automates lead generation, email outreach, LinkedIn engagement, and phone calls. Book 10x more meetings with AI-powered sales development.",
  keywords: "AI SDR, sales development, outreach automation, AI lead generation, automated email outreach, LinkedIn automation, AI sales agent, sales outreach tool, cold email automation, AI prospecting, lead generation software, sales automation platform",
  robots: "index, follow, max-snippet:-1, max-image-preview:large",
  icons: { icon: "/favicon.ico", apple: "/apple-touch-icon.png" },
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "OutreachAI",
    title: "OutreachAI - AI-Powered Sales Development Platform",
    description: "Automate your entire sales outreach with AI. Multi-channel campaigns, smart lead scoring, and autonomous follow-ups that book meetings on autopilot.",
    url: "https://offdx.in",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "OutreachAI - AI Sales Development Platform" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "OutreachAI - AI SDR Platform",
    description: "Book 10x more meetings with AI-powered sales development. Automate email, LinkedIn, and calls.",
    images: ["/og-image.png"],
  },
  alternates: { canonical: "https://offdx.in" },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "OutreachAI",
              applicationCategory: "SalesApplication",
              operatingSystem: "Web",
              description: "AI-powered sales development platform that automates multi-channel outreach, lead generation, and meeting booking.",
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              author: { "@type": "Organization", name: "OutreachAI", url: "https://offdx.in" },
            }),
          }}
        />
      </head>
      <body className="antialiased min-h-screen bg-[hsl(224,45%,4%)]" style={{ fontFamily: "'Inter', system-ui, -apple-system, sans-serif" }}>
        {children}
      </body>
    </html>
  )
}
