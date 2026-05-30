"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import {
  motion, useInView, AnimatePresence, useScroll, useTransform,
} from "framer-motion"
import {
  Brain, Zap, Mail, Linkedin, Phone, BarChart3, LayoutDashboard,
  ChevronDown, Menu, X, ArrowRight, Check, Star, Shield, Users,
  ExternalLink, Sparkles, TrendingUp, Target, Building2, Globe,
  ChevronRight, ChevronLeft, Quote, Play, Clock, MessageSquare,
  Bot, Network, Workflow, Layers, Database, Signal, Cpu, Eye,
} from "lucide-react"
/* ─── Performance: detect touch device ─── */
function isTouchDevice() {
  if (typeof window === "undefined") return false
  return "ontouchstart" in window || navigator.maxTouchPoints > 0
}

/* ─── Smooth mouse position hook (throttled via rAF) ─── */
function useMousePosition() {
  const [pos, setPos] = useState({ x: 0.5, y: 0.5 })
  const raf = useRef<number>(0)

  useEffect(() => {
    if (isTouchDevice()) return
    const onMove = (e: MouseEvent) => {
      if (raf.current) cancelAnimationFrame(raf.current)
      raf.current = requestAnimationFrame(() => {
        setPos({ x: e.clientX / window.innerWidth, y: e.clientY / window.innerHeight })
      })
    }
    window.addEventListener("mousemove", onMove, { passive: true })
    return () => {
      window.removeEventListener("mousemove", onMove)
      if (raf.current) cancelAnimationFrame(raf.current)
    }
  }, [])

  return pos
}

/* ─── 3D Tilt Card wrapper ─── */
function Tilt3D({ children, className = "", intensity = 10 }: { children: React.ReactNode; className?: string; intensity?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const pos = useMousePosition()
  const [isHovered, setIsHovered] = useState(false)
  const touch = useRef(isTouchDevice()).current

  const rotateX = isHovered && !touch ? (pos.y - 0.5) * -intensity : 0
  const rotateY = isHovered && !touch ? (pos.x - 0.5) * intensity : 0

  return (
    <div
      ref={ref}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={className}
      style={{
        perspective: "1200px",
        transformStyle: "preserve-3d",
      }}
      data-cursor-hover
    >
      <motion.div
        animate={{ rotateX, rotateY }}
        transition={{ type: "spring", stiffness: 150, damping: 15 }}
        style={{ transformStyle: "preserve-3d", willChange: "transform" }}
      >
        {children}
      </motion.div>
    </div>
  )
}

/* ─── Floating 3D Shapes ─── */
function FloatingShapes3D() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden>
      <motion.div
        className="absolute top-[15%] left-[10%] w-16 h-16 border-2 border-purple-500/20 rounded-lg"
        style={{ transformStyle: "preserve-3d" }}
        animate={{
          rotateX: [0, 360, 0],
          rotateY: [0, 360, 0],
          z: [0, 60, 0],
        }}
        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute top-[30%] right-[15%] w-20 h-20 border-2 border-cyan-500/20 rounded-full"
        style={{ transformStyle: "preserve-3d" }}
        animate={{
          rotateX: [0, -360, 0],
          z: [0, -40, 0],
          scale: [1, 1.2, 1],
        }}
        transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-[25%] left-[20%] w-12 h-12 border-2 border-blue-500/20"
        style={{ transform: "rotate(45deg)", transformStyle: "preserve-3d" }}
        animate={{
          rotateX: [0, 360],
          rotateZ: [45, 405],
          y: [0, -30, 0],
        }}
        transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute bottom-[35%] right-[10%] w-24 h-24 border border-violet-500/10 rounded-full"
        style={{ transformStyle: "preserve-3d" }}
        animate={{
          rotateX: [0, 180, 360],
          rotateY: [0, -180, -360],
          scale: [1, 1.1, 1],
        }}
        transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute top-[60%] left-[60%] w-10 h-10 border border-emerald-500/20 rounded-lg"
        style={{ transform: "rotate(30deg)", transformStyle: "preserve-3d" }}
        animate={{
          rotateX: [0, 360],
          rotateY: [0, 180],
          y: [0, 20, 0],
        }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  )
}

