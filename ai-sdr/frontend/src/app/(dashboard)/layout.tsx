"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Sidebar } from "@/components/layout/Sidebar"
import { Header } from "@/components/layout/Header"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [checked, setChecked] = useState(false)
  const router = useRouter()

  useEffect(() => {
    document.documentElement.classList.add("dark")

    const token = localStorage.getItem("access_token")
    if (!token) {
      router.replace("/")
    } else {
      setChecked(true)
    }
  }, [router])

  if (!checked) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-secondary">
        <div className="animate-spin w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 bg-surface-secondary">
          {children}
        </main>
      </div>
    </div>
  )
}
