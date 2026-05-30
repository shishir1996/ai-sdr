"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import Link from "next/link"
import {
  Bot, ArrowLeft, Activity, Brain, Users, Mail, MessageCircle, Phone,
  BarChart3, Target, Play, Square, AlertCircle, Clock, RefreshCw,
  Sparkles, TrendingUp, Calendar, CheckCircle, XCircle, PauseCircle,
  Zap, MessageSquare, Globe, Linkedin, Trash2, Cpu,
} from "lucide-react"
import SDRStatusBadge, { type SDRRunState } from "@/components/ui/SDRStatusBadge"

interface TabDef {
  key: string
  label: string
  icon: any
}

const TABS: TabDef[] = [
  { key: "overview", label: "Overview", icon: Activity },
  { key: "campaigns", label: "Campaigns", icon: Target },
  { key: "sequences", label: "Sequences", icon: BarChart3 },
  { key: "leads", label: "Lead List", icon: Users },
  { key: "activity", label: "Activity", icon: Activity },
  { key: "reasoning", label: "AI Reasoning", icon: Brain },
  { key: "emails", label: "Emails", icon: Mail },
  { key: "linkedin", label: "LinkedIn", icon: Linkedin },
  { key: "calls", label: "Calls", icon: Phone },
  { key: "analytics", label: "Analytics", icon: TrendingUp },
  { key: "next", label: "Next Actions", icon: Zap },
  { key: "settings", label: "Settings", icon: Bot },
]

const STATUS_CFG: Record<string, { label: string; color: string; icon: any }> = {
  thinking: { label: "Thinking", color: "text-purple-400 bg-purple-500/10 border-purple-500/30", icon: Brain },
  researching: { label: "Analyzing", color: "text-violet-400 bg-violet-500/10 border-violet-500/30", icon: Cpu },
  analyzing: { label: "Analyzing", color: "text-violet-400 bg-violet-500/10 border-violet-500/30", icon: Cpu },
  drafting: { label: "Drafting", color: "text-amber-400 bg-amber-500/10 border-amber-500/30", icon: Mail },
  waiting_for_response: { label: "Waiting", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30", icon: Clock },
  sending_followup: { label: "Follow-up", color: "text-orange-400 bg-orange-500/10 border-orange-500/30", icon: SendIcon },
  idle: { label: "Idle", color: "text-gray-400 bg-gray-500/10 border-gray-500/30", icon: Activity },
  paused: { label: "Paused", color: "text-red-400 bg-red-500/10 border-red-500/30", icon: PauseCircle },
  executing: { label: "Executing", color: "text-green-400 bg-green-500/10 border-green-500/30", icon: Zap },
}

function SendIcon(props: any) { return <Zap {...props} /> }

/* ─── Format date with timezone ─── */
function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "Never"
  const d = new Date(iso)
  try {
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    })
  } catch {
    return d.toLocaleString()
  }
}

/* ─── Map SDR status to badge state ─── */
function toBadgeState(s: string | undefined): SDRRunState {
  if (!s || s === "idle" || s === "inactive") return "idle"
  if (s === "paused") return "paused"
  if (s === "error") return "error"
  return "running"
}

