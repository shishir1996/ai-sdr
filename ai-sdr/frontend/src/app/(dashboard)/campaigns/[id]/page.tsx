"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import {
  Target, Mail, Phone, Users, RefreshCw, CheckCircle, Clock,
  BarChart3, MessageCircle, Bot, Brain, ArrowLeft, Activity,
  Sparkles, TrendingUp, ChevronRight, DollarSign, Calendar,
  MessageSquare, PauseCircle, PlayCircle, AlertCircle,
} from "lucide-react"

const STAGE_LABELS: Record<string, string> = {
  new: "New", contacted: "Contacted", replied: "Replied",
  meeting_booked: "Meeting Booked", qualified: "Qualified",
  closed_won: "Won", closed_lost: "Lost", archived: "Archived",
}

const STAGE_COLORS: Record<string, string> = {
  new: "bg-blue-500/10 text-blue-400",
  contacted: "bg-amber-500/10 text-amber-400",
  replied: "bg-green-500/10 text-green-400",
  meeting_booked: "bg-purple-500/10 text-purple-400",
  qualified: "bg-emerald-500/10 text-emerald-400",
  closed_won: "bg-green-500/10 text-green-400",
  closed_lost: "bg-red-500/10 text-red-400",
  archived: "bg-gray-500/10 text-gray-400",
}

const CHANNEL_ICONS: Record<string, any> = {
  email: Mail, linkedin: MessageCircle, phone: Phone, meeting: Calendar,
}

const CHANNEL_COLORS: Record<string, string> = {
  email: "text-green-500 bg-green-500/10 border-green-500/30",
  linkedin: "text-cyan-500 bg-cyan-500/10 border-cyan-500/30",
  phone: "text-amber-500 bg-amber-500/10 border-amber-500/30",
  meeting: "text-purple-500 bg-purple-500/10 border-purple-500/30",
}

function ChannelIcon({ channel, size = 14 }: { channel: string; size?: number }) {
  const Icon = CHANNEL_ICONS[channel] || Mail
  return <Icon size={size} />
}

interface CampaignDetail {
  id: string
  name: string
  description: string | null
  status: string
  ai_generated: boolean
  sdr_profile_id: string | null
  sdr_name: string
  created_at: string
  steps: { channel: string; step_order: number; delay_days: number; template_id?: string; call_script_id?: string }[]
  leads_count: number
  emails_sent: number
  emails_opened: number
  emails_replied: number
  pipeline?: Record<string, number>
  recent_reasoning?: { action: string; channel: string; reasoning: string; result: string; created_at: string }[]
}

