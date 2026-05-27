"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import {
  BarChart3, Users, Mail, Phone, TrendingUp, Target, Activity, RefreshCw,
  MessageCircle, Calendar, DollarSign, CheckCircle, MousePointerClick,
  Sparkles, Zap, ArrowUp, ArrowDown, ChevronRight, Bot,
} from "lucide-react"

interface DashboardData {
  total_leads: number
  leads_today: number
  lead_stages: Record<string, number>
  emails_sent: number
  emails_opened: number
  emails_replied: number
  emails_bounced: number
  emails_clicked: number
  open_rate: number
  reply_rate: number
  bounce_rate: number
  click_rate: number
  email_timeline: { date: string; sent: number; opened: number; replied: number }[]
  total_calls: number
  calls_made: number
  calls_connected: number
  avg_call_duration: number
  call_outcomes: Record<string, number>
  total_campaigns: number
  active_campaigns: number
  campaigns: { id: string; name: string; status: string; created_at: string }[]
  total_deals: number
  won_deals: number
  won_deals_value: number
  deals_by_source: { source: string; count: number; value: number }[]
  sdr_actions: Record<string, number>
  sdr_actions_today: number
  sdr_actions_7d: number
  positive_replies: number
  meetings_booked: number
  forecast_value: number
}

function StatCard({ label, value, sub, icon: Icon, color, delay, trend }: {
  label: string; value: string | number; sub: string; icon: any; color: string; delay: number; trend?: "up" | "down"
}) {
  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.03] backdrop-blur-sm p-5 hover:border-white/[0.12] transition-all duration-300 animate-in cursor-default`}
      style={{ animationDelay: `${delay * 0.1}s` }}
    >
      {/* Hover glow */}
      <div className={`absolute -inset-20 opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-3xl pointer-events-none`}
        style={{ background: `radial-gradient(circle, hsl(var(--glow-${color === "text-purple-400" ? "purple" : color === "text-blue-400" ? "blue" : "purple"}) / 0.08), transparent)` }}
      />

      <div className="relative">
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] group-hover:scale-105 transition-transform duration-300`}>
            <Icon size={18} className={color} />
          </div>
          {trend && (
            <div className={`flex items-center gap-1 text-xs ${trend === "up" ? "text-emerald-400" : "text-red-400"}`}>
              {trend === "up" ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
              12%
            </div>
          )}
        </div>
        <p className="stat-value text-white group-hover:scale-[1.02] origin-left transition-transform duration-300">{value}</p>
        <p className="stat-label mt-1">{label}</p>
        <p className="text-xs text-gray-500 mt-0.5">{sub}</p>
      </div>
    </div>
  )
}

