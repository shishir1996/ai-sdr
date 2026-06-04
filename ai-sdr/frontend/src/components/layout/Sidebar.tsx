"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Crown, Users, Mail, Target, Activity, Settings, ChevronLeft, ChevronRight, Sparkles } from "lucide-react"
import { useState } from "react"

const navItems = [
  { href: "/vp", label: "VP Sales Team", icon: Crown },
  { href: "/sdr", label: "SDR Agents", icon: Activity },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/campaigns", label: "Campaigns", icon: Target },
  { href: "/emails", label: "Email", icon: Mail },
  { type: "divider" as const },
  { href: "/admin/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={`flex flex-col bg-[hsl(224,45%,4%)] border-r border-white/[0.04] transition-all duration-300 relative ${collapsed ? "w-16" : "w-60"}`}>
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent" />
      <div className="flex items-center gap-3 px-4 h-14 border-b border-white/[0.04]">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
          <Crown className="text-white" size={18} />
        </div>
        {!collapsed && (
          <div>
            <span className="font-bold text-white text-base">AI Sales</span>
            <span className="block text-[10px] text-gray-500 tracking-wide uppercase">Team</span>
          </div>
        )}
      </div>
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item, idx) => {
          if ("type" in item && item.type === "divider") {
            return <div key={`d-${idx}`} className="my-2 border-t border-white/[0.04]" />
          }
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
          const Icon = item.icon
          return (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-all ${
                isActive ? "bg-emerald-500/10 text-emerald-400 font-medium" : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
              }`}
              title={collapsed ? item.label : undefined}>
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>
      <div className="px-2 py-3 border-t border-white/[0.04]">
        {!collapsed && (
          <div className="p-2 rounded-xl bg-gradient-to-r from-emerald-500/5 to-teal-500/5 border border-emerald-500/10 mb-2">
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <Sparkles size={12} />
              <span>Sales Team Active</span>
            </div>
          </div>
        )}
        <button onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 rounded-xl text-gray-500 hover:text-gray-300 hover:bg-white/5">
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  )
}
