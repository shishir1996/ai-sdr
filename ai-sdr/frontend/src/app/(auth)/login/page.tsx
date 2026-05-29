"use client"

import { useState, useEffect, useRef, useMemo } from "react"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import {
  Building2, Sparkles, Mail, Lock, User, Globe, ArrowRight, Linkedin,
  Eye, EyeOff, Check, X, ChevronRight, Shield, Zap,
} from "lucide-react"
import CustomCursor from "@/components/ui/CustomCursor"

/* ─── Performance helpers ─── */
function isTouchDevice() {
  if (typeof window === "undefined") return false
  return "ontouchstart" in window || navigator.maxTouchPoints > 0
}

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

/* ─── Floating Particles ─── */
function FloatingParticles({ count = 20 }: { count?: number }) {
  const particles = useMemo(
    () =>
      Array.from({ length: count }, () => ({
        left: Math.random() * 100,
        top: Math.random() * 100,
        size: 1 + Math.random() * 2,
        delay: Math.random() * 5,
        duration: 4 + Math.random() * 8,
        xDrift: (Math.random() - 0.5) * 30,
        yRange: 15 + Math.random() * 30,
        color: `hsla(${260 + Math.random() * 40}, 80%, 60%, ${0.15 + Math.random() * 0.25})`,
      })),
    [count]
  )

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden>
      {particles.map((p, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            width: p.size,
            height: p.size,
            background: p.color,
            willChange: "transform",
          }}
          animate={{
            y: [0, -p.yRange, 0],
            x: [0, p.xDrift, 0],
            opacity: [0.2, 0.7, 0.2],
            scale: [1, 1.5, 1],
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

/* ─── 3D Floating Shapes ─── */
function FloatingShapes3D() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden>
      <motion.div
        className="absolute top-[20%] left-[8%] w-14 h-14 border-2 border-purple-500/15 rounded-lg"
        style={{ transformStyle: "preserve-3d" }}
        animate={{ rotateX: [0, 360], rotateY: [0, 180], y: [0, -20, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute top-[15%] right-[12%] w-24 h-24 border border-cyan-500/10 rounded-full"
        style={{ transformStyle: "preserve-3d" }}
        animate={{ rotateX: [0, -360], scale: [1, 1.15, 1] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-[30%] left-[15%] w-10 h-10 border-2 border-blue-500/15"
        style={{ transform: "rotate(45deg)", transformStyle: "preserve-3d" }}
        animate={{ rotateX: [0, 360], rotateZ: [45, 405], y: [0, 15, 0] }}
        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute bottom-[20%] right-[18%] w-16 h-16 border border-violet-500/10 rounded-full"
        style={{ transformStyle: "preserve-3d" }}
        animate={{ rotateX: [0, 180], rotateY: [0, -360], scale: [1, 1.1, 1] }}
        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute top-[55%] left-[55%] w-8 h-8 border border-emerald-500/20 rounded-lg"
        style={{ transform: "rotate(30deg)", transformStyle: "preserve-3d" }}
        animate={{ rotateX: [0, 360], y: [0, -25, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  )
}

/* ─── Password Strength ─── */
function PasswordStrength({ password }: { password: string }) {
  const checks = [
    { label: "At least 8 characters", pass: password.length >= 8 },
    { label: "Contains uppercase", pass: /[A-Z]/.test(password) },
    { label: "Contains lowercase", pass: /[a-z]/.test(password) },
    { label: "Contains number", pass: /\d/.test(password) },
    { label: "Contains special char", pass: /[!@#$%^&*(),.?":{}|<>]/.test(password) },
  ]
  const passed = checks.filter((c) => c.pass).length

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: password ? 1 : 0, height: password ? "auto" : 0 }}
      className="overflow-hidden"
    >
      <div className="flex gap-1 mt-2 mb-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              i <= passed
                ? passed <= 2
                  ? "bg-red-500"
                  : passed <= 3
                    ? "bg-amber-500"
                    : "bg-emerald-500"
                : "bg-white/10"
            }`}
          />
        ))}
      </div>
      <ul className="space-y-1">
        {checks.map((check, i) => (
          <motion.li
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`flex items-center gap-2 text-xs transition-colors ${
              check.pass ? "text-emerald-400" : "text-gray-500"
            }`}
          >
            {check.pass ? <Check size={12} /> : <X size={12} />}
            {check.label}
          </motion.li>
        ))}
      </ul>
    </motion.div>
  )
}

/* ─── 3D Tilt Form Card ─── */
function TiltCard({ children }: { children: React.ReactNode }) {
  const pos = useMousePosition()
  const [isHovered, setIsHovered] = useState(false)
  const touch = useRef(isTouchDevice()).current

  const rotateX = isHovered && !touch ? (pos.y - 0.5) * -6 : 0
  const rotateY = isHovered && !touch ? (pos.x - 0.5) * 6 : 0

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ perspective: "1200px" }}
    >
      <motion.div
        animate={{ rotateX, rotateY }}
        transition={{ type: "spring", stiffness: 120, damping: 12 }}
        style={{ transformStyle: "preserve-3d", willChange: "transform" }}
      >
        {children}
      </motion.div>
    </div>
  )
}

/* ─── Login Page ─── */
export default function LoginPage() {
  const [isSignup, setIsSignup] = useState(false)
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [orgName, setOrgName] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const { login, signup } = useAuth()
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem("access_token")
    if (token) {
      router.replace("/dashboard")
    } else {
      setLoading(false)
    }
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSubmitting(true)
    try {
      if (isSignup) {
        await signup(name, email, password, orgName)
      } else {
        await login(email, password)
      }
      router.push("/dashboard")
    } catch (err: any) {
      setError(err.message || "Authentication failed")
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[hsl(224,45%,4%)] cursor-none">
        <CustomCursor color="168, 85, 247" />
        <div className="relative">
          <div className="w-14 h-14 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
          <div
            className="absolute inset-0 w-14 h-14 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"
            style={{ animationDirection: "reverse", animationDuration: "1.5s" }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex bg-[hsl(224,45%,4%)] cursor-none overflow-hidden">
      <CustomCursor color="168, 85, 247" />

      {/* ─── Left Panel (brand) ─── */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-[hsl(224,45%,6%)] via-[hsl(224,40%,8%)] to-[hsl(224,45%,4%)]">
        <div className="absolute inset-0 bg-grid opacity-30" />
        <FloatingShapes3D />
        <FloatingParticles count={30} />

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="absolute inset-0"
        >
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-pulse-glow" />
          <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-blue-600/10 rounded-full blur-3xl animate-pulse-glow" style={{ animationDelay: "2s" }} />
          <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-cyan-600/8 rounded-full blur-3xl animate-pulse-glow" style={{ animationDelay: "4s" }} />
        </motion.div>

        <div className="relative z-10 flex flex-col justify-center px-16 py-20">
          <motion.a
            href="/"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-3 mb-16 group"
          >
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30 group-hover:shadow-purple-500/50 transition-shadow">
              <Building2 className="text-white" size={24} />
            </div>
            <span className="text-2xl font-bold text-white tracking-tight">
              Outreach<span className="text-gradient">AI</span>
            </span>
          </motion.a>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6 }}
            className="space-y-6"
          >
            <h1 className="text-5xl font-extrabold leading-tight text-white">
              {isSignup ? "Start Your Free Trial" : "Welcome Back"}
            </h1>
            <p className="text-lg text-gray-400 leading-relaxed max-w-md">
              {isSignup
                ? "Join 500+ sales teams using AI to book more meetings and close more deals."
                : "Continue your AI-powered sales journey. Your prospects are waiting."}
            </p>

            <div className="flex items-center gap-4 pt-4">
              <div className="flex -space-x-2">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="w-8 h-8 rounded-full border-2 border-[hsl(224,45%,6%)] bg-gradient-to-br from-purple-500/40 to-blue-500/40"
                  />
                ))}
              </div>
              <span className="text-sm text-gray-500">
                <span className="text-white font-medium">500+</span> teams onboarded
              </span>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.6 }}
            className="mt-16 space-y-4"
          >
            {[
              { icon: Sparkles, text: "AI-powered lead generation & scoring" },
              { icon: Mail, text: "Multi-channel outreach automation" },
              { icon: BarChart3, text: "Real-time analytics & pipeline tracking" },
            ].map((item, i) => {
              const Icon = item.icon
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.7 + i * 0.1 }}
                  className="flex items-center gap-3 text-sm text-gray-400"
                >
                  <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
                    <Icon size={16} className="text-purple-400" />
                  </div>
                  {item.text}
                </motion.div>
              )
            })}
          </motion.div>
        </div>
      </div>

      {/* ─── Right Panel (form) ─── */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-radial opacity-20" />
        <div className="absolute inset-0 bg-grid opacity-10" />
        <FloatingParticles count={15} />

        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="relative z-10 w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex justify-center mb-8">
            <a href="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Building2 className="text-white" size={20} />
              </div>
              <span className="text-xl font-bold text-white tracking-tight">
                Outreach<span className="text-gradient">AI</span>
              </span>
            </a>
          </div>

          <TiltCard>
            <div className="glass-card rounded-2xl p-8 md:p-10 glow relative overflow-hidden">
              <FloatingParticles count={10} />
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-purple-500 via-violet-500 to-indigo-500" />

              {/* Tabs */}
              <div className="flex bg-white/5 rounded-xl p-1 mb-8">
                {[
                  { key: false, label: "Sign In" },
                  { key: true, label: "Sign Up" },
                ].map((tab) => (
                  <button
                    key={tab.label}
                    onClick={() => {
                      setIsSignup(tab.key)
                      setError("")
                    }}
                    className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${
                      isSignup === tab.key
                        ? "bg-purple-600 text-white shadow-lg shadow-purple-500/30"
                        : "text-gray-400 hover:text-white"
                    }`}
                    data-cursor-hover
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <AnimatePresence mode="wait">
                <motion.form
                  key={isSignup ? "signup" : "login"}
                  onSubmit={handleSubmit}
                  initial={{ opacity: 0, x: isSignup ? 20 : -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: isSignup ? -20 : 20 }}
                  transition={{ duration: 0.25 }}
                  className="space-y-4"
                >
                  {isSignup && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.05 }}
                    >
                      <label className="block text-sm text-gray-400 mb-1.5">Full Name</label>
                      <div className="relative group">
                        <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-purple-400 transition-colors" />
                        <input
                          type="text"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          placeholder="John Doe"
                          required
                          className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all text-sm"
                        />
                      </div>
                    </motion.div>
                  )}

                  <div>
                    <label className="block text-sm text-gray-400 mb-1.5">Email Address</label>
                    <div className="relative group">
                      <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-purple-400 transition-colors" />
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@company.com"
                        required
                        className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all text-sm"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-gray-400 mb-1.5">Password</label>
                    <div className="relative group">
                      <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                      <input
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        minLength={6}
                        className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-10 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all text-sm"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                        tabIndex={-1}
                        data-cursor-hover
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                    {isSignup && <PasswordStrength password={password} />}
                  </div>

                  {isSignup && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 }}
                    >
                      <label className="block text-sm text-gray-400 mb-1.5">Organization Name</label>
                      <div className="relative group">
                        <Building2 size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-purple-400 transition-colors" />
                        <input
                          type="text"
                          value={orgName}
                          onChange={(e) => setOrgName(e.target.value)}
                          placeholder="Acme Inc."
                          required
                          className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 transition-all text-sm"
                        />
                      </div>
                    </motion.div>
                  )}

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
                    >
                      {error}
                    </motion.div>
                  )}

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-purple-600 to-violet-600 text-white font-semibold text-sm shadow-lg shadow-purple-500/30 hover:shadow-purple-500/50 transition-all duration-200 disabled:opacity-50 flex items-center justify-center gap-2"
                    data-cursor-hover
                  >
                    {submitting ? (
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <>
                        {isSignup ? "Create Account" : "Sign In"}
                        <ArrowRight size={16} />
                      </>
                    )}
                  </button>

                  <div className="relative my-6">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-white/10" />
                    </div>
                    <div className="relative flex justify-center text-xs">
                      <span className="bg-[hsl(224,45%,7%)] px-3 text-gray-500">or continue with</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      // TODO: LinkedIn OAuth
                    }}
                    className="w-full py-3 rounded-xl bg-white/5 border border-white/10 text-white font-medium text-sm hover:bg-white/10 transition-all duration-200 flex items-center justify-center gap-2"
                    data-cursor-hover
                  >
                    <Linkedin size={18} className="text-blue-400" />
                    Continue with LinkedIn
                  </button>

                  {!isSignup && (
                    <div className="text-center pt-2">
                      <button className="text-sm text-gray-500 hover:text-purple-400 transition-colors" data-cursor-hover>
                        Forgot password?
                      </button>
                    </div>
                  )}
                </motion.form>
              </AnimatePresence>
            </div>
          </TiltCard>

          <p className="text-center text-xs text-gray-600 mt-6">
            By continuing, you agree to our{" "}
            <a href="/terms" className="text-gray-500 hover:text-purple-400 transition-colors underline underline-offset-2">
              Terms
            </a>{" "}
            and{" "}
            <a href="/privacy" className="text-gray-500 hover:text-purple-400 transition-colors underline underline-offset-2">
              Privacy Policy
            </a>
            .
          </p>
        </motion.div>
      </div>
    </div>
  )
}

/* ─── Needed for the left panel icons ─── */
const BarChart3 = (props: any) => (
  <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
  </svg>
)
