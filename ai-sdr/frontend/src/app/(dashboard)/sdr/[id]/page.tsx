"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import {
  Bot, ArrowLeft, Activity, Brain, Users, Mail,
  Target, Play, Square, AlertCircle, Clock, RefreshCw,
  Sparkles, TrendingUp, Calendar, Linkedin, Phone,
  ChevronRight, MessageSquare, Cpu, BarChart3,
  Save, Trash2, Key, Eye, EyeOff,
} from "lucide-react"
import SDRStatusBadge, { type SDRRunState } from "@/components/ui/SDRStatusBadge"

interface NavItem {
  key: string
  label: string
  icon: any
}

const NAV_ITEMS: NavItem[] = [
  { key: "campaigns", label: "Campaigns", icon: Target },
  { key: "timeline", label: "Timeline", icon: Activity },
  { key: "email", label: "Email", icon: Mail },
  { key: "linkedin", label: "LinkedIn", icon: Linkedin },
  { key: "calls", label: "Calls", icon: Phone },
  { key: "channels", label: "Channels", icon: Cpu },
  { key: "leads", label: "Leads", icon: Users },
  { key: "reasoning", label: "AI Reasoning", icon: Brain },
  { key: "next", label: "Next Actions", icon: Sparkles },
]

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "Never"
  const d = new Date(iso)
  try {
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short",
    })
  } catch { return d.toLocaleString() }
}

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
  const [campaigns, setCampaigns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] = useState("campaigns")

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [profile, s, p, acts, reason, ls, camps] = await Promise.all([
        api.get<any>(`/sdr/profiles/${id}`),
        api.get<any>(`/sdr/status?sdr_profile_id=${id}`).catch(() => null),
        api.get<any>(`/sdr/activity/performance?sdr_profile_id=${id}`).catch(() => null),
        api.get<any[]>(`/sdr/activity/feed?sdr_profile_id=${id}&limit=50`).catch(() => []),
        api.get<any[]>(`/sdr/activity/reasoning?sdr_profile_id=${id}&limit=20`).catch(() => []),
        api.get<any[]>(`/sdr/leads?sdr_profile_id=${id}`).catch(() => []),
        api.get<any[]>(`/campaigns?sdr_profile_id=${id}`).catch(() => []),
      ])
      setSdr(profile)
      setStatus(s)
      setPerf(p)
      setActivities(acts)
      setReasoning(reason)
      setLeads(ls)
      setCampaigns(camps)
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
    { label: "Leads", value: perf?.leads_processed || 0, icon: Users, color: "text-blue-500" },
    { label: "Campaigns", value: perf?.campaigns_created || 0, icon: Target, color: "text-purple-500" },
    { label: "Emails", value: perf?.emails_drafted || 0, icon: Mail, color: "text-green-500" },
    { label: "LinkedIn", value: perf?.linkedin_invites_sent || 0, icon: Linkedin, color: "text-cyan-500" },
    { label: "Replies", value: perf?.replies_detected || 0, icon: MessageSquare, color: "text-amber-500" },
    { label: "Meetings", value: perf?.meetings_booked || 0, icon: Calendar, color: "text-emerald-500" },
  ]

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/sdr")} className="p-2 rounded-lg hover:bg-white/5">
            <ArrowLeft size={18} className="text-muted-foreground" />
          </button>
          <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
            <Bot size={22} className="text-purple-500" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">{sdr.name || "AI SDR"}</h1>
              <SDRStatusBadge state={toBadgeState(status?.current_status)} label={status?.current_status || "inactive"} />
            </div>
            <p className="text-xs text-muted-foreground">
              {sdr.target_titles ? sdr.target_titles.split(",")[0].trim() : "No ICP configured"}
              {sdr.region ? ` \u2022 ${sdr.region}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={toggleActivation} className={`text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 ${sdr.is_active ? "bg-amber-500/10 text-amber-500 border border-amber-500/30" : "bg-green-500/10 text-green-500 border border-green-500/30"}`}>
            {sdr.is_active ? <><Square size={14} /> Deactivate</> : <><Play size={14} /> Activate</>}
          </button>
          <button onClick={loadAll} className="btn-ghost text-xs p-2"><RefreshCw size={14} /></button>
        </div>
      </div>

      {status && (
        <div className={`card p-3 mb-6 border-l-4 ${
          toBadgeState(status.current_status) === "error"
            ? "border-l-red-500"
            : toBadgeState(status.current_status) === "running"
              ? "border-l-emerald-500"
              : "border-l-blue-500"
        }`}>
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <SDRStatusBadge state={toBadgeState(status.current_status)} label={status.current_status || "inactive"} pulsate={false} />
              {status.current_action && <span className="text-muted-foreground text-xs">{status.current_action}</span>}
              {status.next_planned_action && <span className="text-muted-foreground text-xs hidden md:inline">Next: <span className="text-cyan-400">{status.next_planned_action}</span></span>}
            </div>
            <span className="text-xs text-muted-foreground">{fmtDate(status.last_active_at)}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-6">
        {metrics.map((m) => (
          <div key={m.label} className="card p-2.5 text-center">
            <m.icon size={14} className={`mx-auto ${m.color}`} />
            <p className="text-lg font-bold mt-0.5">{m.value}</p>
            <p className="text-[9px] text-muted-foreground">{m.label}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-6">
        <nav className="w-44 shrink-0 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const isActive = activeSection === item.key
            const NavIcon = item.icon
            return (
              <button
                key={item.key}
                onClick={() => setActiveSection(item.key)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                }`}
              >
                <NavIcon size={14} />
                {item.label}
              </button>
            )
          })}
        </nav>

        <div className="flex-1 min-w-0 space-y-4">
          {activeSection === "campaigns" && (
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Target size={16} className="text-purple-500" />
                Active Campaigns
              </h3>
              {campaigns.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No campaigns created yet.</p>
              ) : (
                <div className="space-y-2">
                  {campaigns.map((c, i) => (
                    <div key={c.id || i} className="p-3 rounded-lg bg-white/5 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">{c.name || c.campaign_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {c.status || "active"} {c.lead_count ? `\u2022 ${c.lead_count} leads` : ""}
                        </p>
                      </div>
                      <ChevronRight size={14} className="text-muted-foreground" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeSection === "timeline" && (
            <div className="space-y-1">
              {activities.length === 0 ? (
                <div className="card p-8 text-center text-muted-foreground">
                  <Activity size={36} className="mx-auto mb-3 text-purple-500/50" />
                  <p className="text-sm">No activity yet. Activate the SDR to start seeing actions.</p>
                </div>
              ) : (
                activities.map((act, i) => (
                  <div key={act.id || i} className="card p-3 flex items-start gap-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                      act.status === "completed" ? "bg-green-500/10" : "bg-amber-500/10"
                    }`}>
                      {act.channel === "email" ? <Mail size={12} className="text-green-500" /> :
                       act.channel === "linkedin" ? <Linkedin size={12} className="text-cyan-500" /> :
                       <Activity size={12} className={act.status === "completed" ? "text-green-500" : "text-amber-500"} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium">{(act.stage || act.action || "Action").replace(/_/g, " ")}</span>
                        {act.channel && <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 capitalize">{act.channel}</span>}
                        <span className="text-[10px] text-muted-foreground ml-auto">{fmtDate(act.created_at)}</span>
                      </div>
                      {act.summary && <p className="text-xs text-white/80 mt-0.5">{act.summary}</p>}
                      {act.reasoning && <p className="text-[10px] text-muted-foreground mt-0.5 italic">"{act.reasoning}"</p>}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeSection === "email" && (
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Mail size={16} className="text-green-500" />
                Email Activity
              </h3>
              {sdr.has_email ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="p-3 rounded-lg bg-white/5 text-center">
                      <p className="text-lg font-bold text-green-500">{perf?.emails_drafted || 0}</p>
                      <p className="text-[10px] text-muted-foreground">Emails Drafted</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 text-center">
                      <p className="text-lg font-bold text-amber-500">{perf?.replies_detected || 0}</p>
                      <p className="text-[10px] text-muted-foreground">Replies</p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground text-center py-4">
                    Email tracking and draft history will appear here.
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  Connect an email account in settings to get started.
                </p>
              )}
            </div>
          )}

          {activeSection === "linkedin" && (
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Linkedin size={16} className="text-cyan-500" />
                LinkedIn Activity
              </h3>
              {sdr.has_linkedin ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="p-3 rounded-lg bg-white/5 text-center">
                      <p className="text-lg font-bold text-cyan-500">{perf?.linkedin_invites_sent || 0}</p>
                      <p className="text-[10px] text-muted-foreground">Invites Sent</p>
                    </div>
                    <div className="p-3 rounded-lg bg-white/5 text-center">
                      <p className="text-lg font-bold text-purple-500">{perf?.linkedin_messages_sent || 0}</p>
                      <p className="text-[10px] text-muted-foreground">Messages</p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground text-center py-4">
                    LinkedIn outreach history will appear here.
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">
                  Connect a LinkedIn account in settings to get started.
                </p>
              )}
            </div>
          )}

          {activeSection === "calls" && (
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Phone size={16} className="text-orange-500" />
                Calling Activity
              </h3>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 rounded-lg bg-white/5 text-center">
                  <p className="text-lg font-bold text-orange-500">{perf?.calls_made || 0}</p>
                  <p className="text-[10px] text-muted-foreground">Calls Made</p>
                </div>
                <div className="p-3 rounded-lg bg-white/5 text-center">
                  <p className="text-lg font-bold text-emerald-500">{perf?.call_connections || 0}</p>
                  <p className="text-[10px] text-muted-foreground">Connections</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground text-center py-4">AI call logs will appear here.</p>
            </div>
          )}

          {activeSection === "channels" && (
            <ChannelsConfig sdr={sdr} onUpdate={loadAll} />
          )}

          {activeSection === "leads" && (
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Users size={16} className="text-blue-500" />
                Lead Pipeline
              </h3>
              {leads.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No leads in pipeline.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10 text-xs text-muted-foreground">
                        <th className="text-left py-2 px-2">Name</th>
                        <th className="text-left py-2 px-2">Email</th>
                        <th className="text-left py-2 px-2">Company</th>
                        <th className="text-left py-2 px-2">State</th>
                        <th className="text-left py-2 px-2">Last Contacted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leads.map((ls) => (
                        <tr key={ls.lead_id} className="border-b border-white/5 hover:bg-white/5">
                          <td className="py-2 px-2 font-medium text-xs">{ls.lead_name || "—"}</td>
                          <td className="py-2 px-2 text-muted-foreground text-xs">{ls.lead_email || "—"}</td>
                          <td className="py-2 px-2 text-muted-foreground text-xs">{ls.lead_company || "—"}</td>
                          <td className="py-2 px-2">
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 capitalize">{ls.state?.replace(/_/g, " ")}</span>
                          </td>
                          <td className="py-2 px-2 text-muted-foreground text-xs">{fmtDate(ls.last_contacted_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeSection === "reasoning" && (
            <div className="space-y-2">
              {reasoning.length === 0 ? (
                <div className="card p-8 text-center text-muted-foreground">
                  <Brain size={36} className="mx-auto mb-3 text-purple-500/50" />
                  <p className="text-sm">No AI reasoning logged yet.</p>
                </div>
              ) : (
                reasoning.map((r, i) => (
                  <div key={r.id || i} className="card p-4">
                    <div className="flex gap-3">
                      <Brain size={16} className="text-purple-500 mt-0.5 shrink-0" />
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium capitalize">{r.decision_type?.replace(/_/g, " ")}</span>
                          {r.ai_confidence_score && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">{r.ai_confidence_score}%</span>
                          )}
                          <span className="text-[10px] text-muted-foreground ml-auto">{fmtDate(r.created_at)}</span>
                        </div>
                        {r.human_readable_reasoning && <p className="text-sm text-white/80">"{r.human_readable_reasoning}"</p>}
                        <div className="flex flex-wrap gap-2 mt-1.5 text-[10px]">
                          {r.channel_selected && <span className="text-cyan-400">Channel: {r.channel_selected}</span>}
                          {r.personalization_strategy && <span className="text-emerald-400">Strategy: {r.personalization_strategy}</span>}
                          {r.country_context && <span className="text-indigo-400">Country: {r.country_context}</span>}
                        </div>
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {r.lead_first_name && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">{r.lead_first_name}</span>
                          )}
                          {r.lead_company_name && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">{r.lead_company_name}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeSection === "next" && (
            <div className="card p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
                <Sparkles size={16} className="text-amber-500" />
                Next Planned Actions
              </h3>
              {status?.next_planned_action ? (
                <div className="space-y-3">
                  <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
                    <p className="text-xs text-amber-400 mb-1">Next Action</p>
                    <p className="text-sm text-white/90">{status.next_planned_action}</p>
                  </div>
                  {status.next_action_time && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Clock size={12} />
                      Scheduled: {fmtDate(status.next_action_time)}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-sm text-muted-foreground mb-2">No upcoming actions planned.</p>
                  {!sdr.is_active && (
                    <p className="text-xs text-muted-foreground">Activate the SDR to start generating action plans.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ChannelsConfig({ sdr, onUpdate }: { sdr: any; onUpdate: () => void }) {
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null)
  const [emailOn, setEmailOn] = useState<boolean>(!!(sdr.email_enabled ?? sdr.has_email))
  const [linkedinOn, setLinkedinOn] = useState<boolean>(!!(sdr.linkedin_enabled ?? sdr.has_linkedin))
  const [vapiOn, setVapiOn] = useState<boolean>(!!sdr.vapi_enabled)
  const [hasVapi, setHasVapi] = useState<boolean>(!!(sdr.vapi_credentials_encrypted && sdr.vapi_credentials_encrypted.length > 0))
  const [showKey, setShowKey] = useState(false)
  const [vapiForm, setVapiForm] = useState({
    api_key: "",
    phone_number: sdr.vapi_phone || "",
    assistant_id: sdr.vapi_assistant_id || "",
    voice_id: sdr.vapi_voice_id || "",
    first_message: sdr.vapi_first_message || "Hi, this is a quick call from {{company}}.",
  })

  useEffect(() => {
    setEmailOn(!!(sdr.email_enabled ?? sdr.has_email))
    setLinkedinOn(!!(sdr.linkedin_enabled ?? sdr.has_linkedin))
    setVapiOn(!!sdr.vapi_enabled)
    setHasVapi(!!(sdr.vapi_credentials_encrypted && sdr.vapi_credentials_encrypted.length > 0))
  }, [sdr])

  const saveChannels = async () => {
    setSaving(true); setMsg(null)
    try {
      await api.put(`/sdr/profiles/${sdr.id}/channels`, {
        email_enabled: emailOn,
        linkedin_enabled: linkedinOn,
        vapi_enabled: vapiOn && hasVapi,
      })
      setMsg({ type: "ok", text: "Channels updated" })
      onUpdate()
    } catch (e: any) {
      setMsg({ type: "err", text: e.message || "Failed to update channels" })
    } finally { setSaving(false) }
  }

  const saveVapi = async () => {
    if (!vapiForm.api_key && !vapiForm.phone_number && !vapiForm.assistant_id) {
      setMsg({ type: "err", text: "Fill at least API key or phone number" })
      return
    }
    setSaving(true); setMsg(null)
    try {
      await api.put(`/sdr/profiles/${sdr.id}/vapi-creds`, vapiForm)
      setVapiForm((f) => ({ ...f, api_key: "" }))
      setHasVapi(true)
      setMsg({ type: "ok", text: "Vapi credentials saved" })
      onUpdate()
    } catch (e: any) {
      setMsg({ type: "err", text: e.message || "Failed to save Vapi credentials" })
    } finally { setSaving(false) }
  }

  const removeVapi = async () => {
    if (!confirm("Remove Vapi credentials and disable voice calling?")) return
    setSaving(true); setMsg(null)
    try {
      await api.delete(`/sdr/profiles/${sdr.id}/vapi-creds`)
      setHasVapi(false); setVapiOn(false)
      setMsg({ type: "ok", text: "Vapi credentials removed" })
      onUpdate()
    } catch (e: any) {
      setMsg({ type: "err", text: e.message || "Failed to remove Vapi" })
    } finally { setSaving(false) }
  }

  const resetConfig = async () => {
    if (!confirm("Reset all channel configuration? This will clear credentials and disable all channels.")) return
    setSaving(true); setMsg(null)
    try {
      await api.post(`/sdr/profiles/${sdr.id}/reset-config`, {})
      setEmailOn(false); setLinkedinOn(false); setVapiOn(false); setHasVapi(false)
      setMsg({ type: "ok", text: "Configuration reset" })
      onUpdate()
    } catch (e: any) {
      setMsg({ type: "err", text: e.message || "Failed to reset" })
    } finally { setSaving(false) }
  }

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold flex items-center gap-2 text-sm">
            <Cpu size={16} className="text-purple-500" />
            Outreach Channels
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Enable or disable channels. Campaigns will only use enabled channels.
          </p>
        </div>
        <button onClick={resetConfig} disabled={saving}
          className="text-xs px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 flex items-center gap-1.5">
          <Trash2 size={12} /> Reset All
        </button>
      </div>

      {msg && (
        <div className={`text-xs px-3 py-2 rounded-lg ${msg.type === "ok" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" : "bg-red-500/10 text-red-400 border border-red-500/30"}`}>
          {msg.text}
        </div>
      )}

      <div className="space-y-2">
        <ChannelRow
          icon={<Mail size={16} />}
          label="Email"
          on={emailOn}
          setOn={setEmailOn}
          configured={!!sdr.has_email}
          configLabel={sdr.email_provider || "Connect in Setup"}
        />
        <ChannelRow
          icon={<Linkedin size={16} />}
          label="LinkedIn"
          on={linkedinOn}
          setOn={setLinkedinOn}
          configured={!!sdr.has_linkedin}
          configLabel={sdr.has_linkedin ? "Connected" : "Not connected"}
        />
        <ChannelRow
          icon={<Phone size={16} />}
          label="Vapi Voice Calling"
          on={vapiOn}
          setOn={(v) => { if (hasVapi || !v) setVapiOn(v); else setMsg({ type: "err", text: "Add Vapi credentials first" }) }}
          configured={hasVapi}
          configLabel={hasVapi ? `${sdr.vapi_phone || "Configured"}` : "No credentials"}
        />
      </div>

      <button onClick={saveChannels} disabled={saving}
        className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2">
        <Save size={14} /> {saving ? "Saving..." : "Save Channel Selection"}
      </button>

      {/* Vapi Config */}
      <div className="border-t border-white/10 pt-4 mt-4">
        <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Phone size={14} className="text-orange-500" />
          Vapi Credentials
        </h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-muted-foreground">Vapi API Key {hasVapi && "(leave blank to keep existing)"}</label>
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                value={vapiForm.api_key}
                onChange={(e) => setVapiForm((f) => ({ ...f, api_key: e.target.value }))}
                placeholder={hasVapi ? "••••••••" : "sk-..."}
                className="w-full px-3 py-2 pr-10 bg-white/5 border border-white/10 rounded-lg text-sm"
              />
              <button type="button" onClick={() => setShowKey(!showKey)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white">
                {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Phone Number (E.164)</label>
            <input
              value={vapiForm.phone_number}
              onChange={(e) => setVapiForm((f) => ({ ...f, phone_number: e.target.value }))}
              placeholder="+14155551234"
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Assistant ID (optional)</label>
            <input
              value={vapiForm.assistant_id}
              onChange={(e) => setVapiForm((f) => ({ ...f, assistant_id: e.target.value }))}
              placeholder="asst_..."
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Voice ID (optional)</label>
            <input
              value={vapiForm.voice_id}
              onChange={(e) => setVapiForm((f) => ({ ...f, voice_id: e.target.value }))}
              placeholder="alloy, echo, nova..."
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">First Message</label>
            <input
              value={vapiForm.first_message}
              onChange={(e) => setVapiForm((f) => ({ ...f, first_message: e.target.value }))}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm"
            />
          </div>
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={saveVapi} disabled={saving}
            className="flex-1 py-2 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2">
            <Key size={14} /> {saving ? "Saving..." : hasVapi ? "Update Vapi" : "Add Vapi"}
          </button>
          {hasVapi && (
            <button onClick={removeVapi} disabled={saving}
              className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-400 rounded-lg text-sm flex items-center gap-1.5">
              <Trash2 size={14} /> Remove
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function ChannelRow({ icon, label, on, setOn, configured, configLabel }: {
  icon: React.ReactNode; label: string; on: boolean; setOn: (v: boolean) => void; configured: boolean; configLabel: string
}) {
  return (
    <div className={`p-3 rounded-lg border flex items-center gap-3 ${on ? "bg-emerald-500/5 border-emerald-500/30" : "bg-white/5 border-white/10"}`}>
      <div className={`shrink-0 ${on ? "text-emerald-400" : "text-muted-foreground"}`}>{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">{label}</div>
        <div className={`text-[10px] ${configured ? "text-emerald-400" : "text-amber-400"}`}>
          {configured ? "✓ " : "⚠ "}{configLabel}
        </div>
      </div>
      <button
        onClick={() => setOn(!on)}
        className={`relative w-10 h-5 rounded-full transition-colors ${on ? "bg-emerald-500" : "bg-white/20"}`}
      >
        <span className={`absolute top-0.5 ${on ? "right-0.5" : "left-0.5"} w-4 h-4 bg-white rounded-full transition-all`} />
      </button>
    </div>
  )
}
