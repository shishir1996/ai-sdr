"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard, Users, Mail, PhoneCall, Target, BarChart3, Settings,
  ChevronLeft, ChevronRight, Building2, Plug, ToggleLeft, Brain, Activity,
} from "lucide-react"
import { useState } from "react"
const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/campaigns", label: "Campaigns", icon: Target },
  { href: "/emails", label: "Email", icon: Mail },
  { href: "/calls", label: "Phone", icon: PhoneCall },
  { href: "/deals", label: "Deals", icon: BarChart3 },
  { type: "divider" as const },
  { href: "/sdr", label: "AI SDR", icon: Brain },
  { href: "/agent", label: "Agent Activity", icon: Activity },
  { type: "divider" as const },
  { href: "/admin/integrations", label: "Integrations", icon: Plug },
  { href: "/admin/feature-flags", label: "Feature Flags", icon: ToggleLeft },
  { href: "/admin/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`flex flex-col bg-sidebar border-r border-white/10 transition-all duration-200 ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      <div className="flex items-center gap-3 px-4 h-14 border-b border-white/10">
        <Building2 className="text-brand-400 shrink-0" size={24} />
        {!collapsed && <span className="font-semibold text-sidebar-fg text-lg">AI SDR</span>}
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          if ("type" in item && item.type === "divider") {
            return <div key="divider" className="my-2 border-t border-white/10" />
          }
          const isActive = pathname === item.href
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${isActive ? "sidebar-link-active" : ""}`}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={20} className="shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      <div className="flex items-center justify-between px-3 py-3 border-t border-white/10">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 rounded-lg hover:bg-white/5 text-sidebar-muted hover:text-sidebar-fg transition-colors"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>
    </aside>
  )
}
