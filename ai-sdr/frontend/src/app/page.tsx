"use client"

import { useState, useEffect, useRef } from "react"
import { motion, useInView, AnimatePresence } from "framer-motion"
import {
  Brain, Zap, Mail, Linkedin, Phone, BarChart3, LayoutDashboard,
  ChevronDown, Menu, X, ArrowRight, Check, Star, Shield, Users,
  ExternalLink, Sparkles, TrendingUp, Target, Building2, Globe,
  ChevronRight, ChevronLeft, Quote, Play, Clock, MessageSquare,
  Bot, Network, Workflow, Layers, Database, Signal, Cpu,
} from "lucide-react"

/* ─── Variants ─── */
const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
}

const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: { opacity: 1, scale: 1 },
}

/* ─── Navigation ─── */
const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "Pricing", href: "#pricing" },
  { label: "About", href: "/about" },
]

/* ─── Features Data ─── */
const FEATURES = [
  {
    icon: Brain,
    title: "AI Lead Generation",
    description: "Our AI scans millions of data points to find your ideal prospects — filtering by industry, role, company size, and intent signals with 95% accuracy.",
    color: "from-purple-500 to-violet-600",
    glow: "glow",
  },
  {
    icon: Mail,
    title: "Smart Email Outreach",
    description: "AI crafts personalized email sequences that adapt based on reply patterns. A/B test subject lines, tone, and timing automatically.",
    color: "from-blue-500 to-cyan-500",
    glow: "glow-blue",
  },
  {
    icon: Linkedin,
    title: "LinkedIn Automation",
    description: "Auto-engage with prospects via connection requests, messages, and profile visits. Smart rate limiting to keep accounts safe.",
    color: "from-blue-600 to-blue-700",
    glow: "glow-blue",
  },
  {
    icon: Phone,
    title: "AI Phone Calls",
    description: "Natural-sounding AI voice agents handle initial outreach calls, qualify leads, and book meetings — 24/7 in multiple languages.",
    color: "from-emerald-500 to-teal-500",
    glow: "glow-sm",
  },
  {
    icon: Target,
    title: "Smart Lead Scoring",
    description: "Predictive scoring models rank leads by engagement, fit, and purchase intent — so your team focuses on the hottest prospects.",
    color: "from-amber-500 to-orange-500",
    glow: "glow-sm",
  },
  {
    icon: LayoutDashboard,
    title: "Unified Dashboard",
    description: "Real-time analytics across all channels. See pipeline value, meeting booking rates, response rates, and ROI in one place.",
    color: "from-purple-500 to-pink-500",
    glow: "glow",
  },
]

/* ─── How It Works ─── */
const STEPS = [
  {
    icon: Database,
    title: "Connect Your Data",
    description: "Connect your CRM, LinkedIn, email, and data sources in one click. Our AI ingests your existing workflows and prospect lists.",
    step: "01",
  },
  {
    icon: Cpu,
    title: "AI Learns Your Style",
    description: "The AI analyzes your best-performing emails, calls, and campaigns to replicate your unique sales voice across every channel.",
    step: "02",
  },
  {
    icon: Workflow,
    title: "Launch Multi-Channel Campaigns",
    description: "Set up omnichannel sequences — email, LinkedIn, calls — with smart fallbacks. The AI handles follow-ups and personalization.",
    step: "03",
  },
  {
    icon: Calendar,
    title: "AI Books Meetings",
    description: "Qualified leads are automatically routed to your calendar. The AI handles scheduling, reminders, and rescheduling seamlessly.",
    step: "04",
  },
]

/* ─── Pricing Data ─── */
const PRICING_TIERS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Perfect for solo founders exploring AI SDR capabilities.",
    features: [
      "50 AI-generated leads/month",
      "100 email outreach credits",
      "LinkedIn automation (limited)",
      "Basic analytics dashboard",
      "Email support",
    ],
    cta: "Get Started Free",
    href: "/signup",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$49",
    period: "/month",
    description: "For growing sales teams that want to scale outreach.",
    features: [
      "5,000 AI-generated leads/month",
      "Unlimited email campaigns",
      "Full LinkedIn automation",
      "AI phone call credits (100 min)",
      "Smart lead scoring & intent data",
      "Custom AI voice cloning",
      "Priority support & onboarding",
    ],
    cta: "Start Free Trial",
    href: "/signup",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For organizations needing custom workflows and dedicated support.",
    features: [
      "Unlimited leads & outreach",
      "Custom AI model training",
      "Dedicated account manager",
      "SSO & advanced security",
      "Custom integrations",
      "SLA guarantees",
      "On-premise deployment option",
    ],
    cta: "Contact Sales",
    href: "#contact",
    highlighted: false,
  },
]