function GlassCard({ title, children, className = "", icon: Icon, action, style }: {
  title: string; children: React.ReactNode; className?: string; icon?: any; action?: React.ReactNode; style?: React.CSSProperties
}) {
  return (
    <div className={`rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-5 hover:border-white/[0.1] transition-all duration-300 ${className}`} style={style}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          {Icon && (
            <div className="p-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20">
              <Icon size={16} className="text-purple-400" />
            </div>
          )}
          <h3 className="text-sm font-semibold text-white/80">{title}</h3>
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const d = await api.get<DashboardData>("/analytics/dashboard")
      setData(d)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-48 bg-white/5 rounded-xl animate-pulse" />
            <div className="h-4 w-64 bg-white/5 rounded-lg mt-2 animate-pulse" />
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1,2,3,4,5,6,7,8].map(i => (
            <div key={i} className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 animate-pulse">
              <div className="h-10 w-10 rounded-xl bg-white/5" />
              <div className="h-8 w-24 bg-white/5 rounded-lg mt-4" />
              <div className="h-4 w-20 bg-white/5 rounded mt-2" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  const d = data!

  const statCards = [
    { label: "Total Leads", value: d.total_leads, sub: `${d.leads_today} new today`, icon: Users, color: "text-blue-400", delay: 1, trend: d.leads_today > 0 ? "up" as const : undefined },
    { label: "Emails Sent", value: d.emails_sent, sub: `${d.open_rate}% open · ${d.reply_rate}% reply`, icon: Mail, color: "text-emerald-400", delay: 2 },
    { label: "Calls Made", value: d.calls_made, sub: `${d.avg_call_duration}s avg duration`, icon: Phone, color: "text-purple-400", delay: 3 },
    { label: "Won Deals", value: d.won_deals, sub: `$${d.won_deals_value.toLocaleString()}`, icon: DollarSign, color: "text-amber-400", delay: 4 },
    { label: "Positive Replies", value: d.positive_replies, sub: "interested leads", icon: MessageCircle, color: "text-emerald-400", delay: 5 },
    { label: "Meetings Booked", value: d.meetings_booked, sub: "scheduled", icon: Calendar, color: "text-cyan-400", delay: 6 },
    { label: "SDR Actions (7d)", value: d.sdr_actions_7d, sub: `${d.sdr_actions_today} today`, icon: Zap, color: "text-rose-400", delay: 7, trend: "up" as const },
    { label: "Forecast", value: `$${d.forecast_value.toLocaleString()}`, sub: "weighted pipeline", icon: TrendingUp, color: "text-indigo-400", delay: 8 },
  ]

  const stages = Object.entries(d.lead_stages)
  const maxStageCount = Math.max(...stages.map(([, c]) => c), 1)

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center justify-between animate-in">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div className="p-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20">
              <Sparkles size={16} className="text-purple-400" />
            </div>
            <h1 className="text-xl font-bold text-white">Dashboard</h1>
          </div>
          <p className="text-sm text-gray-400 ml-9">SDR performance, analytics, and revenue forecast</p>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2 group">
          <RefreshCw size={14} className="group-hover:rotate-180 transition-transform duration-500" />
          Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      {/* Second row: Lead Stages + Email Timeline + Deal Sources */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Lead Stages */}
        <GlassCard title="Lead Qualification" icon={Target} className="animate-in" style={{ animationDelay: "0.9s" }}
          action={
            stages.length > 0 && (
              <span className="text-xs text-gray-500">{stages.reduce((s, [, c]) => s + c, 0)} total</span>
            )
          }
        >
          {stages.length === 0 ? (
            <div className="text-center py-8">
              <Users size={32} className="mx-auto text-gray-600 mb-2" />
              <p className="text-sm text-gray-500">No leads in pipeline yet</p>
              <p className="text-xs text-gray-600 mt-1">Create leads or start a campaign</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {stages.map(([stage, count], i) => (
                <div key={stage} className="animate-in" style={{ animationDelay: `${1 + i * 0.1}s` }}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <span className="text-gray-400 capitalize text-xs">{stage.replace(/_/g, " ")}</span>
                    <span className="font-semibold text-white text-xs">{count}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-purple-500 to-violet-500 transition-all duration-1000"
                      style={{ width: `${(count / maxStageCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        {/* Email Timeline */}
        <GlassCard title="Email Activity (7 days)" icon={Mail} className="animate-in" style={{ animationDelay: "1s" }}
          action={d.email_timeline.length > 0 && <span className="text-xs text-gray-500">{d.emails_sent} total</span>}
        >
          {d.email_timeline.length === 0 ? (
            <div className="text-center py-8">
              <Mail size={32} className="mx-auto text-gray-600 mb-2" />
              <p className="text-sm text-gray-500">No email activity</p>
              <p className="text-xs text-gray-600 mt-1">Start a campaign to see email metrics</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {d.email_timeline.map((day, i) => (
                <div key={day.date} className="flex items-center gap-3 animate-in" style={{ animationDelay: `${1 + i * 0.08}s` }}>
                  <span className="text-xs text-gray-500 w-16 shrink-0 font-mono">{day.date.slice(5)}</span>
                  <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-1000"
                      style={{ width: `${(day.sent / Math.max(...d.email_timeline.map(x => x.sent), 1)) * 100}%` }}
                    />
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {day.sent > 0 && <span className="text-[11px] text-blue-400">{day.sent}</span>}
                    {day.opened > 0 && <span className="text-[11px] text-emerald-400">+{day.opened}</span>}
                    {day.replied > 0 && <span className="text-[11px] text-amber-400">+{day.replied}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        {/* Won Deals by Source */}
        <GlassCard title="Won Deals by Source" icon={DollarSign} className="animate-in" style={{ animationDelay: "1.1s" }}>
          {d.deals_by_source.length === 0 ? (
            <div className="text-center py-8">
              <BarChart3 size={32} className="mx-auto text-gray-600 mb-2" />
              <p className="text-sm text-gray-500">No won deals yet</p>
              <p className="text-xs text-gray-600 mt-1">Close deals to see source breakdown</p>
            </div>
          ) : (
            <div className="space-y-3">
              {d.deals_by_source.map((ds, i) => {
                const pct = d.won_deals_value > 0 ? ((ds.value / d.won_deals_value) * 100).toFixed(0) : "0"
                return (
                  <div key={ds.source} className="animate-in" style={{ animationDelay: `${1.1 + i * 0.1}s` }}>
                    <div className="flex items-center justify-between text-sm mb-1.5">
                      <span className="text-gray-400 capitalize text-xs">{ds.source.replace(/_/g, " ")}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-white font-semibold text-xs">{ds.count}</span>
                        <span className="text-gray-500 text-xs">${ds.value.toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-1000"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </GlassCard>
      </div>

      {/* Email Rates Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-in" style={{ animationDelay: "1.2s" }}>
        {[
          { label: "Open Rate", value: `${d.open_rate}%`, icon: CheckCircle, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
          { label: "Reply Rate", value: `${d.reply_rate}%`, icon: MessageCircle, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
          { label: "Bounce Rate", value: `${d.bounce_rate}%`, icon: Mail, color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20" },
          { label: "Click Rate", value: `${d.click_rate}%`, icon: MousePointerClick, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
        ].map((item, i) => {
          const Icon = item.icon
          return (
            <div key={item.label} className={`rounded-xl border ${item.border} ${item.bg}/20 backdrop-blur-sm p-4 hover:-translate-y-0.5 transition-all duration-300`}
              style={{ animationDelay: `${1.2 + i * 0.1}s` }}>
              <div className="flex items-center gap-2.5 mb-2">
                <Icon size={16} className={item.color} />
                <span className="text-xs text-gray-400 font-medium">{item.label}</span>
              </div>
              <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
            </div>
          )
        })}
      </div>

      {/* Campaigns */}
      <GlassCard title={`Campaigns (${d.active_campaigns} active / ${d.total_campaigns} total)`} icon={Target} className="animate-in" style={{ animationDelay: "1.3s" }}
        action={
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Bot size={12} className="text-purple-400" />
            AI SDR managed
          </span>
        }
      >
        {d.campaigns.length === 0 ? (
          <div className="text-center py-8">
            <Target size={32} className="mx-auto text-gray-600 mb-2" />
            <p className="text-sm text-gray-500">No campaigns yet</p>
            <p className="text-xs text-gray-600 mt-1">Create your first campaign in the SDR config</p>
          </div>
        ) : (
          <div className="space-y-2">
            {d.campaigns.map((c, i) => (
              <div key={c.id}
                className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] transition-all duration-200 group cursor-default animate-in"
                style={{ animationDelay: `${1.3 + i * 0.05}s` }}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${c.status === "active" ? "bg-emerald-500 shadow-[0_0_8px_hsl(160,84%,50%)]" : "bg-gray-600"}`} />
                  <span className="text-sm font-medium text-white/80">{c.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2.5 py-1 rounded-lg font-medium ${
                    c.status === "active"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : c.status === "completed"
                      ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                      : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                  }`}>
                    {c.status}
                  </span>
                  <ChevronRight size={14} className="text-gray-600 group-hover:text-gray-400 transition-colors" />
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
