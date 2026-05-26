"use client"

import { useState, useRef, useEffect } from "react"
import { Bell, Search, LogOut, User, Settings } from "lucide-react"
import { useRouter } from "next/navigation"
import { ThemeToggle } from "./ThemeToggle"

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

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
    router.push("/login")
  }

  return (
    <header className="flex items-center justify-between h-14 px-6 border-b bg-surface">
      <div className="flex items-center gap-3 flex-1 max-w-md">
        <Search size={18} className="text-muted-foreground" />
        <input
          type="text"
          placeholder="Search leads, campaigns..."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <button className="p-2 rounded-lg hover:bg-muted transition-colors">
          <Bell size={18} className="text-muted-foreground" />
        </button>
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-xs font-medium text-white hover:bg-brand-700 transition-colors cursor-pointer"
          >
            AS
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-popover border border-border rounded-lg shadow-lg py-1 z-50">
              <a href="/admin/settings" className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted transition-colors" onClick={() => setMenuOpen(false)}>
                <Settings size={16} /> Settings
              </a>
              <hr className="border-border my-1" />
              <button onClick={logout} className="flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-muted transition-colors w-full text-left">
                <LogOut size={16} /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