/* ─── FAQ Data ─── */
const FAQ_ITEMS = [
  {
    q: "What is OutreachAI?",
    a: "OutreachAI is an AI-powered Sales Development platform that automates multi-channel outreach — email, LinkedIn, and phone calls. Our intelligent agents find prospects, personalize messaging, handle follow-ups, and book meetings automatically, so your sales team can focus on closing deals.",
  },
  {
    q: "How does the AI SDR work?",
    a: "Our AI SDR learns from your existing sales data and communication patterns. It scans your CRM, email history, and call recordings to understand your brand voice. It then executes personalized multi-channel campaigns — sending emails, LinkedIn messages, and making calls — with smart follow-ups based on prospect behavior. The system continuously improves using response data and A/B testing.",
  },
  {
    q: "Which channels are supported?",
    a: "OutreachAI supports Email (via SMTP/API integrations with Gmail, Outlook, SendGrid, SES), LinkedIn (connection requests, InMail, profile visits), Phone calls (AI voice agents with natural speech synthesis), and SMS (coming soon). All channels work together in coordinated sequences with smart fallbacks.",
  },
  {
    q: "Is my data secure?",
    a: "Absolutely. OutreachAI is built with enterprise-grade security. All data is encrypted at rest (AES-256) and in transit (TLS 1.3). We are SOC 2 compliant, GDPR compliant, and CCPA compliant. Your data is never used to train models for other customers. We offer SSO, RBAC, and audit logging for enterprise plans.",
  },
  {
    q: "Can I try it for free?",
    a: "Yes! Our Free plan is available forever with no credit card required. You get 50 AI-generated leads and 100 email credits to test the platform. Our Pro plan comes with a 14-day free trial with full access to all features — cancel anytime, no questions asked.",
  },
  {
    q: "What integrations are supported?",
    a: "OutreachAI integrates with Salesforce, HubSpot, Pipedrive, Zoho CRM, Close, and Copper for CRM sync. For email, we support Gmail, Outlook, SendGrid, Amazon SES, and Mailgun. We also integrate with LinkedIn Sales Navigator, ZoomInfo, Apollo, and Clearbit for data enrichment. Custom integrations via our API are available on Enterprise plans.",
  },
]

/* ─── Floating Particle Component ─── */
function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 20 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 rounded-full bg-purple-400/30"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          animate={{
            y: [0, -30, 0],
            opacity: [0.2, 0.6, 0.2],
            scale: [1, 1.5, 1],
          }}
          transition={{
            duration: 3 + Math.random() * 4,
            repeat: Infinity,
            delay: Math.random() * 3,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  )
}

/* ─── Section Header ─── */
function SectionHeader({ badge, title, subtitle }: { badge?: string; title: string; subtitle?: string }) {
  return (
    <motion.div
      variants={fadeIn}
      className="text-center max-w-3xl mx-auto mb-16"
    >
      {badge && (
        <motion.div variants={fadeIn} className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-purple-300 mb-6 border-purple-500/20">
          <Sparkles size={14} />
          {badge}
        </motion.div>
      )}
      <motion.h2 variants={fadeIn} className="text-4xl md:text-5xl font-bold mb-4">
        <span className="text-gradient">{title}</span>
      </motion.h2>
      {subtitle && (
        <motion.p variants={fadeIn} className="text-lg text-gray-400 leading-relaxed">
          {subtitle}
        </motion.p>
      )}
    </motion.div>
  )
}

