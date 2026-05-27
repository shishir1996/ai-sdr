"use client"

/*
  SEO: OutreachAI Disclaimer
  Title: Disclaimer | OutreachAI
  Description: OutreachAI general disclaimer - AI accuracy limitations, no guarantees, third-party links, and limitation of liability for our AI SDR platform.
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
    title: "AI Accuracy Disclaimer",
    content: "OutreachAI uses artificial intelligence and machine learning models to generate outreach content, analyze prospect data, and automate communications. While we strive for accuracy, AI-generated content may occasionally contain errors, inaccuracies, or inappropriate suggestions. You are solely responsible for reviewing, editing, and approving all AI-generated content before it is sent. We make no warranties or representations about the completeness, accuracy, reliability, or suitability of AI-generated outputs."
  },
  {
    title: "No Guarantee of Results",
    content: "OutreachAI provides tools to enhance sales development efforts, but we do not guarantee specific results, including but not limited to: number of meetings booked, reply rates, conversion rates, pipeline value, closed deals, or revenue generated. Sales outcomes depend on numerous factors beyond our control including market conditions, product quality, pricing, timing, and sales team execution. Use the Platform as a tool to augment — not replace — strategic sales efforts."
  },
  {
    title: "Third-Party Links & Services",
    content: "The Platform may integrate with or contain links to third-party services (CRM platforms, email providers, LinkedIn, data enrichment tools, etc.). We do not endorse, control, or assume responsibility for the content, privacy practices, or terms of these third-party services. Your use of integrated services is governed by their respective terms and policies. We recommend reviewing third-party terms before connecting accounts."
  },
  {
    title: "Compliance Responsibility",
    content: "You are responsible for ensuring that your use of OutreachAI complies with all applicable laws and regulations, including but not limited to: CAN-SPAM Act, GDPR, CCPA, Telephone Consumer Protection Act (TCPA), and LinkedIn's Terms of Service. We provide tools for compliance (unsubscribe links, opt-in management, rate limiting), but you are ultimately responsible for how you use them. We are not liable for any fines, penalties, or damages resulting from non-compliant use of the Platform."
  },
  {
    title: "Limitation of Liability",
    content: "To the fullest extent permitted by law, OutreachAI, its affiliates, officers, directors, employees, and agents shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to: lost profits, lost revenue, lost data, business interruption, or reputational damage arising from your use of the Platform. Our total liability for any claim shall not exceed the amount paid by you in the 12 months preceding the claim."
  },
  {
    title: "No Professional Advice",
    content: "OutreachAI does not provide legal, financial, or professional advice. The Platform's features — including compliance tools, AI-generated content, and analytics — are not substitutes for professional advice. Consult qualified professionals for legal, financial, and compliance guidance specific to your business. We disclaim any liability for decisions made based on Platform outputs."
  },
  {
    title: "Service Availability",
    content: "We strive for high availability but do not guarantee uninterrupted or error-free service. The Platform may be temporarily unavailable for maintenance, upgrades, or due to factors beyond our control (internet outages, DDoS attacks, cloud provider failures, force majeure). We recommend maintaining backups of your data and having contingency plans for critical sales operations."
  },
  {
    title: "Changes to This Disclaimer",
    content: "We reserve the right to update this Disclaimer at any time. Changes will be posted on this page with an updated 'Last updated' date. Material changes may be notified via email. Your continued use of the Platform after changes constitutes acceptance. We encourage you to review this page periodically."
  },
  {
    title: "Contact",
    content: "For questions about this Disclaimer: Email: legal@offdx.in. Address: OutreachAI, Mumbai, India. We will respond to inquiries within 5-10 business days."
  },
]

export default function DisclaimerPage() {
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
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-4">Disclaimer</h1>
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
