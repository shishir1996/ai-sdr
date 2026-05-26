"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Activity, CheckCircle, XCircle, Clock, Mail, Phone, MessageCircle, Link as LinkIcon, PauseCircle, PlayCircle, StopCircle } from "lucide-react"

interface LeadStateItem {
  lead_id: string
  lead_name: string
  lead_email: string
  state: string
  is_paused: boolean
  contact_count: number
  channels_used: string[]
  last_contacted_at: string | null
}

interface LogEntry {
  id: string
  lead_id: string
  action: string
  channel: string
  reasoning: string
  result: string
  status: string
  created_at: string
}

const channelIcons: Record<string, any> = {
  email: Mail,
  phone: Phone,
  linkedin: MessageCircle,
  meeting: LinkIcon,
  payment: LinkIcon,
}

const channelColors: Record<string, string> = {
  email: "text-blue-500",
  phone: "text-purple-500",
  linkedin: "text-cyan-500",
  meeting: "text-green-500",
  payment: "text-yellow-500",
}

export default function AgentPage() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [leadStates, setLeadStates] = useState<LeadStateItem[]>([])
  const [progress, setProgress] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<"activity" | "leads">("activity")

  useEffect(() => { refresh() }, [])

  const refresh = async () => {
    try {
      const [l, ls, p] = await Promise.all([
        api.get<LogEntry[]>("/sdr/activity"),
        api.get<LeadStateItem[]>("/sdr/leads"),
        api.get<Record<string, number>>("/sdr/leads/progress"),
      ])
      setLogs(l)
      setLeadStates(ls)
      setProgress(p)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const pauseLead = async (leadId: string) => {
    await api.post(`/sdr/leads/${leadId}/pause`)
    refresh()
  }

  const resumeLead = async (leadId: string) => {
    await api.post(`/sdr/leads/${leadId}/resume`)
    refresh()
  }

  const stopLead = async (leadId: string) => {
    if (!confirm("Stop processing this lead?")) return
    await api.post(`/sdr/leads/${leadId}/stop`)
    refresh()
  }

  if (loading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Activity size={28} className="text-purple-500" />
        <h1 className="text-2xl font-semibold">Agent Activity</h1>
      </div>

      {/* Lead Progress Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Object.entries(progress).map(([state, count]) => (
          <div key={state} className="card p-4 text-center">
            <div className="text-2xl font-bold">{count}</div>
            <div className="text-xs text-muted-foreground capitalize">{state.replace(/_/g, " ")}</div>
          </div>
        ))}
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2 border-b border-border">
        <button onClick={() => setActiveTab("activity")} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === "activity" ? "border-brand-500 text-brand-500" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
          Activity Feed
        </button>
        <button onClick={() => setActiveTab("leads")} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === "leads" ? "border-brand-500 text-brand-500" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
          Lead Controls
        </button>
      </div>

      {/* Activity Feed Tab */}
      {activeTab === "activity" && (
        <div className="card p-5">
          {logs.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No activity yet. Configure and activate the AI SDR to see logs.
            </p>
          ) : (
            <div className="space-y-3">
              {logs.map((log) => {
                const Icon = channelIcons[log.channel] || Activity
                const color = channelColors[log.channel] || "text-muted-foreground"
                return (
                  <div key={log.id} className="flex items-start gap-3 p-3 rounded-lg border bg-surface-secondary">
                    <Icon size={18} className={`mt-0.5 shrink-0 ${color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium capitalize">{log.action.replace(/_/g, " ")}</span>
                        {log.status === "success" ? (
                          <CheckCircle size={14} className="text-green-500 shrink-0" />
                        ) : log.status === "failed" ? (
                          <XCircle size={14} className="text-red-500 shrink-0" />
                        ) : (
                          <Clock size={14} className="text-yellow-500 shrink-0" />
                        )}
                        <span className="text-xs text-muted-foreground ml-auto">
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{log.reasoning}</p>
                      {log.result && (
                        <p className="text-xs mt-1 truncate text-muted-foreground/80">{log.result}</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Lead Controls Tab */}
      {activeTab === "leads" && (
        <div className="card p-5">
          {leadStates.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No leads found. Import leads or enable Apollo auto-discovery.
            </p>
          ) : (
            <div className="space-y-2">
              {leadStates.map((ls) => (
                <div key={ls.lead_id} className="flex items-center justify-between p-3 rounded-lg border bg-surface-secondary">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{ls.lead_name || ls.lead_email}</span>
                      {ls.is_paused && (
                        <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-yellow-500/10 text-yellow-600">Paused</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                      <span className="capitalize">{ls.state.replace(/_/g, " ")}</span>
                      <span>{ls.contact_count} contacts</span>
                      {ls.channels_used.length > 0 && (
                        <span>via {ls.channels_used.join(", ")}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {ls.is_paused ? (
                      <button onClick={() => resumeLead(ls.lead_id)} className="p-2 rounded-lg hover:bg-green-500/10 text-green-600 transition-colors" title="Resume">
                        <PlayCircle size={18} />
                      </button>
                    ) : ls.state !== "archived" && ls.state !== "closed_won" && ls.state !== "closed_lost" ? (
                      <button onClick={() => pauseLead(ls.lead_id)} className="p-2 rounded-lg hover:bg-yellow-500/10 text-yellow-600 transition-colors" title="Pause">
                        <PauseCircle size={18} />
                      </button>
                    ) : null}
                    {ls.state !== "archived" && ls.state !== "closed_won" && ls.state !== "closed_lost" && (
                      <button onClick={() => stopLead(ls.lead_id)} className="p-2 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors" title="Stop">
                        <StopCircle size={18} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
