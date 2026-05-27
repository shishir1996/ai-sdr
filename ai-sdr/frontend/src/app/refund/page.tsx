"use client"

/*
  SEO: OutreachAI Refund Policy
  Title: Refund Policy | OutreachAI
  Description: OutreachAI refund policy - 14-day money-back guarantee, pro-rata refunds, cancellation terms for our AI SDR platform subscriptions.
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
    title: "14-Day Money-Back Guarantee",
    content: "We stand behind OutreachAI with a 14-day money-back guarantee. If you are not satisfied for any reason within the first 14 days of your paid subscription, email refund@offdx.in and we will issue a full refund — no questions asked. Free plans are not eligible for refunds as they incur no charges."
  },
  {
    title: "Pro-Rata Refunds",
    content: "After the initial 14-day period, refunds are handled on a pro-rata basis for unused service time. If you cancel mid-cycle, you will receive a proportional refund for the remaining days in your billing period. Annual subscriptions receive a pro-rata refund based on months remaining, minus any discounts applied at purchase."
  },
  {
    title: "Cancellation Process",
    content: "To cancel your subscription: (1) Log into your dashboard and navigate to Settings > Billing > Cancel Subscription; (2) Follow the cancellation flow; (3) You will receive a confirmation email. Alternatively, email cancel@offdx.in from your registered email. Cancellations take effect at the end of your current billing period except where the 14-day guarantee applies."
  },
  {
    title: "Enterprise Plans",
    content: "Enterprise and custom plans are subject to refund terms as specified in your individual Master Services Agreement. Typically, enterprise agreements include a 30-day evaluation period. Please refer to your signed agreement for specific terms. Contact your account manager for questions about enterprise billing."
  },
  {
    title: "Add-On & Credit Refunds",
    content: "AI phone call credits, additional user seats, and add-on features are non-refundable except during the 14-day guarantee period. Unused credits expire at the end of each billing cycle and do not roll over unless specified in your plan. Pre-paid credit packs are non-refundable once activated."
  },
  {
    title: "Chargebacks & Disputes",
    content: "If you believe a charge is incorrect, please contact our support team at billing@offdx.in before filing a chargeback. We are happy to resolve billing issues directly. Unauthorized chargebacks may result in account suspension and additional recovery fees. We reserve the right to dispute chargebacks with evidence of service provided."
  },
  {
    title: "How to Request a Refund",
    content: "Email refund@offdx.in from your registered account email with: (1) Account email and name; (2) Reason for refund request; (3) Date of payment. We process refunds within 5-10 business days. Refunds are issued to the original payment method. International refunds may take longer depending on your bank."
  },
  {
    title: "Contact Billing Support",
    content: "For any billing or refund questions: Email: billing@offdx.in. Response time: within 24 hours on business days. We are committed to fair and transparent billing practices and will work with you to resolve any concerns."
  },
]

export default function RefundPage() {
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
            Refunds
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-4">Refund Policy</h1>
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
