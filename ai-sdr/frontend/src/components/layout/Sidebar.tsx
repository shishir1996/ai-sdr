"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard, Users, Mail, PhoneCall, Target, BarChart3, Settings,
  ChevronLeft, ChevronRight, Building2, Plug, ToggleLeft, Brain, Activity,
  ScrollText, Sparkles, Phone, PhoneForwarded, Crown, Search,
  SlidersHorizontal,
} from "lucide-react"
import { useState } from "react"

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/campaigns", label: "Campaigns", icon: Target },
  { href: "/emails", label: "Email", icon: Mail },
  { href: "/calls", label: "Call Logs", icon: Phone },
  { href: "/deals", label: "Deals", icon: BarChart3 },
  { type: "divider" as const },
  { href: "/vp/command-center", label: "VP Command Center", icon: Crown },
  { href: "/vp/dashboard", label: "VP Dashboard", icon: Activity },
  { href: "/vp/agents", label: "Research Agents", icon: Search },
  { href: "/vp/lead-sources", label: "Lead Sources", icon: SlidersHorizontal },
  { type: "divider" as const },
  { href: "/sdr", label: "AI SDR", icon: Brain },
  { href: "/agent", label: "Agent Activity", icon: Activity },
  { href: "/audit", label: "Monitoring", icon: ScrollText },
  { type: "divider" as const },
  { href: "/admin/calling", label: "AI Calling", icon: PhoneForwarded },
  { href: "/admin/integrations", label: "Integrations", icon: Plug },
  { href: "/admin/feature-flags", label: "Feature Flags", icon: ToggleLeft },
  { href: "/admin/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`flex flex-col bg-[hsl(224,45%,4%)] border-r border-white/[0.04] transition-all duration-300 relative ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      {/* Gradient accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent" />

      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-white/[0.04] relative">
        <div className="relative shrink-0">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Building2 className="text-white" size={18} />
          </div>
          <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-[hsl(224,45%,4%)]" />
        </div>
        {!collapsed && (
          <div className="animate-fade-in">
            <span className="font-bold text-sidebar-fg text-base">AI SDR</span>
            <span className="block text-[10px] text-gray-500 tracking-wide uppercase">Platform</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item, idx) => {
          if ("type" in item && item.type === "divider") {
            return <div key={`d-${idx}`} className="my-2 border-t border-white/[0.04]" />
          }
          const isActive = pathname === item.href
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link group ${isActive ? "sidebar-link-active" : ""}`}
              title={collapsed ? item.label : undefined}
            >
              <div className="relative">
                <Icon size={18} className={`shrink-0 transition-all duration-200 ${
                  isActive ? "text-purple-400" : "text-gray-500 group-hover:text-gray-300"
                }`} />
                {isActive && (
                  <div className="absolute -inset-1 bg-purple-500/20 rounded-full blur-sm animate-pulse-glow" />
                )}
              </div>
              {!collapsed && (
                <span className={`transition-all duration-200 ${
                  isActive ? "text-white font-medium" : "text-gray-400 group-hover:text-gray-200"
                }`}>
                  {item.label}
                </span>
              )}
              {isActive && !collapsed && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-purple-500 shadow-[0_0_6px_hsl(262,80%,55%)]" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Bottom section */}
      <div className="px-2 py-3 border-t border-white/[0.04] space-y-1">
        <div className="px-3 py-2">
          {!collapsed && (
            <div className="p-2 rounded-xl bg-gradient-to-r from-purple-500/5 to-violet-500/5 border border-purple-500/10">
              <div className="flex items-center gap-2 text-xs text-purple-300">
                <Sparkles size={12} />
                <span>AI SDR Active</span>
              </div>
            </div>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 rounded-xl text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-all duration-200"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  )
}
