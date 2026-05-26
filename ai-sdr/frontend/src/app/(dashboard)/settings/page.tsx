"use client"

import { useState } from "react"
import { Save, LogOut } from "lucide-react"
import { useRouter } from "next/navigation"

export default function SettingsPage() {
  const router = useRouter()

  const handleLogout = () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    router.push("/login")
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your account and platform settings.</p>
      </div>

      <div className="card p-5 space-y-4">
        <h3 className="font-semibold">Account</h3>
        <p className="text-sm text-muted-foreground">You are logged in as an admin.</p>
        <button onClick={handleLogout} className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-500/10 transition-colors">
          <LogOut size={16} /> Sign Out
        </button>
      </div>

      <div className="card p-5 space-y-4">
        <h3 className="font-semibold">Quick Links</h3>
        <div className="space-y-2 text-sm">
          <a href="/admin/integrations" className="block text-brand-600 hover:text-brand-700">Configure Integrations →</a>
          <a href="/admin/feature-flags" className="block text-brand-600 hover:text-brand-700">Manage Feature Flags →</a>
          <a href="/admin/settings" className="block text-brand-600 hover:text-brand-700">Organization Settings →</a>
          <a href="/sdr" className="block text-brand-600 hover:text-brand-700">AI SDR Configuration →</a>
        </div>
      </div>
    </div>
  )
}