/* ─── Feature Card ─── */
function FeatureCard({ feature, index }: { feature: typeof FEATURES[0]; index: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-50px" })
  const Icon = feature.icon

  return (
    <motion.div
      ref={ref}
      variants={fadeIn}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{ delay: index * 0.1 }}
      className={`group relative glass-card rounded-2xl p-8 ${feature.glow} card-3d hover:scale-[1.02] transition-all duration-500`}
    >
      <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 shadow-lg`}>
        <Icon className="text-white" size={26} />
      </div>
      <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
      <p className="text-gray-400 leading-relaxed">{feature.description}</p>
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
    </motion.div>
  )
}

/* ─── Step Card ─── */
function StepCard({ step, index }: { step: typeof STEPS[0]; index: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-50px" })
  const Icon = step.icon
  const isLast = index === STEPS.length - 1

  return (
    <motion.div
      ref={ref}
      variants={fadeIn}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{ delay: index * 0.15 }}
      className="relative flex flex-col items-center text-center"
    >
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-500/20 to-violet-600/20 border border-purple-500/20 flex items-center justify-center backdrop-blur-xl">
          <Icon className="text-purple-400" size={36} />
        </div>
        <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-xs font-bold text-white shadow-lg shadow-purple-500/30">
          {step.step}
        </div>
      </div>
      <h3 className="text-xl font-semibold text-white mb-3">{step.title}</h3>
      <p className="text-gray-400 leading-relaxed max-w-xs">{step.description}</p>
    </motion.div>
  )
}

/* ─── Pricing Card ─── */
function PricingCard({ tier, index }: { tier: typeof PRICING_TIERS[0]; index: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-50px" })

  return (
    <motion.div
      ref={ref}
      variants={fadeIn}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{ delay: index * 0.15 }}
      className={`relative glass-card rounded-2xl p-8 flex flex-col ${tier.highlighted ? 'border-purple-500/40 glow scale-[1.05] md:scale-110 z-10' : ''}`}
    >
      {tier.highlighted && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-purple-600 to-violet-600 text-xs font-semibold text-white shadow-lg">
          Most Popular
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-2xl font-bold text-white mb-1">{tier.name}</h3>
        <div className="flex items-baseline gap-1 mb-2">
          <span className="text-5xl font-extrabold text-white">{tier.price}</span>
          {tier.period && <span className="text-gray-400 text-lg">/{tier.period}</span>}
        </div>
        <p className="text-gray-400 text-sm">{tier.description}</p>
      </div>

      <div className="flex-1 mb-8">
        <ul className="space-y-3">
          {tier.features.map((f, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-gray-300">
              <Check size={18} className="text-emerald-400 shrink-0 mt-0.5" />
              {f}
            </li>
          ))}
        </ul>
      </div>

      <a
        href={tier.href}
        className={`w-full text-center py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
          tier.highlighted
            ? 'btn-primary'
            : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
        }`}
      >
        {tier.cta}
      </a>
    </motion.div>
  )
}

/* ─── FAQ Item ─── */
function FAQItem({ item, index }: { item: typeof FAQ_ITEMS[0]; index: number }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-50px" })

  return (
    <motion.div
      ref={ref}
      variants={fadeIn}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{ delay: index * 0.1 }}
      className="glass-card rounded-2xl overflow-hidden transition-all duration-300"
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-6 text-left"
      >
        <span className="text-white font-medium pr-4">{item.q}</span>
        <ChevronDown
          size={20}
          className={`text-gray-400 shrink-0 transition-transform duration-300 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-6 text-gray-400 leading-relaxed border-t border-white/5 pt-4">
              {item.a}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

/* ─── Navbar ─── */
function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener("scroll", onScroll)
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'glass-dark shadow-2xl' : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Logo */}
          <a href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30 group-hover:shadow-purple-500/50 transition-shadow">
              <Building2 className="text-white" size={20} />
            </div>
            <span className="text-xl font-bold text-white tracking-tight">
              Outreach<span className="text-gradient">AI</span>
            </span>
          </a>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Desktop Buttons */}
          <div className="hidden md:flex items-center gap-3">
            <a href="/login" className="btn-ghost">Sign In</a>
            <a href="/signup" className="btn-primary">Get Started <ArrowRight size={16} className="ml-1" /></a>
          </div>

          {/* Mobile toggle */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 text-gray-400 hover:text-white"
          >
            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden glass-dark border-t border-white/10"
          >
            <div className="px-4 py-6 space-y-4">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="block text-sm text-gray-400 hover:text-white py-2"
                >
                  {link.label}
                </a>
              ))}
              <div className="pt-4 border-t border-white/10 space-y-3">
                <a href="/login" onClick={() => setMobileOpen(false)} className="block w-full text-center py-2.5 rounded-xl bg-white/5 text-white text-sm font-medium">Sign In</a>
                <a href="/signup" onClick={() => setMobileOpen(false)} className="block w-full text-center py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-violet-600 text-white text-sm font-semibold shadow-lg shadow-purple-500/30">Get Started</a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}

