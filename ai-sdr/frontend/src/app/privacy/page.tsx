"use client"

/*
  SEO: OutreachAI Privacy Policy
  Title: Privacy Policy | OutreachAI
  Description: OutreachAI privacy policy - data collected, cookies, third-party sharing, GDPR/CCPA compliance, data retention, and security practices.
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
    title: "1. Information We Collect",
    content: "We collect information you provide: name, email, company name, billing details, and account preferences. We also collect data automatically: IP address, browser type, device info, usage patterns, pages visited, and referral URLs. When you integrate CRM or email accounts, we access contact data and communication metadata necessary for platform functionality."
  },
  {
    title: "2. How We Use Your Data",
    content: "We use your data to: (a) operate, maintain, and improve the Platform; (b) generate AI-powered outreach content; (c) analyze prospect engagement and optimize campaigns; (d) process payments and send invoices; (e) communicate product updates and support; (f) detect and prevent abuse or fraudulent activity; (g) comply with legal obligations. We do not sell your personal information."
  },
  {
    title: "3. Cookies & Tracking",
    content: "We use essential cookies for authentication and security. Analytics cookies (Google Analytics, PostHog) help us understand usage patterns. You can disable cookies in browser settings, though some features may not function properly. We also use session storage for temporary data. We do not use third-party advertising cookies."
  },
  {
    title: "4. Data Sharing & Third Parties",
    content: "We share data with: (a) service providers (cloud hosting via AWS, payment processing via Stripe, email delivery via SendGrid); (b) integrated third-party services you authorize (CRM, email, LinkedIn); (c) legal authorities when required by law. All service providers are contractually bound to protect your data and use it only for specified purposes."
  },
  {
    title: "5. Data Security",
    content: "We implement comprehensive security measures: AES-256 encryption at rest, TLS 1.3 encryption in transit, SOC 2 compliant infrastructure, regular security audits, access controls, and employee security training. However, no method of transmission is 100% secure. We cannot guarantee absolute security but follow industry best practices."
  },
  {
    title: "6. Data Retention",
    content: "We retain your data for as long as your account is active. After account deletion, we delete your data within 30 days unless retention is required by law. Anonymized analytics data may be retained indefinitely. Backup data is retained for 90 days. You can request data export at any time."
  },
  {
    title: "7. GDPR Compliance",
    content: "For EU/EEA users: (a) legal basis for processing is consent, contract performance, or legitimate interests; (b) you have rights to access, rectify, erase, restrict, port, and object to processing; (c) you may withdraw consent at any time; (d) data may be transferred to countries with adequate safeguards; (e) our Data Protection Officer can be reached at dpo@offdx.in. Complaints may be filed with your local supervisory authority."
  },
  {
    title: "8. CCPA Compliance",
    content: "California residents have the right to: (a) know what personal information is collected and shared; (b) request deletion of personal information; (c) opt out of sale of personal information (we do not sell data); (d) non-discrimination for exercising these rights. To exercise your rights, email privacy@offdx.in with 'CCPA Request' in the subject line."
  },
  {
    title: "9. Children's Privacy",
    content: "The Platform is not intended for users under 18 years of age. We do not knowingly collect data from children. If we discover a child under 18 has provided personal information, we will delete it immediately. Parents or guardians can contact us at privacy@offdx.in to request deletion."
  },
  {
    title: "10. International Data Transfers",
    content: "Your data may be processed on servers located in India, the United States, or other countries where our service providers operate. We ensure appropriate safeguards through Standard Contractual Clauses (SCCs) and Data Processing Agreements (DPAs) with all data processors."
  },
  {
    title: "11. Changes to This Policy",
    content: "We may update this Privacy Policy periodically. Material changes will be notified via email or platform notice. Your continued use after changes constitutes acceptance. We encourage you to review this policy regularly. Previous versions are available upon request."
  },
  {
    title: "12. Contact Us",
    content: "For privacy-related inquiries: Email: privacy@offdx.in. Address: OutreachAI, Mumbai, India. For data subject requests, we will respond within 30 days. You may also lodge a complaint with your local data protection authority."
  },
]

export default function PrivacyPage() {
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
            Privacy
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-4">Privacy Policy</h1>
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