export default function CampaignDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [campaign, setCampaign] = useState<CampaignDetail | null>(null)
  const [dashboard, setDashboard] = useState<CampaignDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [statusUpdating, setStatusUpdating] = useState(false)

  useEffect(() => {
    load()
  }, [id])

  const load = async () => {
    setLoading(true)
    try {
      const c = await api.get<CampaignDetail>(`/campaigns/${id}`)
      setCampaign(c)

      if (c.sdr_profile_id) {
        const data = await api.get<CampaignDetail[]>(`/sdr/campaign-dashboard?sdr_profile_id=${c.sdr_profile_id}`)
        const match = data.find((d: any) => d.id === id)
        if (match) setDashboard(match)
      }
    } catch (e: any) {
      console.error("Failed to load campaign", e)
    } finally {
      setLoading(false)
    }
  }

  const updateStatus = async (status: string) => {
    setStatusUpdating(true)
    try {
      await api.put(`/campaigns/${id}/status?status=${status}`, {})
      await load()
    } catch (e) {
      console.error(e)
    } finally {
      setStatusUpdating(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <button onClick={() => router.back()} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft size={16} /> Back to Campaigns
        </button>
        <div className="text-center py-20 text-muted-foreground animate-pulse">Loading campaign dashboard...</div>
      </div>
    )
  }

  if (!campaign) {
    return (
      <div className="space-y-6 animate-fade-in">
        <button onClick={() => router.push("/campaigns")} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft size={16} /> Back to Campaigns
        </button>
        <div className="card p-8 text-center text-muted-foreground">
          <AlertCircle size={40} className="mx-auto mb-3 text-red-500/50" />
          <p>Campaign not found.</p>
        </div>
      </div>
    )
  }

  const c = dashboard || campaign
  const sent = c.emails_sent || 0
  const opened = c.emails_opened || 0
  const replied = c.emails_replied || 0
  const openRate = sent > 0 ? Math.round((opened / sent) * 100) : 0
  const replyRate = sent > 0 ? Math.round((replied / sent) * 100) : 0
  const pipeline = dashboard?.pipeline || {}
  const pipelineTotal = Object.values(pipeline).reduce((a: number, b: any) => a + (typeof b === "number" ? b : 0), 0)
  const reasoningLogs = dashboard?.recent_reasoning || []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back + Header */}
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => router.push("/campaigns")} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft size={14} /> Back to Campaigns
          </button>
          <div className="flex items-center gap-3">
            <Target size={28} className="text-purple-500" />
            <h1 className="text-2xl font-semibold">{c.name}</h1>
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
              c.status === "active" ? "bg-green-500/10 text-green-500 border border-green-500/30" :
              c.status === "paused" ? "bg-amber-500/10 text-amber-500 border border-amber-500/30" :
              c.status === "completed" ? "bg-blue-500/10 text-blue-500 border border-blue-500/30" :
              "bg-gray-500/10 text-gray-400 border border-gray-500/30"
            }`}>{c.status}</span>
            {c.ai_generated && (
              <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-purple-500/10 text-purple-500 border border-purple-500/30 flex items-center gap-1">
                <Sparkles size={12} /> AI Generated
              </span>
            )}
          </div>
          {c.description && <p className="text-sm text-muted-foreground mt-1 ml-1">{c.description}</p>}
          <p className="text-xs text-muted-foreground mt-1 ml-1">Created {new Date(c.created_at).toLocaleDateString()}</p>
        </div>
        <div className="flex items-center gap-2">
          {c.sdr_name && (
            <span className="text-xs px-2.5 py-1.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/30 flex items-center gap-1.5">
              <Bot size={12} /> {c.sdr_name}
            </span>
          )}
          {(c.status === "draft" || c.status === "paused") && (
            <button
              onClick={() => updateStatus("active")}
              disabled={statusUpdating}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              <PlayCircle size={14} /> Activate
            </button>
          )}
          {c.status === "active" && (
            <button
              onClick={() => updateStatus("paused")}
              disabled={statusUpdating}
              className="btn-secondary text-xs flex items-center gap-1.5"
            >
              <PauseCircle size={14} /> Pause
            </button>
          )}
          <button onClick={load} className="btn-ghost text-xs"><RefreshCw size={14} /></button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        {[
          { label: "Leads", value: c.leads_count, icon: Users, color: "text-blue-500" },
          { label: "Emails Sent", value: sent, icon: Mail, color: "text-green-500" },
          { label: "Opened", value: opened, icon: MessageSquare, color: "text-amber-500" },
          { label: "Replies", value: replied, icon: MessageCircle, color: "text-emerald-500" },
          { label: "Open Rate", value: `${openRate}%`, icon: BarChart3, color: "text-purple-500", sub: `${opened}/${sent}` },
          { label: "Reply Rate", value: `${replyRate}%`, icon: CheckCircle, color: "text-indigo-500", sub: `${replied}/${sent}` },
        ].map((s) => (
          <div key={s.label} className="card p-3 text-center">
            <s.icon size={16} className={`mx-auto ${s.color}`} />
            <p className="text-xl font-bold mt-1">{s.value}</p>
            <p className="text-xs text-muted-foreground">{s.label}</p>
            {s.sub && <p className="text-[10px] text-muted-foreground">{s.sub}</p>}
          </div>
        ))}
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Steps + Pipeline */}
        <div className="lg:col-span-2 space-y-6">
          {/* Campaign Steps */}
          <div className="card p-5">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Activity size={16} className="text-purple-500" />
              Campaign Sequence
            </h3>
            {(!c.steps || c.steps.length === 0) ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No steps defined yet. Add steps to build your outreach sequence.</p>
            ) : (
              <div className="space-y-3">
                {c.steps.map((step, i) => {
                  const colorClass = CHANNEL_COLORS[step.channel] || "text-gray-400 bg-gray-500/10 border-gray-500/30"
                  return (
                    <div key={i} className="flex items-start gap-3">
                      <div className="flex flex-col items-center">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${colorClass}`}>
                          <ChannelIcon channel={step.channel} size={18} />
                        </div>
                        {i < c.steps.length - 1 && <div className="w-px h-6 bg-white/10 mt-1" />}
                      </div>
                      <div className="flex-1 pt-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium capitalize">{step.channel}</span>
                          <span className="text-xs text-muted-foreground">Step {step.step_order}</span>
                          {step.delay_days > 0 && (
                            <span className="text-xs text-amber-400 flex items-center gap-1">
                              <Clock size={11} /> {step.delay_days}d delay
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Lead Pipeline */}
          <div className="card p-5">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <BarChart3 size={16} className="text-emerald-500" />
              Lead Pipeline
            </h3>
            {pipelineTotal === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No leads in the pipeline for this campaign.</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(pipeline).map(([state, count]: [string, any]) => {
                  const pct = pipelineTotal > 0 ? Math.round(((typeof count === "number" ? count : 0) / pipelineTotal) * 100) : 0
                  const colorClass = STAGE_COLORS[state] || "bg-gray-500/10 text-gray-400"
                  return (
                    <div key={state} className="flex items-center gap-3">
                      <span className={`text-xs font-medium px-2 py-1 rounded w-24 text-center shrink-0 ${colorClass}`}>
                        {STAGE_LABELS[state] || state}
                      </span>
                      <div className="flex-1 h-2.5 rounded-full bg-white/5 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-green-500 transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-8 text-right shrink-0">{count}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: AI Reasoning + SDR Info */}
        <div className="space-y-6">
          {/* SDR Assignment */}
          <div className="card p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Bot size={16} className="text-brand-500" />
              SDR Assignment
            </h3>
            {c.sdr_name ? (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-brand-500/20 flex items-center justify-center">
                  <Bot size={20} className="text-brand-500" />
                </div>
                <div>
                  <p className="text-sm font-medium">{c.sdr_name}</p>
                  <p className="text-xs text-muted-foreground">AI SDR Profile</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No SDR assigned to this campaign.</p>
            )}
          </div>

          {/* AI Reasoning */}
          <div className="card p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Brain size={16} className="text-purple-500" />
              AI Reasoning
            </h3>
            {reasoningLogs.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No AI reasoning yet.</p>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {reasoningLogs.slice(0, 6).map((log: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-white/5 border border-white/10">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium capitalize text-purple-300">{log.action?.replace(/_/g, " ") || "Action"}</span>
                      {log.channel && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full capitalize bg-cyan-500/10 text-cyan-400">{log.channel}</span>
                      )}
                    </div>
                    {log.reasoning && <p className="text-xs text-muted-foreground mb-1">"{log.reasoning}"</p>}
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span className={log.result === "success" ? "text-green-400" : log.result === "skipped" ? "text-amber-400" : "text-red-400"}>{log.result || "pending"}</span>
                      <span>{new Date(log.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="card p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Zap size={16} className="text-amber-500" />
              Actions
            </h3>
            <div className="space-y-2">
              <button
                onClick={() => router.push(`/leads?campaign_id=${id}`)}
                className="w-full text-xs p-2.5 rounded-lg bg-white/5 border border-white/10 text-left hover:bg-white/10 transition-colors"
              >
                <Users size={14} className="inline mr-1.5 text-blue-400" />
                View Campaign Leads
              </button>
              <button
                onClick={() => router.push(`/emails?campaign_id=${id}`)}
                className="w-full text-xs p-2.5 rounded-lg bg-white/5 border border-white/10 text-left hover:bg-white/10 transition-colors"
              >
                <Mail size={14} className="inline mr-1.5 text-green-400" />
                View Email Activity
              </button>
              <button
                onClick={() => router.push(`/deals?campaign_id=${id}`)}
                className="w-full text-xs p-2.5 rounded-lg bg-white/5 border border-white/10 text-left hover:bg-white/10 transition-colors"
              >
                <DollarSign size={14} className="inline mr-1.5 text-emerald-400" />
                View Deals
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Zap(props: any) { return <Sparkles {...props} /> }