/* ─── Hero Section ─── */
function HeroSection() {
  const ref = useRef(null)

  return (
    <section ref={ref} className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
      {/* Background layers */}
      <div className="absolute inset-0 bg-gradient-mesh" />
      <div className="absolute inset-0 bg-gradient-radial opacity-50" />
      <div className="absolute inset-0 bg-grid opacity-40" />
      <FloatingParticles />

      {/* Decorative orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-pulse-glow" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl animate-pulse-glow" style={{ animationDelay: "1.5s" }} />

      {/* Content */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 text-center">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="space-y-8"
        >
          {/* Badge */}
          <motion.div variants={fadeIn} className="inline-flex items-center gap-2 px-5 py-2 rounded-full glass text-sm text-purple-300 border-purple-500/20">
            <Sparkles size={14} />
            Trusted by 500+ sales teams worldwide
            <Star size={14} className="text-amber-400 ml-1" />
          </motion.div>

          {/* Headline */}
          <motion.h1
            variants={fadeIn}
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-extrabold leading-[1.05] tracking-tight"
          >
            <span className="text-white">Your AI </span>
            <span className="text-gradient-cyan">Sales Development</span>
            <br />
            <span className="text-white">Team, On</span>{" "}
            <span className="text-gradient">Autopilot</span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            variants={fadeIn}
            className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed"
          >
            OutreachAI finds prospects, personalizes outreach, and books meetings across email, LinkedIn, and phone — 
            <span className="text-white/80"> so your team closes more deals, faster.</span>
          </motion.p>

          {/* CTAs */}
          <motion.div variants={fadeIn} className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <a href="/signup" className="btn-primary text-base px-8 py-4 rounded-xl group">
              Start Your Free Trial
              <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />
            </a>
            <a href="#features" className="btn-secondary text-base px-8 py-4 rounded-xl">
              See How It Works
            </a>
          </motion.div>

          {/* Stats */}
          <motion.div variants={fadeIn} className="pt-12 flex flex-wrap items-center justify-center gap-8 sm:gap-16">
            {[
              { value: "10x", label: "More Meetings" },
              { value: "95%", label: "Lead Accuracy" },
              { value: "50K+", label: "Deals Influenced" },
              { value: "4.9/5", label: "Customer Rating" },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="stat-value text-gradient">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

/* ─── Features Section ─── */
function FeaturesSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section id="features" ref={ref} className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-20" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Features"
          title="Everything You Need to Close More Deals"
          subtitle="One platform. Every channel. Infinite possibilities for your sales pipeline."
        />

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {FEATURES.map((feature, i) => (
            <FeatureCard key={feature.title} feature={feature} index={i} />
          ))}
        </motion.div>
      </div>
    </section>
  )
}

/* ─── How It Works Section ─── */
function HowItWorksSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-mesh" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="How It Works"
          title="From Data to Meetings in 4 Steps"
          subtitle="Set up once. Let the AI run your outreach while you focus on closing."
        />

        <div className="relative">
          {/* Connecting line */}
          <div className="absolute top-20 left-[calc(50%-1px)] w-0.5 h-[calc(100%-5rem)] bg-gradient-to-b from-purple-500/50 via-purple-500/30 to-transparent hidden md:block" />

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="grid md:grid-cols-4 gap-12 relative"
          >
            {STEPS.map((step, i) => (
              <StepCard key={step.title} step={step} index={i} />
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}

/* ─── Pricing Section ─── */
function PricingSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section id="pricing" ref={ref} className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-radial opacity-30" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="Pricing"
          title="Simple, Transparent Pricing"
          subtitle="Start free. Scale when you're ready. No hidden fees, no surprises."
        />

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid md:grid-cols-3 gap-8 items-start max-w-5xl mx-auto"
        >
          {PRICING_TIERS.map((tier, i) => (
            <PricingCard key={tier.name} tier={tier} index={i} />
          ))}
        </motion.div>
      </div>
    </section>
  )
}

/* ─── FAQ Section ─── */
function FAQSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-20" />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <SectionHeader
          badge="FAQ"
          title="Frequently Asked Questions"
          subtitle="Everything you need to know about OutreachAI."
        />

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="space-y-4"
        >
          {FAQ_ITEMS.map((item, i) => (
            <FAQItem key={item.q} item={item} index={i} />
          ))}
        </motion.div>
      </div>
    </section>
  )
}

/* ─── CTA Section ─── */
function CTASection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-mesh" />
      <div className="absolute inset-0 bg-gradient-radial opacity-60" />

      <motion.div
        variants={fadeIn}
        initial="hidden"
        animate={isInView ? "visible" : "hidden"}
        className="relative z-10 max-w-4xl mx-auto px-4 text-center"
      >
        <div className="glass-card rounded-3xl p-12 md:p-16 glow relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-violet-500 to-indigo-500" />
          <FloatingParticles />

          <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-6">
            Ready to <span className="text-gradient-cyan">10x</span> Your Sales?
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Join 500+ sales teams that have transformed their outreach. Set up in minutes, see results in days.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="/signup" className="btn-primary text-base px-10 py-4 rounded-xl group">
              Start Free Trial
              <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />
            </a>
            <a href="/login" className="btn-secondary text-base px-10 py-4 rounded-xl">
              Sign In
            </a>
          </div>
          <p className="text-sm text-gray-500 mt-6">No credit card required. 14-day free trial on Pro.</p>
        </div>
      </motion.div>
    </section>
  )
}

