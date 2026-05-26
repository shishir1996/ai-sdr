"use client"

import { useState, useRef, useEffect } from "react"
import { Bell, Search, LogOut, User, Settings, Sparkles, ChevronDown } from "lucide-react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"


export function Header() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [searchFocused, setSearchFocused] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const { user } = useAuth()

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const logout = () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    localStorage.removeItem("org_id")
    router.push("/login")
  }

  const initials = user?.name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) || "AS"

  return (
    <header className="flex items-center justify-between h-14 px-5 border-b border-white/[0.04] bg-[hsl(224,45%,7%)/80] backdrop-blur-xl sticky top-0 z-40">
      {/* Search */}
      <div className={`flex items-center gap-3 flex-1 max-w-md rounded-xl px-3 py-1.5 transition-all duration-200 ${
        searchFocused ? "bg-white/8 ring-1 ring-purple-500/30" : "bg-white/[0.03] hover:bg-white/[0.05]"
      }`}>
        <Search size={16} className="text-gray-500 shrink-0" />
        <input
          type="text"
          placeholder="Search leads, campaigns..."
          onFocus={() => setSearchFocused(true)}
          onBlur={() => setSearchFocused(false)}
          className="flex-1 bg-transparent text-sm text-white outline-none placeholder:text-gray-500"
        />
        {searchFocused && (
          <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-white/5 text-[10px] text-gray-500 border border-white/10">
            ⌘K
          </kbd>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <button className="relative p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-all duration-200 group">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-purple-500 rounded-full shadow-[0_0_6px_hsl(262,80%,55%)]" />
          <div className="absolute inset-0 rounded-xl bg-purple-500/0 group-hover:bg-purple-500/5 transition-colors" />
        </button>

        {/* Divider */}
        <div className="w-px h-6 bg-white/[0.04] mx-1" />

        {/* User Menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-white/5 transition-all duration-200 group"
          >
            <div className="relative">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-xs font-bold text-white shadow-lg shadow-purple-500/20">
                {initials}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-[hsl(224,45%,7%)]" />
            </div>
            <ChevronDown size={14} className={`text-gray-500 transition-transform duration-200 ${menuOpen ? "rotate-180" : ""}`} />
          </button>

          {menuOpen && (
            <div className="absolute right-0 mt-2 w-56 glass rounded-2xl border border-white/10 shadow-2xl py-2 z-50 animate-scale-in origin-top-right">
              {/* User info */}
              <div className="px-4 py-3 border-b border-white/5">
                <p className="text-sm font-medium text-white">{user?.name || "AI SDR Admin"}</p>
                <p className="text-xs text-gray-400 mt-0.5">{user?.email || "admin@offdx.in"}</p>
              </div>

              <div className="py-1">
                <a
                  href="/admin/settings"
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-300 hover:text-white hover:bg-white/5 transition-colors"
                  onClick={() => setMenuOpen(false)}
                >
                  <Settings size={16} className="text-gray-500" />
                  Settings
                </a>
              </div>

              <div className="border-t border-white/5 py-1">
                <button
                  onClick={logout}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-white/5 transition-colors w-full text-left"
                >
                  <LogOut size={16} />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
