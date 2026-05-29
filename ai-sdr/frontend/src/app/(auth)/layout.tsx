"use client"
import { useEffect } from "react"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    document.documentElement.classList.add("dark")
  }, [])

  return (
    <div className="min-h-screen bg-[hsl(224,45%,4%)] relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-mesh opacity-40" />
      <div className="absolute inset-0 bg-grid opacity-20" />

      <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-purple-500/15 blur-[150px] animate-pulse-glow" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-blue-500/10 blur-[120px] animate-float" />
      <div className="absolute top-[40%] right-[20%] w-[400px] h-[400px] rounded-full bg-cyan-500/8 blur-[100px] animate-pulse-glow" />

      {children}
    </div>
  )
}