export default function SDRDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [sdr, setSdr] = useState<any>(null)
  const [status, setStatus] = useState<any>(null)
  const [perf, setPerf] = useState<any>(null)
  const [activities, setActivities] = useState<any[]>([])
  const [reasoning, setReasoning] = useState<any[]>([])
  const [leads, setLeads] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState("overview")
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState("")
  const [deleting, setDeleting] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState<any>(null)

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [profile, s, p, acts, reason, ls] = await Promise.all([
        api.get<any>(`/sdr/profiles/${id}`),
        api.get<any>(`/sdr/status?sdr_profile_id=${id}`).catch(() => null),
        api.get<any>(`/sdr/activity/performance?sdr_profile_id=${id}`).catch(() => null),
        api.get<any[]>(`/sdr/activity/feed?sdr_profile_id=${id}&limit=20`).catch(() => []),
        api.get<any[]>(`/sdr/activity/reasoning?sdr_profile_id=${id}&limit=10`).catch(() => []),
        api.get<any[]>(`/sdr/leads?sdr_profile_id=${id}`).catch(() => []),
      ])
      setSdr(profile)
      setStatus(s)
      setPerf(p)
      setActivities(acts)
      setReasoning(reason)
      setLeads(ls)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [id])

  useEffect(() => { loadAll() }, [loadAll])

  const toggleActivation = async () => {
    try {
      if (sdr.is_active) {
        await api.post(`/sdr/profiles/${sdr.id}/deactivate`)
      } else {
        await api.post(`/sdr/profiles/${sdr.id}/activate`)
      }
      await loadAll()
    } catch (e) { console.error(e) }
  }

  const openDeleteModal = async () => {
    try {
      const impact = await api.get<any>(`/sdr/profiles/${id}/deletion-impact`)
      setDeleteImpact(impact)
    } catch {}
    setShowDeleteModal(true)
    setDeleteConfirm("")
  }

  const confirmDelete = async () => {
    if (deleteConfirm !== "DELETE") return
    setDeleting(true)
    try {
      await api.post(`/sdr/profiles/${id}/delete`, { confirmation: "DELETE" })
      router.push("/sdr")
    } catch (e) {
      console.error(e)
      setDeleting(false)
    }
  }

  if (loading || !sdr) {
    return (
      <div className="space-y-6 animate-fade-in">
        <button onClick={() => router.push("/sdr")} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft size={16} /> Back to SDRs
        </button>
        <div className="text-center py-20 text-muted-foreground animate-pulse">
          <Bot size={40} className="mx-auto mb-3 text-purple-500/50" />
          Loading SDR workspace...
        </div>
      </div>
    )
  }

  const metrics = [
    { label: "Leads Processed", value: perf?.leads_processed || 0, icon: Users, color: "text-blue-500" },
    { label: "Campaigns Created", value: perf?.campaigns_created || 0, icon: Target, color: "text-purple-500" },
    { label: "Emails Drafted", value: perf?.emails_drafted || 0, icon: Mail, color: "text-green-500" },
    { label: "LinkedIn Invites", value: perf?.linkedin_invites_sent || 0, icon: Linkedin, color: "text-cyan-500" },
    { label: "Replies Detected", value: perf?.replies_detected || 0, icon: MessageSquare, color: "text-amber-500" },
    { label: "Meetings Booked", value: perf?.meetings_booked || 0, icon: Calendar, color: "text-emerald-500" },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back + header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/sdr")} className="p-2 rounded-lg hover:bg-white/5">
            <ArrowLeft size={18} className="text-muted-foreground" />
          </button>
          <div className="w-12 h-12 rounded-xl bg-purple-500/15 flex items-center justify-center">
            <Bot size={26} className="text-purple-500" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold">{sdr.name || "AI SDR"}</h1>
              <SDRStatusBadge state={toBadgeState(status?.current_status)} label={status?.current_status || "inactive"} />
            </div>
            <p className="text-xs text-muted-foreground">
              {sdr.target_titles ? `${sdr.target_titles.split(",")[0].trim()}` : "No ICP configured"}
              {sdr.region ? ` \u2022 ${sdr.region}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status?.current_action && (
            <span className="text-xs text-muted-foreground max-w-[200px] truncate hidden sm:block">
              <span className="text-purple-400">Now:</span> {status.current_action}
            </span>
          )}
          <button onClick={toggleActivation} className={`text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 ${sdr.is_active ? "bg-amber-500/10 text-amber-500 border border-amber-500/30" : "bg-green-500/10 text-green-500 border border-green-500/30"}`}>
            {sdr.is_active ? <><Square size={14} /> Deactivate</> : <><Play size={14} /> Activate</>}
          </button>
          <button onClick={loadAll} className="btn-ghost text-xs p-2"><RefreshCw size={14} /></button>
          <button onClick={openDeleteModal} className="btn-ghost text-xs p-2 text-red-500 hover:bg-red-500/10"><Trash2 size={14} /></button>
        </div>
      </div>

      {/* Status bar */}
      {status && (
        <div className={`card p-4 border-l-4 ${
          toBadgeState(status.current_status) === "error"
            ? "border-l-red-500"
            : toBadgeState(status.current_status) === "running"
              ? "border-l-emerald-500"
              : "border-l-blue-500"
        }`}>
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <SDRStatusBadge state={toBadgeState(status.current_status)} label={status.current_status || "inactive"} pulsate={false} />
              {status.current_action && <span className="text-muted-foreground">Action: <span className="text-white/80">{status.current_action}</span></span>}
              {status.next_planned_action && <span className="text-muted-foreground hidden md:inline">Next: <span className="text-cyan-400">{status.next_planned_action}</span></span>}
            </div>
            <span className="text-xs text-muted-foreground">
              {fmtDate(status.last_active_at)}
            </span>
          </div>
        </div>
      )}

      {/* Performance metrics */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="card p-3 text-center">
            <m.icon size={16} className={`mx-auto ${m.color}`} />
            <p className="text-xl font-bold mt-1">{m.value}</p>
            <p className="text-[10px] text-muted-foreground">{m.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border overflow-x-auto pb-px">
        {TABS.map((tab) => {
          const TabIcon = tab.icon
          const isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap shrink-0 ${
                isActive ? "border-purple-500 text-purple-400" : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <TabIcon size={14} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            {/* Activity Feed */}
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Activity size={16} className="text-purple-500" />
                Recent Activity
              </h3>
              {activities.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No activity yet. Activate the SDR to see actions.</p>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {activities.slice(0, 15).map((act, i) => (
                    <div key={act.id || i} className="flex items-start gap-3 p-2 rounded-lg hover:bg-white/5">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${act.status === "completed" ? "bg-green-500/10" : "bg-amber-500/10"}`}>
                        <Activity size={12} className={act.status === "completed" ? "text-green-500" : "text-amber-500"} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-white/90 truncate">{act.summary || act.stage || "Action"}</p>
                        <p className="text-[10px] text-muted-foreground">{fmtDate(act.created_at)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {/* Leads */}
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Users size={16} className="text-blue-500" />
                Lead Pipeline
              </h3>
              {leads.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No leads in pipeline.</p>
              ) : (
                <div className="space-y-1.5">
                  {leads.slice(0, 10).map((ls) => (
                    <div key={ls.lead_id} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5 text-xs">
                      <span className="font-medium truncate">{ls.lead_name || ls.lead_email || "Unknown"}</span>
                      <span className="capitalize text-muted-foreground shrink-0 ml-2">{ls.state?.replace(/_/g, " ")}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="space-y-4">
            {/* SDR config info */}
            <div className="card p-5">
              <h3 className="font-semibold mb-3 text-sm">Configuration</h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Type</span>
                  <span className="capitalize">{sdr.sell_type || "Not set"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tone</span>
                  <span className="capitalize">{sdr.outreach_tone || "professional"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Email</span>
                  <span className={sdr.has_email ? "text-green-500" : "text-red-500"}>{sdr.has_email ? "Connected" : "Not connected"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">LinkedIn</span>
                  <span className={sdr.has_linkedin ? "text-green-500" : "text-red-500"}>{sdr.has_linkedin ? "Connected" : "Not connected"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Daily Emails</span>
                  <span>{sdr.max_daily_emails || 20}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Lead Target</span>
                  <span>{sdr.leads_target || 100}</span>
                </div>
              </div>
            </div>
            {/* AI Reasoning */}
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Brain size={16} className="text-purple-500" />
                Latest Reasoning
              </h3>
              {reasoning.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">No AI decisions logged yet.</p>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {reasoning.slice(0, 5).map((r, i) => (
                    <div key={r.id || i} className="p-2 rounded-lg bg-white/5 text-xs">
                      <p className="text-purple-300 font-medium capitalize">{r.decision_type?.replace(/_/g, " ")}</p>
                      {r.human_readable_reasoning && (
                        <p className="text-muted-foreground mt-0.5 line-clamp-2">"{r.human_readable_reasoning}"</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Campaigns Tab */}
      {activeTab === "campaigns" && (
        <div className="card p-5">
          <p className="text-sm text-muted-foreground text-center py-8">
            Campaign management for this SDR will appear here. Active campaigns: {perf?.campaigns_created || 0}.
          </p>
        </div>
      )}

      {/* Sequences Tab */}
      {activeTab === "sequences" && (
        <div className="card p-5">
          <p className="text-sm text-muted-foreground text-center py-8">
            Outreach sequences will be displayed here.
          </p>
        </div>
      )}

      {/* Leads Tab */}
      {activeTab === "leads" && (
        <div className="card p-5">
          <h3 className="font-semibold mb-4 text-sm">Lead List</h3>
          {leads.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No leads assigned to this SDR.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-xs text-muted-foreground">
                    <th className="text-left py-2 px-2">Name</th>
                    <th className="text-left py-2 px-2">Email</th>
                    <th className="text-left py-2 px-2">Company</th>
                    <th className="text-left py-2 px-2">State</th>
                    <th className="text-left py-2 px-2">Contacts</th>
                    <th className="text-left py-2 px-2">Last Contacted</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map((ls) => (
                    <tr key={ls.lead_id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-2 px-2 font-medium">{ls.lead_name || "—"}</td>
                      <td className="py-2 px-2 text-muted-foreground">{ls.lead_email || "—"}</td>
                      <td className="py-2 px-2 text-muted-foreground">{ls.lead_company || "—"}</td>
                      <td className="py-2 px-2">
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 capitalize">{ls.state?.replace(/_/g, " ")}</span>
                      </td>
                      <td className="py-2 px-2">{ls.contact_count}</td>
                      <td className="py-2 px-2 text-muted-foreground">{fmtDate(ls.last_contacted_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Activity Tab */}
      {activeTab === "activity" && (
        <div className="space-y-2">
          {activities.length === 0 ? (
            <div className="card p-8 text-center text-muted-foreground">
              <p>No activity logged yet.</p>
            </div>
          ) : (
            activities.map((act, i) => (
              <div key={act.id || i} className="card p-4">
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${act.status === "completed" ? "bg-green-500/10" : "bg-amber-500/10"}`}>
                    {act.channel === "email" ? <Mail size={14} className="text-green-500" /> :
                     act.channel === "linkedin" ? <Linkedin size={14} className="text-cyan-500" /> :
                     <Activity size={14} className={act.status === "completed" ? "text-green-500" : "text-amber-500"} />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium">{(act.stage || act.action || "Action").replace(/_/g, " ")}</span>
                      {act.channel && <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 capitalize">{act.channel}</span>}
                      <span className="text-[10px] text-muted-foreground ml-auto">{fmtDate(act.created_at)}</span>
                    </div>
                    {act.summary && <p className="text-xs text-white/80 mt-1">{act.summary}</p>}
                    {act.reasoning && <p className="text-[10px] text-muted-foreground mt-0.5 italic">"{act.reasoning}"</p>}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* AI Reasoning Tab */}
      {activeTab === "reasoning" && (
        <div className="space-y-3">
          {reasoning.length === 0 ? (
            <div className="card p-8 text-center text-muted-foreground">
              <Brain size={36} className="mx-auto mb-3 text-purple-500/50" />
              <p>No AI reasoning logs yet.</p>
            </div>
          ) : (
            reasoning.map((r, i) => (
              <div key={r.id || i} className="card p-4">
                <div className="flex gap-3">
                  <Brain size={18} className="text-purple-500 mt-0.5 shrink-0" />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium capitalize">{r.decision_type?.replace(/_/g, " ")}</span>
                      {r.ai_confidence_score && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">{r.ai_confidence_score}%</span>
                      )}
                      <span className="text-[10px] text-muted-foreground ml-auto">{fmtDate(r.created_at)}</span>
                    </div>
                    {r.human_readable_reasoning && <p className="text-sm text-white/80">"{r.human_readable_reasoning}"</p>}
                    <div className="flex flex-wrap gap-2 mt-2 text-[10px]">
                      {r.channel_selected && <span className="text-cyan-400">Channel: {r.channel_selected}</span>}
                      {r.personalization_strategy && <span className="text-emerald-400">Strategy: {r.personalization_strategy}</span>}
                      {r.country_context && <span className="text-indigo-400">Country: {r.country_context}</span>}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Emails Tab */}
      {activeTab === "emails" && (
        <div className="card p-5">
          <p className="text-sm text-muted-foreground text-center py-8">
            {sdr.has_email ? "Email activity and tracking will appear here." : "Connect an email account in settings to get started."}
          </p>
        </div>
      )}

      {/* LinkedIn Tab */}
      {activeTab === "linkedin" && (
        <div className="card p-5">
          <p className="text-sm text-muted-foreground text-center py-8">
            {sdr.has_linkedin ? "LinkedIn outreach history will appear here." : "Connect a LinkedIn account in settings to get started."}
          </p>
        </div>
      )}

      {/* Calls Tab */}
      {activeTab === "calls" && (
        <div className="card p-5">
          <p className="text-sm text-muted-foreground text-center py-8">AI call logs will appear here.</p>
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === "analytics" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {metrics.map((m) => (
            <div key={m.label} className="card p-4 flex items-center gap-4">
              <div className={`w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center ${m.color}`}>
                <m.icon size={20} />
              </div>
              <div>
                <p className="text-2xl font-bold">{m.value}</p>
                <p className="text-xs text-muted-foreground">{m.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Next Actions Tab */}
      {activeTab === "next" && (
        <div className="card p-5">
          <p className="text-sm text-muted-foreground text-center py-8">
            AI recommendations for the next best actions will appear here.
          </p>
        </div>
      )}

      {/* Settings Tab */}
      {activeTab === "settings" && (
        <div className="max-w-2xl space-y-4">
          <div className="card p-5">
            <h3 className="font-semibold mb-4">SDR Profile</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-muted-foreground">Name</span>
                <span>{sdr.name || "AI SDR"}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-muted-foreground">Region</span>
                <span>{sdr.region || "Not set"}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-muted-foreground">Outreach Tone</span>
                <span className="capitalize">{sdr.outreach_tone || "professional"}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-muted-foreground">Personality</span>
                <span className="truncate max-w-[200px]">{sdr.sdr_personality || "Not set"}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-muted-foreground">Target Titles</span>
                <span className="truncate max-w-[200px]">{sdr.target_titles || "Not set"}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-muted-foreground">Target Industries</span>
                <span className="truncate max-w-[200px]">{sdr.target_industries || "Not set"}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-white/5">
                <span className="text-muted-foreground">Lead Target</span>
                <span>{sdr.leads_target || 100}</span>
              </div>
            </div>
          </div>

          <div className="card p-5">
            <h3 className="font-semibold mb-4">Connected Accounts</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                <div className="flex items-center gap-3">
                  <Mail size={18} className={sdr.has_email ? "text-green-500" : "text-gray-500"} />
                  <div>
                    <p className="text-sm font-medium">Email</p>
                    <p className="text-xs text-muted-foreground">{sdr.has_email ? sdr.email_sender || "Connected" : "Not connected"}</p>
                  </div>
                </div>
                <span className={`text-[10px] px-2 py-1 rounded-full ${sdr.has_email ? "bg-green-500/10 text-green-500" : "bg-gray-500/10 text-gray-500"}`}>
                  {sdr.has_email ? "Connected" : "Disconnected"}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                <div className="flex items-center gap-3">
                  <Linkedin size={18} className={sdr.has_linkedin ? "text-cyan-500" : "text-gray-500"} />
                  <div>
                    <p className="text-sm font-medium">LinkedIn</p>
                    <p className="text-xs text-muted-foreground">{sdr.has_linkedin ? "Connected" : "Not connected"}</p>
                  </div>
                </div>
                <span className={`text-[10px] px-2 py-1 rounded-full ${sdr.has_linkedin ? "bg-green-500/10 text-green-500" : "bg-gray-500/10 text-gray-500"}`}>
                  {sdr.has_linkedin ? "Connected" : "Disconnected"}
                </span>
              </div>
            </div>
            <div className="mt-4">
              <Link
                href={`/sdr/setup?edit=${sdr.id}`}
                className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
              >
                Edit configuration <ArrowLeft size={12} className="rotate-180" />
              </Link>
            </div>
          </div>

          <div className="card p-5 border-red-500/20">
            <h3 className="font-semibold mb-2 text-red-500 flex items-center gap-2">
              <AlertCircle size={16} />
              Danger Zone
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              Deleting this SDR will remove its configuration and disconnect all accounts. Lead data and campaign history will be preserved.
            </p>
            <button onClick={openDeleteModal} className="text-xs px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 border border-red-500/30 hover:bg-red-500/20 flex items-center gap-1.5">
              <Trash2 size={14} /> Delete SDR
            </button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="rounded-xl bg-gray-900 border border-white/10 p-6 w-full max-w-md mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-red-500/15 flex items-center justify-center">
                <AlertCircle size={22} className="text-red-500" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Delete SDR</h3>
                <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
              </div>
            </div>

            {deleteImpact && (
              <div className="mb-4 p-3 rounded-lg bg-white/5 text-xs space-y-1.5">
                <p className="font-medium text-amber-400 mb-2">Impact Summary:</p>
                <div className="flex justify-between"><span>Campaigns affected</span><span className="font-medium">{deleteImpact.total_campaigns} ({deleteImpact.active_campaigns} active)</span></div>
                <div className="flex justify-between"><span>Leads in pipeline</span><span className="font-medium">{deleteImpact.total_leads_associated}</span></div>
                <div className="flex justify-between"><span>Email connected</span><span className="font-medium">{deleteImpact.email_connected ? "Yes" : "No"}</span></div>
                <div className="flex justify-between"><span>LinkedIn connected</span><span className="font-medium">{deleteImpact.linkedin_connected ? "Yes" : "No"}</span></div>
                <div className="flex justify-between"><span>Activity history</span><span className="font-medium">{deleteImpact.has_activity_history ? "Yes" : "No"}</span></div>
                <p className="text-muted-foreground mt-2">Lead data and campaign history will be preserved.</p>
              </div>
            )}

            <p className="text-sm mb-3">
              Type <span className="font-mono font-bold text-red-500">DELETE</span> to confirm:
            </p>
            <input
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              placeholder="Type DELETE"
              className="input w-full mb-4 text-sm"
            />
            <div className="flex items-center justify-end gap-2">
              <button onClick={() => setShowDeleteModal(false)} className="btn-secondary text-xs px-3 py-1.5">
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleteConfirm !== "DELETE" || deleting}
                className="text-xs px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 border border-red-500/30 hover:bg-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
              >
                {deleting ? "Deleting..." : <><Trash2 size={14} /> Delete SDR</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


