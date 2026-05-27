"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { Building2, Sparkles, Mail, Lock, User, Globe, ArrowRight, Linkedin } from "lucide-react"

export default function LoginPage() {
  const [isSignup, setIsSignup] = useState(false)
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [orgName, setOrgName] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="relative">
          <div className="w-12 h-12 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
          <div className="w-12 h-12 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin-slow absolute inset-0" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="relative w-full max-w-md">
        {/* Glow behind card */}
        <div className="absolute -inset-4 bg-gradient-to-r from-purple-600/20 via-violet-600/20 to-indigo-600/20 rounded-3xl blur-2xl" />

        <div className="relative glass rounded-3xl p-8 animate-scale-in">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-8">
            <div className="relative">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Building2 className="text-white" size={24} />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-[hsl(224,45%,6%)] flex items-center justify-center">
                <Sparkles size={8} className="text-white" />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">AI SDR</h1>
              <p className="text-xs text-gray-400">Sales Development Platform</p>
            </div>
          </div>

          <h2 className="text-lg font-semibold text-white/90 text-center mb-2">
            {isSignup ? "Create your workspace" : "Welcome back"}
          </h2>
          <p className="text-sm text-gray-400 text-center mb-8">
            {isSignup ? "Set up your AI SDR account" : "Sign in to your AI SDR dashboard"}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isSignup && (
              <>
                <div className="relative group">
                  <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-purple-400 transition-colors" />
                  <input
                    type="text"
                    placeholder="Your name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="input pl-10"
                    required
                  />
                </div>
                <div className="relative group">
                  <Globe size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-purple-400 transition-colors" />
                  <input
                    type="text"
                    placeholder="Organization name"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="input pl-10"
                    required
                  />
                </div>
              </>
            )}

            <div className="relative group">
              <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-purple-400 transition-colors" />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input pl-10"
                required
              />
            </div>

            <div className="relative group">
              <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-purple-400 transition-colors" />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input pl-10"
                required
              />
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400 animate-slide-in">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="btn-primary w-full group relative overflow-hidden"
            >
              {submitting ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {isSignup ? "Creating..." : "Signing in..."}
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  {isSignup ? "Create Account" : "Sign In"}
                  <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
                </span>
              )}
            </button>
          </form>

          {/* OAuth Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/[0.06]" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-3 bg-[hsl(224,45%,6%)] text-gray-500">Or continue with</span>
            </div>
          </div>

          {/* Google OAuth */}
          <a
            href="/api/auth/google/login"
            className="group relative w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl border border-white/[0.06] bg-white/[0.03] backdrop-blur-sm hover:border-white/[0.12] hover:bg-white/[0.06] transition-all duration-300 text-sm text-gray-300 hover:text-white mb-3"
          >
            <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </a>

          {/* LinkedIn OAuth */}
          <a
            href="/api/auth/linkedin/login"
            className="group relative w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl border border-white/[0.06] bg-white/[0.03] backdrop-blur-sm hover:border-white/[0.12] hover:bg-white/[0.06] transition-all duration-300 text-sm text-gray-300 hover:text-white"
          >
            <Linkedin size={20} className="text-[#0A66C2]" />
            Continue with LinkedIn
          </a>

          <div className="mt-8 text-center">
            <p className="text-sm text-gray-400">
              {isSignup ? "Already have an account?" : "Don't have an account?"}{" "}
              <button
                onClick={() => { setIsSignup(!isSignup); setError("") }}
                className="text-purple-400 hover:text-purple-300 font-medium transition-colors"
              >
                {isSignup ? "Sign in" : "Sign up"}
              </button>
            </p>
          </div>

          {!isSignup && (
            <div className="mt-4 p-3 rounded-xl bg-white/5 border border-white/10 text-xs text-gray-500 text-center">
              Demo: test@sdr.ai / password123
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
