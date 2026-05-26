"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { BarChart3, Users, Mail, Phone, TrendingUp, Target, Activity, RefreshCw, MessageCircle, Calendar, DollarSign, CheckCircle, MousePointerClick } from "lucide-react"

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
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between"><h1 className="text-2xl font-semibold">Dashboard</h1></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="card p-5 animate-pulse"><div className="h-8 w-20 rounded bg-muted" /><div className="h-4 w-16 mt-2 rounded bg-muted" /></div>)}
        </div>
      </div>
    )
  }

  const d = data!

  const statCards = [
    { label: "Total Leads", value: d.total_leads, sub: `${d.leads_today} today`, icon: Users, color: "text-blue-500", bg: "bg-blue-500/10" },
    { label: "Emails Sent", value: d.emails_sent, sub: `${d.open_rate}% open · ${d.reply_rate}% reply`, icon: Mail, color: "text-green-500", bg: "bg-green-500/10" },
    { label: "Calls Made", value: d.calls_made, sub: `${d.avg_call_duration}s avg`, icon: Phone, color: "text-purple-500", bg: "bg-purple-500/10" },
    { label: "Won Deals", value: d.won_deals, sub: `$${d.won_deals_value.toLocaleString()}`, icon: DollarSign, color: "text-amber-500", bg: "bg-amber-500/10" },
    { label: "Positive Replies", value: d.positive_replies, sub: "interested leads", icon: MessageCircle, color: "text-emerald-500", bg: "bg-emerald-500/10" },
    { label: "Meetings Booked", value: d.meetings_booked, sub: "scheduled", icon: Calendar, color: "text-cyan-500", bg: "bg-cyan-500/10" },
    { label: "SDR Actions (7d)", value: d.sdr_actions_7d, sub: `${d.sdr_actions_today} today`, icon: Activity, color: "text-rose-500", bg: "bg-rose-500/10" },
    { label: "Forecast", value: `$${d.forecast_value.toLocaleString()}`, sub: "weighted pipeline", icon: TrendingUp, color: "text-indigo-500", bg: "bg-indigo-500/10" },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">SDR performance, analytics, and forecast</p>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2"><RefreshCw size={14} /> Refresh</button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="card p-5 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className={`p-2 rounded-lg ${stat.bg}`}><Icon size={20} className={stat.color} /></div>
              </div>
              <p className="text-2xl font-bold">{stat.value}</p>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              <p className="text-xs text-muted-foreground/70 mt-0.5">{stat.sub}</p>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lead Stages */}
        <div className="card p-5">
          <h3 className="font-medium mb-4">Lead Qualification Stages</h3>
          {Object.keys(d.lead_stages).length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No leads in pipeline yet</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(d.lead_stages).map(([stage, count]) => (
                <div key={stage} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-muted-foreground">{stage.replace(/_/g, " ")}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Email Timeline */}
        <div className="card p-5">
          <h3 className="font-medium mb-4">Email Activity (7 days)</h3>
          {d.email_timeline.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No email activity</p>
          ) : (
            <div className="space-y-2 text-sm">
              {d.email_timeline.map((day) => (
                <div key={day.date} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-16">{day.date.slice(5)}</span>
                  <div className="flex-1 flex gap-4">
                    <span className="text-blue-500">{day.sent} sent</span>
                    {day.opened > 0 && <span className="text-green-500">{day.opened} opened</span>}
                    {day.replied > 0 && <span className="text-amber-500">{day.replied} replied</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Deal Sources */}
        <div className="card p-5">
          <h3 className="font-medium mb-4">Won Deals by Source</h3>
          {d.deals_by_source.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">No won deals yet</p>
          ) : (
            <div className="space-y-2">
              {d.deals_by_source.map((ds) => (
                <div key={ds.source} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-muted-foreground">{ds.source.replace(/_/g, " ")}</span>
                  <div className="flex gap-3">
                    <span className="font-medium">{ds.count}</span>
                    <span className="text-muted-foreground">${ds.value.toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Email Rates */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card p-4"><div className="flex items-center gap-2 text-sm text-green-500"><CheckCircle size={16} /> Open Rate</div><p className="text-xl font-bold mt-1">{d.open_rate}%</p></div>
        <div className="card p-4"><div className="flex items-center gap-2 text-sm text-amber-500"><MessageCircle size={16} /> Reply Rate</div><p className="text-xl font-bold mt-1">{d.reply_rate}%</p></div>
        <div className="card p-4"><div className="flex items-center gap-2 text-sm text-red-500"><Mail size={16} /> Bounce Rate</div><p className="text-xl font-bold mt-1">{d.bounce_rate}%</p></div>
        <div className="card p-4"><div className="flex items-center gap-2 text-sm text-blue-500"><MousePointerClick size={16} /> Click Rate</div><p className="text-xl font-bold mt-1">{d.click_rate}%</p></div>
      </div>

      {/* Active Campaigns */}
      <div className="card p-5">
        <h3 className="font-medium mb-4">Campaigns ({d.active_campaigns} active / {d.total_campaigns} total)</h3>
        {d.campaigns.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">No campaigns yet</p>
        ) : (
          <div className="space-y-2">
            {d.campaigns.map((c) => (
              <div key={c.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-muted transition-colors">
                <span className="text-sm font-medium">{c.name}</span>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === "active" ? "bg-green-500/10 text-green-600" : "bg-muted text-muted-foreground"}`}>{c.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