/* ─── Floating Particles ─── */
function FloatingParticles({ count = 20, color = "rgba(168,85,247,0.3)" }: { count?: number; color?: string }) {
  const particles = useRef(
    Array.from({ length: count }, () => ({
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: 1 + Math.random() * 2,
      delay: Math.random() * 5,
      duration: 4 + Math.random() * 8,
      xDrift: (Math.random() - 0.5) * 30,
      yRange: 15 + Math.random() * 25,
    }))
  ).current

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            width: p.size,
            height: p.size,
            background: color,
            willChange: "transform",
          }}
          animate={{
            y: [0, -p.yRange, 0],
            x: [0, p.xDrift, 0],
            opacity: [0.2, 0.6, 0.2],
            scale: [1, 1.5 + Math.random(), 1],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            delay: p.delay,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  )
}

/* ─── Variants ─── */
const fadeIn = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
}
const fadeInLeft = {
  hidden: { opacity: 0, x: -50 },
  visible: { opacity: 1, x: 0 },
}
const fadeInRight = {
  hidden: { opacity: 0, x: 50 },
  visible: { opacity: 1, x: 0 },
}
const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
}
const scaleIn = {
  hidden: { opacity: 0, scale: 0.85 },
  visible: { opacity: 1, scale: 1 },
}
const card3DEnter = {
  hidden: { opacity: 0, rotateX: 15, y: 40 },
  visible: { opacity: 1, rotateX: 0, y: 0 },
}

/* ─── Data ─── */
const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "Pricing", href: "#pricing" },
  { label: "About", href: "/about" },
]

const FEATURES = [
  {
    icon: Brain,
    title: "AI Lead Generation",
    description: "Scans millions of data points to find ideal prospects — filtered by industry, role, company size, and intent signals with 95% accuracy.",
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
    description: "Auto-engage via connection requests, messages, and profile visits. Smart rate limiting keeps accounts safe.",
    color: "from-blue-600 to-blue-700",
    glow: "glow-blue",
  },
  {
    icon: Phone,
    title: "AI Phone Calls",
    description: "Natural-sounding AI voice agents handle initial outreach, qualify leads, and book meetings — 24/7 in multiple languages.",
    color: "from-emerald-500 to-teal-500",
    glow: "glow-sm",
  },
  {
    icon: Target,
    title: "Smart Lead Scoring",
    description: "Predictive models rank leads by engagement, fit, and purchase intent — so your team focuses on the hottest prospects.",
    color: "from-amber-500 to-orange-500",
    glow: "glow-sm",
  },
  {
    icon: LayoutDashboard,
    title: "Unified Dashboard",
    description: "Real-time analytics across all channels. Pipeline value, meeting booking rates, response rates, and ROI in one place.",
    color: "from-purple-500 to-pink-500",
    glow: "glow",
  },
]

const STEPS = [
  {
    icon: Database,
    title: "Connect Your Data",
    description: "Connect CRM, LinkedIn, email, and data sources in one click. AI ingests existing workflows and prospect lists.",
    step: "01",
  },
  {
    icon: Cpu,
    title: "AI Learns Your Style",
    description: "AI analyzes your best-performing emails, calls, and campaigns to replicate your unique sales voice across every channel.",
    step: "02",
  },
  {
    icon: Workflow,
    title: "Launch Multi-Channel Campaigns",
    description: "Omnichannel sequences — email, LinkedIn, calls — with smart fallbacks. AI handles follow-ups and personalization.",
    step: "03",
  },
  {
    icon: Calendar,
    title: "AI Books Meetings",
    description: "Qualified leads auto-routed to your calendar. AI handles scheduling, reminders, and rescheduling seamlessly.",
    step: "04",
  },
]

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

