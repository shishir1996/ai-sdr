"use client"

/*
  SEO: About OutreachAI - Company story, mission, and AI-powered vision
  Title: About Us | OutreachAI - AI-Powered Sales Development Platform
  Description: Learn about OutreachAI's mission to democratize AI-powered sales development. Our story, team, values, and vision for the future of sales automation.
*/

import { motion } from "framer-motion"
import { Building2, ArrowRight, Target, Eye, Heart, Users, Sparkles, Shield, Zap, Globe } from "lucide-react"
import Link from "next/link"

const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
}

const values = [
  { icon: Zap, title: "Innovation First", desc: "We push the boundaries of what AI can do for sales teams, constantly iterating on our models and features." },
  { icon: Shield, title: "Trust & Security", desc: "Enterprise-grade security and data privacy are foundational to everything we build." },
  { icon: Target, title: "Customer Obsession", desc: "Every feature we build starts with a customer problem. Your success is our success." },
  { icon: Heart, title: "Transparency", desc: "We believe in clear pricing, honest AI capabilities, and open communication with our users." },
  { icon: Globe, title: "Global Scale", desc: "Sales is global. Our AI speaks multiple languages and understands regional business nuances." },
  { icon: Users, title: "Empowerment", desc: "We empower sales professionals to focus on what matters — building relationships and closing deals." },
]

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-[hsl(224,45%,4%)]">
      {/* Nav */}
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
        {/* Hero */}
        <motion.div initial="hidden" animate="visible" variants={staggerContainer} className="text-center mb-20">
          <motion.div variants={fadeIn} className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-purple-300 mb-6 border-purple-500/20">
            <Sparkles size={14} />
            Our Story
          </motion.div>
          <motion.h1 variants={fadeIn} className="text-4xl md:text-5xl font-extrabold text-white mb-6">
            We&apos;re on a mission to <span className="text-gradient">democratize AI sales</span>
          </motion.h1>
          <motion.p variants={fadeIn} className="text-lg text-gray-400 leading-relaxed max-w-2xl mx-auto">
            OutreachAI was founded in 2024 with a simple belief: every sales team — from solo founders to enterprise 
            organizations — deserves access to world-class AI that automates the grunt work of sales development.
          </motion.p>
        </motion.div>

        {/* Story */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={staggerContainer}
          className="glass-card rounded-2xl p-8 md:p-12 mb-12"
        >
          <motion.h2 variants={fadeIn} className="text-2xl font-bold text-white mb-6">Our Story</motion.h2>
          <motion.div variants={fadeIn} className="space-y-4 text-gray-400 leading-relaxed">
            <p>
              Sales development has traditionally been a numbers game — hundreds of cold emails, LinkedIn messages, and 
              phone calls hoping for a handful of replies. The most talented SDRs spend 70% of their time on repetitive 
              tasks instead of building relationships.
            </p>
            <p>
              We founded OutreachAI to change that. By combining cutting-edge large language models, voice AI, and 
              intelligent automation, we built a platform that handles the entire first-touch outreach process — from 
              finding the right prospects to booking qualified meetings.
            </p>
            <p>
              Today, OutreachAI powers sales development for over 500 companies across 30+ countries, processing 
              millions of outreach touchpoints every month. Our AI has influenced over 50,000 deals worth hundreds of 
              millions in pipeline value.
            </p>
          </motion.div>
        </motion.div>

        {/* Mission & Vision */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeIn}
            className="glass-card rounded-2xl p-8"
          >
            <Target className="text-purple-400 mb-4" size={32} />
            <h2 className="text-xl font-bold text-white mb-3">Our Mission</h2>
            <p className="text-gray-400 leading-relaxed">
              To empower every sales professional with an AI co-pilot that handles the tedious work of prospecting, 
              outreach, and follow-up — freeing them to focus on what humans do best: build genuine connections.
            </p>
          </motion.div>
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeIn}
            className="glass-card rounded-2xl p-8"
          >
            <Eye className="text-cyan-400 mb-4" size={32} />
            <h2 className="text-xl font-bold text-white mb-3">Our Vision</h2>
            <p className="text-gray-400 leading-relaxed">
              A world where AI handles 90% of sales development outreach, sales teams close 10x more deals, and 
              the buyer experience is actually personalized, helpful, and human — at scale.
            </p>
          </motion.div>
        </div>

        {/* Values */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={staggerContainer}
          className="mb-12"
        >
          <motion.h2 variants={fadeIn} className="text-2xl font-bold text-white text-center mb-12">
            What We <span className="text-gradient">Believe In</span>
          </motion.h2>
          <div className="grid md:grid-cols-3 gap-6">
            {values.map((v) => {
              const Icon = v.icon
              return (
                <motion.div key={v.title} variants={fadeIn} className="glass-card rounded-2xl p-6">
                  <Icon className="text-purple-400 mb-4" size={24} />
                  <h3 className="text-lg font-semibold text-white mb-2">{v.title}</h3>
                  <p className="text-sm text-gray-400 leading-relaxed">{v.desc}</p>
                </motion.div>
              )
            })}
          </div>
        </motion.div>

        {/* CTA */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="text-center glass-card rounded-2xl p-12 glow"
        >
          <h2 className="text-3xl font-bold text-white mb-4">Ready to transform your sales development?</h2>
          <p className="text-gray-400 mb-8">Join 500+ teams using OutreachAI to book more meetings.</p>
          <Link href="/signup" className="btn-primary inline-flex items-center gap-2 px-8 py-4 text-base">
            Start Free Trial <ArrowRight size={18} />
          </Link>
        </motion.div>

        <div className="mt-12 text-center">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors">
            &larr; Back to Home
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 text-center">
        <p className="text-sm text-gray-600">&copy; {new Date().getFullYear()} OutreachAI. All rights reserved. | <a href="https://offdx.in" className="hover:text-gray-400">offdx.in</a></p>
      </footer>
    </main>
  )
}
