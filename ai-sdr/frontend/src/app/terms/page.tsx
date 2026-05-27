"use client"

/*
  SEO: OutreachAI Terms of Service
  Title: Terms of Service | OutreachAI
  Description: OutreachAI terms of service - account terms, payment terms, AI usage guidelines, data handling, and liability limitations for our AI SDR platform.
*/

import { motion } from "framer-motion"
import { Building2, ArrowRight, Shield } from "lucide-react"
import Link from "next/link"

const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

const sections = [
  {
    title: "1. Acceptance of Terms",
    content: "By accessing or using OutreachAI (\"the Platform\"), you agree to be bound by these Terms of Service. If you do not agree, do not use the Platform. We may update these terms at any time, and continued use constitutes acceptance of changes."
  },
  {
    title: "2. Account Registration",
    content: "You must provide accurate, complete information when creating an account. You are responsible for maintaining confidentiality of your credentials and for all activity under your account. Notify us immediately of unauthorized use. You must be at least 18 years old to use the Platform."
  },
  {
    title: "3. Subscription & Payment",
    content: "Paid plans are billed monthly or annually as selected. All fees are non-refundable except as stated in our Refund Policy. We may change pricing with 30 days notice. Late payments may result in service suspension. Enterprise plans are subject to a separate agreement."
  },
  {
    title: "4. AI Usage & Limitations",
    content: "OutreachAI uses artificial intelligence to generate outreach content, analyze prospect data, and automate communications. The AI may occasionally produce inaccurate or inappropriate content. You are responsible for reviewing and approving AI-generated content before sending. The Platform is a tool to augment — not replace — human judgment. We make no guarantees about specific outcomes or conversion rates."
  },
  {
    title: "5. Acceptable Use",
    content: "You agree not to: (a) use the Platform for spam, illegal activities, or harassment; (b) reverse engineer or attempt to extract source code; (c) upload malicious code or attempt to breach security; (d) use the Platform to compete with us; (e) exceed rate limits or API usage thresholds; (f) impersonate others or misrepresent affiliation. Violation may result in immediate termination."
  },
  {
    title: "6. Data & Privacy",
    content: "We collect and process data as described in our Privacy Policy. You retain ownership of your data. We use data to provide and improve the Platform. We do not train our models using your data without consent. We implement industry-standard security measures to protect your data."
  },
  {
    title: "7. Intellectual Property",
    content: "The Platform, including its UI, algorithms, AI models, branding, and documentation, is the property of OutreachAI and is protected by intellectual property laws. We grant you a limited, non-exclusive, non-transferable license to use the Platform during your subscription. You may not copy, modify, or create derivative works without permission."
  },
  {
    title: "8. Third-Party Integrations",
    content: "The Platform integrates with third-party services (CRM, email, LinkedIn, etc.). We are not responsible for the availability, security, or performance of these services. Your use of third-party services is governed by their respective terms. We may share necessary data with these services to enable functionality."
  },
  {
    title: "9. Service Level & Downtime",
    content: "We strive for 99.9% uptime for paid plans, excluding scheduled maintenance. We are not liable for downtime caused by third-party services, force majeure, or factors beyond our control. Enterprise plans include SLA guarantees as specified in your agreement."
  },
  {
    title: "10. Limitation of Liability",
    content: "To the maximum extent permitted by law, OutreachAI shall not be liable for indirect, incidental, special, consequential, or punitive damages, including lost profits, data loss, or business interruption. Our total liability for any claim shall not exceed the amount you paid us in the 12 months preceding the claim."
  },
  {
    title: "11. Termination",
    content: "Either party may terminate at any time with notice. Upon termination, your access will be revoked and data deleted within 30 days unless required by law. We may terminate immediately for breach of terms. Sections 6-12 survive termination."
  },
  {
    title: "12. Governing Law",
    content: "These terms are governed by the laws of India. Any disputes shall be resolved through binding arbitration in Mumbai, India. The Platform complies with Indian IT laws including the IT Act, 2000 and IT Rules, 2011."
  },
]

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-[hsl(224,45%,4%)]">
      <nav className="glass-dark border-b border-white/10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
              <Building2 className="text-white" size={18} />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">
              Outreach<span className="text-gradient">AI</span>
            </span>
          </Link>
          <Link href="/" className="text-sm text-gray-400 hover:text-white transition-colors flex items-center gap-1">
            <ArrowRight size={14} className="rotate-180" />
            Back to Home
          </Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 py-20">
        <motion.div initial="hidden" animate="visible" variants={fadeIn} className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-purple-300 mb-6 border-purple-500/20">
            <Shield size={14} />
            Legal
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-4">Terms of Service</h1>
          <p className="text-gray-400">Last updated: January 1, 2025</p>
        </motion.div>

        <div className="glass-card rounded-2xl p-8 md:p-12 space-y-10">
          {sections.map((section, i) => (
            <motion.div
              key={section.title}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeIn}
              transition={{ delay: i * 0.05 }}
            >
              <h2 className="text-xl font-bold text-white mb-3">{section.title}</h2>
              <p className="text-gray-400 leading-relaxed">{section.content}</p>
            </motion.div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors">
            &larr; Back to Home
          </Link>
        </div>
      </div>

      <footer className="border-t border-white/5 py-8 text-center">
        <p className="text-sm text-gray-600">&copy; {new Date().getFullYear()} OutreachAI. All rights reserved. | <a href="https://offdx.in" className="hover:text-gray-400">offdx.in</a></p>
      </footer>
    </main>
  )
}