const FAQ_ITEMS = [
  {
    q: "What is OutreachAI?",
    a: "OutreachAI is an AI-powered Sales Development platform that automates multi-channel outreach — email, LinkedIn, and phone calls. Our AI agents find prospects, personalize messaging, handle follow-ups, and book meetings automatically.",
  },
  {
    q: "How does the AI SDR work?",
    a: "Our AI SDR learns from your sales data and communication patterns. It scans your CRM, email history, and call recordings to understand your brand voice. It then executes personalized multi-channel campaigns with smart follow-ups based on prospect behavior.",
  },
  {
    q: "Which channels are supported?",
    a: "OutreachAI supports Email (SMTP/API with Gmail, Outlook, SendGrid, SES), LinkedIn (connection requests, InMail, profile visits), Phone calls (AI voice agents), and SMS (coming soon). All channels work together in coordinated sequences.",
  },
  {
    q: "Is my data secure?",
    a: "Absolutely. All data encrypted at rest (AES-256) and in transit (TLS 1.3). SOC 2 compliant, GDPR compliant, and CCPA compliant. SSO, RBAC, and audit logging for enterprise plans.",
  },
  {
    q: "Can I try it for free?",
    a: "Yes! Our Free plan is available forever with no credit card required. You get 50 AI-generated leads and 100 email credits. The Pro plan comes with a 14-day free trial with full access.",
  },
  {
    q: "What integrations are supported?",
    a: "CRM: Salesforce, HubSpot, Pipedrive, Zoho, Close, Copper. Email: Gmail, Outlook, SendGrid, SES, Mailgun. Data: LinkedIn Sales Navigator, ZoomInfo, Apollo, Clearbit.",
  },
]

/* ─── Section Header ─── */
function SectionHeader({ badge, title, subtitle }: { badge?: string; title: string; subtitle?: string }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-80px" })

  return (
    <div ref={ref} className="text-center max-w-3xl mx-auto mb-16 md:mb-20">
      {badge && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-purple-300 mb-6 border-purple-500/20"
        >
          <Sparkles size={14} />
          {badge}
        </motion.div>
      )}
      <motion.h2
        initial={{ opacity: 0, y: 24 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ delay: 0.1, duration: 0.6 }}
        className="text-4xl md:text-5xl lg:text-6xl font-bold mb-4"
      >
        <span className="text-gradient">{title}</span>
      </motion.h2>
      {subtitle && (
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-lg text-gray-400 leading-relaxed max-w-2xl mx-auto"
        >
          {subtitle}
        </motion.p>
      )}
    </div>
  )
}

/* ─── Parallax Section ─── */
function ParallaxSection({ children, className = "", speed = 0.15 }: { children: React.ReactNode; className?: string; speed?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] })
  const y = useTransform(scrollYProgress, [0, 1], [0, speed * 250])

  return (
    <div ref={ref} className={`relative ${className}`}>
      <motion.div style={{ y, willChange: "transform" }}>
        {children}
      </motion.div>
    </div>
  )
}