/* ─── Calendar icon (for StepCard) ─── */
function Calendar(props: any) {
  return (
    <svg
      {...props}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

/* ─── Footer ─── */
function FooterSection() {
  const footerLinks = {
    Product: [
      { label: "Features", href: "#features" },
      { label: "Pricing", href: "#pricing" },
      { label: "About", href: "/about" },
    ],
    Legal: [
      { label: "Terms of Service", href: "/terms" },
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Refund Policy", href: "/refund" },
      { label: "Disclaimer", href: "/disclaimer" },
    ],
    Contact: [
      { label: "hello@offdx.in", href: "mailto:hello@offdx.in" },
      { label: "Support Center", href: "#" },
      { label: "API Docs", href: "#" },
      { label: "Status", href: "#" },
    ],
  }

  return (
    <footer className="relative border-t border-white/5 pt-20 pb-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10 mb-16">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <a href="/" className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Building2 className="text-white" size={20} />
              </div>
              <span className="text-lg font-bold text-white tracking-tight">
                Outreach<span className="text-gradient">AI</span>
              </span>
            </a>
            <p className="text-sm text-gray-500 leading-relaxed max-w-xs">
              AI-powered sales development platform that automates multi-channel outreach and books meetings on autopilot.
            </p>
            <div className="flex items-center gap-3 mt-6">
              <Globe size={16} className="text-gray-500" />
              <span className="text-sm text-gray-500">offdx.in</span>
            </div>
          </div>

          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title}>
              <h4 className="text-sm font-semibold text-white mb-4">{title}</h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-white/5 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-gray-600">
            &copy; {new Date().getFullYear()} OutreachAI. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            <a href="/terms" className="text-xs text-gray-600 hover:text-gray-400">Terms</a>
            <a href="/privacy" className="text-xs text-gray-600 hover:text-gray-400">Privacy</a>
            <a href="/refund" className="text-xs text-gray-600 hover:text-gray-400">Refund</a>
            <a href="/disclaimer" className="text-xs text-gray-600 hover:text-gray-400">Disclaimer</a>
          </div>
        </div>
      </div>
    </footer>
  )
}

/* ─── Main Page ─── */
export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[hsl(224,45%,4%)]">
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <PricingSection />
      <FAQSection />
      <CTASection />
      <FooterSection />
    </main>
  )
}