/* ─── Navbar ─── */
function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled ? "bg-black/60 backdrop-blur-2xl shadow-2xl" : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 md:h-20">
          <a href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30 group-hover:shadow-purple-500/50 transition-shadow">
              <Building2 className="text-white" size={20} />
            </div>
            <span className="text-xl font-bold text-white tracking-tight">
              Outreach<span className="text-gradient">AI</span>
            </span>
          </a>

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

          <div className="hidden md:flex items-center gap-3">
            <a href="/login" className="btn-ghost" data-cursor-hover>Sign In</a>
            <a href="/signup" className="btn-primary" data-cursor-hover>
              Get Started <ArrowRight size={16} className="ml-1" />
            </a>
          </div>

          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 text-gray-400 hover:text-white"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-black/80 backdrop-blur-2xl border-t border-white/10"
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
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] })
  const y = useTransform(scrollYProgress, [0, 1], [0, 200])
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0])
  const scale3D = useTransform(scrollYProgress, [0, 1], [1, 0.92])

  return (
    <section
      ref={ref}
      className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20"
      style={{ perspective: "1000px" }}
    >
      {/* Depth layer 1: background mesh (slowest) */}
      <motion.div
        className="absolute inset-0 bg-gradient-mesh"
        style={{ y: useTransform(scrollYProgress, [0, 1], [0, 80]), willChange: "transform" }}
      />

      {/* Depth layer 2: gradient orbs */}
      <motion.div
        className="absolute inset-0 bg-gradient-radial opacity-60"
        style={{ y: useTransform(scrollYProgress, [0, 1], [0, 140]), opacity, willChange: "transform" }}
      />

      {/* Depth layer 3: grid */}
      <motion.div
        className="absolute inset-0 bg-grid opacity-40"
        style={{ y: useTransform(scrollYProgress, [0, 1], [0, 50]), willChange: "transform" }}
      />

      <FloatingParticles count={40} />
      <FloatingShapes3D />

      {/* Glowing orbs */}
      <motion.div
        className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/15 rounded-full blur-3xl"
        animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.6, 0.3] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        style={{ y: useTransform(scrollYProgress, [0, 1], [0, -100]), willChange: "transform" }}
      />
      <motion.div
        className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-600/15 rounded-full blur-3xl"
        animate={{ scale: [1, 1.3, 1], opacity: [0.2, 0.5, 0.2] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
        style={{ y: useTransform(scrollYProgress, [0, 1], [0, 80]), willChange: "transform" }}
      />

      {/* Main content */}
      <motion.div
        className="relative z-10 max-w-5xl mx-auto px-4 text-center"
        style={{ scale: scale3D, willChange: "transform" }}
      >
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="space-y-8"
        >
          <motion.div
            variants={fadeIn}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-full glass text-sm text-purple-300 border-purple-500/20"
            data-cursor-hover
          >
            <Sparkles size={14} />
            Trusted by 500+ sales teams worldwide
            <Star size={14} className="text-amber-400 ml-1" />
          </motion.div>

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

          <motion.p
            variants={fadeIn}
            className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed"
          >
            OutreachAI finds prospects, personalizes outreach, and books meetings across email, LinkedIn, and phone —
            <span className="text-white/80"> so your team closes more deals, faster.</span>
          </motion.p>

          <motion.div variants={fadeIn} className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <a href="/signup" className="btn-primary text-base px-8 py-4 rounded-xl group" data-cursor-hover>
              Start Your Free Trial
              <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />
            </a>
            <a href="#features" className="btn-secondary text-base px-8 py-4 rounded-xl" data-cursor-hover>
              See How It Works
            </a>
          </motion.div>

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
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        <ChevronDown size={24} className="text-gray-500" />
      </motion.div>
    </section>
  )
}

/* ─── Feature Card with 3D Tilt ─── */
function FeatureCard({ feature, index }: { feature: typeof FEATURES[0]; index: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  const Icon = feature.icon
  const dir = index % 2 === 0 ? fadeInLeft : fadeInRight

  return (
    <motion.div
      ref={ref}
      variants={card3DEnter}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{ delay: index * 0.08, duration: 0.6 }}
    >
      <Tilt3D intensity={8}>
        <div className={`group relative glass-card rounded-2xl p-8 ${feature.glow} transition-all duration-500 hover:border-purple-500/30`}>
          <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 shadow-lg`}>
            <Icon className="text-white" size={26} />
          </div>
          <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
          <p className="text-gray-400 leading-relaxed">{feature.description}</p>
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-white/[0.03] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        </div>
      </Tilt3D>
    </motion.div>
  )
}

/* ─── Step Card ─── */
function StepCard({ step, index }: { step: typeof STEPS[0]; index: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  const Icon = step.icon

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40, rotateX: 10 }}
      animate={isInView ? { opacity: 1, y: 0, rotateX: 0 } : {}}
      transition={{ delay: index * 0.15, duration: 0.6 }}
      className="relative flex flex-col items-center text-center"
      style={{ perspective: "800px" }}
    >
      <Tilt3D intensity={6}>
        <div className="relative mb-6">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-500/20 to-violet-600/20 border border-purple-500/20 flex items-center justify-center backdrop-blur-xl group-hover:border-purple-500/40 transition-all duration-300">
            <Icon className="text-purple-400" size={36} />
          </div>
          <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-xs font-bold text-white shadow-lg shadow-purple-500/30">
            {step.step}
          </div>
        </div>
      </Tilt3D>
      <h3 className="text-xl font-semibold text-white mb-3">{step.title}</h3>
      <p className="text-gray-400 leading-relaxed max-w-xs">{step.description}</p>
    </motion.div>
  )
}

/* ─── Pricing Card ─── */
function PricingCard({ tier, index }: { tier: typeof PRICING_TIERS[0]; index: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <motion.div
      ref={ref}
      variants={scaleIn}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{ delay: index * 0.15, duration: 0.5 }}
    >
      <Tilt3D intensity={6}>
        <div
          className={`relative glass-card rounded-2xl p-8 flex flex-col ${
            tier.highlighted ? "border-purple-500/40 glow scale-[1.02] md:scale-110 z-10" : ""
          }`}
          data-cursor-hover
        >
          {tier.highlighted && (
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-purple-600 to-violet-600 text-xs font-semibold text-white shadow-lg whitespace-nowrap">
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
                ? "btn-primary"
                : "bg-white/5 text-white hover:bg-white/10 border border-white/10"
            }`}
            data-cursor-hover
          >
            {tier.cta}
          </a>
        </div>
      </Tilt3D>
    </motion.div>
  )
}

/* ─── FAQ Item ─── */
function FAQItem({ item, index }: { item: typeof FAQ_ITEMS[0]; index: number }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-60px" })

  return (
    <motion.div
      ref={ref}
      variants={fadeIn}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{ delay: index * 0.08 }}
      className="glass-card rounded-2xl overflow-hidden transition-all duration-300"
      data-cursor-hover
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-6 text-left"
      >
        <span className="text-white font-medium pr-4">{item.q}</span>
        <ChevronDown
          size={20}
          className={`text-gray-400 shrink-0 transition-transform duration-300 ${open ? "rotate-180" : ""}`}
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

/* ─── Features Section ─── */
function FeaturesSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <ParallaxSection speed={0.06}>
      <section id="features" ref={ref} className="relative py-32 overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-20" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/30 to-transparent" />
        <FloatingShapes3D />
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
    </ParallaxSection>
  )
}

/* ─── How It Works ─── */
function HowItWorksSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <ParallaxSection speed={-0.04}>
      <section ref={ref} className="relative py-32 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-mesh" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
        <FloatingShapes3D />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeader
            badge="How It Works"
            title="From Data to Meetings in 4 Steps"
            subtitle="Set up once. Let the AI run your outreach while you focus on closing."
          />
          <div className="relative">
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
    </ParallaxSection>
  )
}

/* ─── Pricing Section ─── */
function PricingSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <ParallaxSection speed={0.08}>
      <section id="pricing" ref={ref} className="relative py-32 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-radial opacity-30" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent" />
        <FloatingShapes3D />
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
    </ParallaxSection>
  )
}

/* ─── FAQ Section ─── */
function FAQSection() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-20" />
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/30 to-transparent" />
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
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] })
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [0.92, 1, 0.92])
  const opacity = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [0.6, 1, 1, 0.6])

  return (
    <section ref={ref} className="relative py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-mesh" />
      <div className="absolute inset-0 bg-gradient-radial opacity-60" />
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/30 to-transparent" />
      <FloatingShapes3D />
      <FloatingParticles count={25} />

      <motion.div
        style={{ scale, opacity, willChange: "transform" }}
        className="relative z-10 max-w-4xl mx-auto px-4 text-center"
      >
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="glass-card rounded-3xl p-12 md:p-16 glow relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-violet-500 to-indigo-500" />

          <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-6">
            Ready to <span className="text-gradient-cyan">10x</span> Your Sales?
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Join 500+ sales teams that have transformed their outreach. Set up in minutes, see results in days.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="/signup" className="btn-primary text-base px-10 py-4 rounded-xl group" data-cursor-hover>
              Start Free Trial
              <ArrowRight size={18} className="ml-2 group-hover:translate-x-1 transition-transform" />
            </a>
            <a href="/login" className="btn-secondary text-base px-10 py-4 rounded-xl" data-cursor-hover>
              Sign In
            </a>
          </div>
          <p className="text-sm text-gray-500 mt-6">No credit card required. 14-day free trial on Pro.</p>
        </motion.div>
      </motion.div>
    </section>
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

/* ─── Calendar icon ─── */
function Calendar(props: any) {
  return (
    <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

/* ─── Main Page ─── */
export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[hsl(224,45%,4%)] overflow-x-hidden">
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
