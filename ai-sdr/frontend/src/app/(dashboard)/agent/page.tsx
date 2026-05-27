"use client"

import { useState, useEffect, useCallback } from "react"
import { api } from "@/lib/api-client"
import {
  Activity, CheckCircle, XCircle, Clock, Mail, Phone, MessageCircle,
  PauseCircle, PlayCircle, StopCircle, Bot, Brain, Target, Users,
  BarChart3, Sparkles, ChevronDown, ChevronRight, AlertCircle,
  RefreshCw, Cpu, Zap, Loader, Globe, TrendingUp, MessageSquare,
  Link, Calendar, DollarSign,
} from "lucide-react"

interface ActivityItem {
  id: string
  sdr_profile_id: string | null
  lead_id: string | null
  campaign_id: string | null
  stage: string
  status: string
  summary: string
  reasoning: string
  details: Record<string, any> | null
  channel: string | null
  next_planned_action: string | null
  confidence_score: number | null
  is_expandable: boolean
  lead_name: string | null
  lead_email: string | null
  created_at: string
}

interface ReasoningLog {
  id: string
  decision_type: string
  human_readable_reasoning: string | null
  ai_confidence_score: number | null
  channel_selected: string | null
  timing_explanation: string | null
  personalization_strategy: string | null
  industry_context: string | null
  country_context: string | null
  context_summary: string | null
  created_at: string
}

interface SdrStatusInfo {
  current_status: string
  current_action: string | null
  current_lead_id: string | null
  current_campaign_id: string | null
  reasoning_summary: string | null
  next_planned_action: string | null
  heartbeat_at: string | null
  last_active_at: string | null
  sdr_name?: string
  sdr_id?: string
  leads_processed: number
  campaigns_created: number
  emails_drafted: number
  linkedin_invites_sent: number
  replies_detected: number
  meetings_booked: number
}

interface LeadStateItem {
  lead_id: string
  sdr_profile_id: string | null
  lead_name: string
  lead_email: string
  lead_company: string
  lead_source: string
  state: string
  is_paused: boolean
  contact_count: number
  channels_used: string[]
  last_contacted_at: string | null
}

interface StageSummary {
  stage: string
  count: number
  latest: string | null
}

const STAGE_LABELS: Record<string, string> = {
  leads_analyzed: "Leads Analyzed",
  icp_identified: "ICP Identified",
  campaign_strategy_created: "Campaign Strategy Created",
  outreach_sequence_planned: "Outreach Sequence Planned",
  email_drafted: "Email Drafted",
  linkedin_invite_generated: "LinkedIn Invite Generated",
  followup_scheduled: "Follow-up Scheduled",
  ai_call_planned: "AI Call Planned",
  followup_email_triggered: "Follow-up Email Triggered",
  reply_detected: "Reply Detected",
  next_action_decided: "Next Action Decided",
  campaign_optimized: "Campaign Optimized",
  lead_researched: "Lead Analyzed",
  lead_analyzed: "Lead Analyzed",
  message_sent: "Message Sent",
  call_made: "Call Made",
  meeting_booked: "Meeting Booked",
  payment_sent: "Payment Sent",
  lead_won: "Lead Won",
  lead_lost: "Lead Lost",
}

const STAGE_ICONS: Record<string, any> = {
  leads_analyzed: Users,
  icp_identified: Target,
  campaign_strategy_created: Bot,
  outreach_sequence_planned: BarChart3,
  email_drafted: Mail,
  linkedin_invite_generated: MessageCircle,
  followup_scheduled: Clock,
  ai_call_planned: Phone,
  followup_email_triggered: Mail,
  reply_detected: MessageSquare,
  next_action_decided: Brain,
  campaign_optimized: TrendingUp,
  lead_researched: Sparkles,
  lead_analyzed: Sparkles,
  message_sent: Send,
  call_made: Phone,
  meeting_booked: Calendar,
  payment_sent: DollarSign,
  lead_won: CheckCircle,
  lead_lost: XCircle,
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
  thinking: { label: "Thinking", color: "text-purple-400 bg-purple-500/10 border-purple-500/30", icon: Brain },
  researching: { label: "Researching", color: "text-blue-400 bg-blue-500/10 border-blue-500/30", icon: Sparkles },
  drafting: { label: "Drafting", color: "text-amber-400 bg-amber-500/10 border-amber-500/30", icon: Mail },
  waiting_for_response: { label: "Waiting for Response", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30", icon: Clock },
  sending_followup: { label: "Sending Follow-up", color: "text-orange-400 bg-orange-500/10 border-orange-500/30", icon: Send },
  optimizing_campaign: { label: "Optimizing Campaign", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30", icon: TrendingUp },
  idle: { label: "Idle", color: "text-gray-400 bg-gray-500/10 border-gray-500/30", icon: Activity },
  paused: { label: "Paused", color: "text-red-400 bg-red-500/10 border-red-500/30", icon: PauseCircle },
  analyzing: { label: "Analyzing", color: "text-violet-400 bg-violet-500/10 border-violet-500/30", icon: Cpu },
  planning: { label: "Planning", color: "text-indigo-400 bg-indigo-500/10 border-indigo-500/30", icon: Brain },
  personalizing: { label: "Personalizing", color: "text-pink-400 bg-pink-500/10 border-pink-500/30", icon: Sparkles },
  executing: { label: "Executing", color: "text-green-400 bg-green-500/10 border-green-500/30", icon: Zap },
}

const STAGE_ORDER = [
  "campaign_strategy_created", "leads_analyzed", "lead_researched", "lead_analyzed",
  "email_drafted", "linkedin_invite_generated", "ai_call_planned",
  "followup_scheduled", "reply_detected", "next_action_decided",
  "meeting_booked", "lead_won",
]

const CHANNEL_ICONS: Record<string, any> = {
  email: Mail, linkedin: MessageCircle, phone: Phone, meeting: Calendar,
}

function Send(props: any) { return <Zap {...props} /> }
function ChannelIcon({ channel, size }: { channel: string; size?: number }) {
  const Icon = CHANNEL_ICONS[channel]
  return Icon ? <Icon size={size ?? 16} /> : null
}

export default function AgentPage() {
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [reasoningLogs, setReasoningLogs] = useState<ReasoningLog[]>([])
  const [sdrStatus, setSdrStatus] = useState<SdrStatusInfo | SdrStatusInfo[] | null>(null)
  const [leadStates, setLeadStates] = useState<LeadStateItem[]>([])
  const [stageSummaries, setStageSummaries] = useState<StageSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<"timeline" | "reasoning" | "leads" | "stages">("timeline")
  const [expandedActivity, setExpandedActivity] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const [acts, logs, status, ls, stages] = await Promise.all([
        api.get<ActivityItem[]>("/sdr/activity/feed").catch(() => []),
        api.get<ReasoningLog[]>("/sdr/activity/reasoning?limit=10").catch(() => []),
        api.get<SdrStatusInfo[]>("/sdr/status").catch(() => []),
        api.get<LeadStateItem[]>("/sdr/leads").catch(() => []),
        api.get<StageSummary[]>("/sdr/activity/stages").catch(() => []),
      ])
      setActivities(acts)
      setReasoningLogs(logs)
      setSdrStatus(Array.isArray(status) && status.length > 0 ? status : null)
      setLeadStates(ls)
      setStageSummaries(stages)
    } catch { }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(refresh, 10000)
    return () => clearInterval(interval)
  }, [autoRefresh, refresh])

  const pauseLead = async (id: string) => { await api.post(`/sdr/leads/${id}/pause`); refresh() }
  const resumeLead = async (id: string) => { await api.post(`/sdr/leads/${id}/resume`); refresh() }
  const stopLead = async (id: string) => {
    if (!confirm("Stop processing this lead?")) return
    await api.post(`/sdr/leads/${id}/stop`); refresh()
  }

  if (loading) {
    return <div className="text-center py-20 text-muted-foreground">Loading SDR activity...</div>
  }

  const statusList: SdrStatusInfo[] = Array.isArray(sdrStatus) ? sdrStatus : sdrStatus ? [sdrStatus] : []
  const totalPerformance = statusList.reduce(
    (acc, s) => ({
      leads_processed: acc.leads_processed + (s.leads_processed || 0),
      campaigns_created: acc.campaigns_created + (s.campaigns_created || 0),
      emails_drafted: acc.emails_drafted + (s.emails_drafted || 0),
      linkedin_invites_sent: acc.linkedin_invites_sent + (s.linkedin_invites_sent || 0),
      replies_detected: acc.replies_detected + (s.replies_detected || 0),
      meetings_booked: acc.meetings_booked + (s.meetings_booked || 0),
    }),
    { leads_processed: 0, campaigns_created: 0, emails_drafted: 0, linkedin_invites_sent: 0, replies_detected: 0, meetings_booked: 0 }
  )

  const isSdrActive = statusList.some(s => s.current_status !== "idle" && s.current_status !== "inactive" && s.current_status !== "paused")

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity size={28} className="text-purple-500" />
          <h1 className="text-2xl font-semibold">Agent Activity</h1>
          {isSdrActive && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-500 border border-green-500/30">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              SDR Active
            </span>
          )}
          {!isSdrActive && statusList.length > 0 && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gray-500/10 text-gray-400 border border-gray-500/30">
              <span className="w-2 h-2 rounded-full bg-gray-500" />
              SDR Idle
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${autoRefresh ? "bg-purple-500/10 border-purple-500/30 text-purple-400" : "bg-white/5 border-white/10 text-gray-400"}`}
          >
            {autoRefresh ? "Live" : "Paused"}
          </button>
          <button onClick={refresh} className="btn-ghost text-xs flex items-center gap-1">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* SDR Live Status */}
      {statusList.map((s, i) => {
        const cfg = STATUS_CONFIG[s.current_status] || STATUS_CONFIG.idle
        const Icon = cfg.icon
        const isLive = s.heartbeat_at && (Date.now() - new Date(s.heartbeat_at).getTime()) < 120000
        return (
          <div key={i} className={`card p-5 border-l-4 ${isLive ? "border-l-green-500" : "border-l-gray-600"}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${cfg.color}`}>
                    <Icon size={16} />
                    {cfg.label}
                    {isLive && <span className="w-2 h-2 rounded-full bg-current animate-pulse" />}
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {s.sdr_name && `${s.sdr_name} — `}
                    {isLive ? "Active now" : `Last active: ${s.last_active_at ? new Date(s.last_active_at).toLocaleTimeString() : "N/A"}`}
                  </span>
                </div>
                {s.current_action && (
                  <p className="text-sm text-white/80 mb-1">
                    <span className="text-purple-400 font-medium">Now:</span> {s.current_action}
                  </p>
                )}
                {s.next_planned_action && (
                  <p className="text-xs text-muted-foreground">
                    <span className="text-cyan-400 font-medium">Next:</span> {s.next_planned_action}
                  </p>
                )}
                {s.reasoning_summary && (
                  <p className="text-xs text-muted-foreground mt-1 italic">{s.reasoning_summary}</p>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {isLive && <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />}
              </div>
            </div>
          </div>
        )
      })}

      {/* Performance Metrics */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        {[
          { label: "Leads Proc.", value: totalPerformance.leads_processed, icon: Users, color: "text-blue-500" },
          { label: "Campaigns", value: totalPerformance.campaigns_created, icon: Target, color: "text-purple-500" },
          { label: "Emails", value: totalPerformance.emails_drafted, icon: Mail, color: "text-green-500" },
          { label: "LinkedIn", value: totalPerformance.linkedin_invites_sent, icon: MessageCircle, color: "text-cyan-500" },
          { label: "Replies", value: totalPerformance.replies_detected, icon: MessageSquare, color: "text-amber-500" },
          { label: "Meetings", value: totalPerformance.meetings_booked, icon: Calendar, color: "text-emerald-500" },
        ].map((m) => (
          <div key={m.label} className="card p-3 text-center">
            <m.icon size={16} className={`mx-auto ${m.color}`} />
            <p className="text-xl font-bold mt-1">{m.value}</p>
            <p className="text-xs text-muted-foreground">{m.label}</p>
          </div>
        ))}
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2 border-b border-border overflow-x-auto">
        {[
          { key: "timeline", label: "Activity Timeline", icon: Activity },
          { key: "reasoning", label: "AI Reasoning", icon: Brain },
          { key: "leads", label: "Lead Pipeline", icon: Users },
          { key: "stages", label: "Stage Progress", icon: BarChart3 },
        ].map((tab) => {
          const TabIcon = tab.icon
          const isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${isActive ? "border-purple-500 text-purple-400" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            >
              <TabIcon size={16} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Activity Timeline Tab */}
      {activeTab === "timeline" && (
        <div className="space-y-3">
          {activities.length === 0 ? (
            <div className="card p-8 text-center text-muted-foreground">
              <Bot size={40} className="mx-auto mb-3 text-purple-500/50" />
              <p>No SDR activity yet. Configure and activate the AI SDR to see real-time execution.</p>
            </div>
          ) : (
            activities.map((act, i) => {
              const StageIcon = STAGE_ICONS[act.stage] || Activity
              const isExpanded = expandedActivity === act.id
              const isLatest = i === 0
              return (
                <div
                  key={act.id}
                  className={`card p-4 transition-all ${isLatest ? "border-purple-500/40" : ""} ${isExpanded ? "ring-1 ring-purple-500/30" : ""}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex flex-col items-center">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center ${act.status === "completed" ? "bg-green-500/10" : act.status === "skipped" ? "bg-gray-500/10" : "bg-amber-500/10"}`}>
                        <StageIcon size={16} className={act.status === "completed" ? "text-green-500" : act.status === "skipped" ? "text-gray-400" : "text-amber-500"} />
                      </div>
                      {i < activities.length - 1 && <div className="w-px h-full min-h-[2rem] bg-white/5 mt-1" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">{STAGE_LABELS[act.stage] || act.stage.replace(/_/g, " ")}</span>
                        {act.confidence_score && (
                          <span className={`text-xs px-1.5 py-0.5 rounded ${act.confidence_score > 80 ? "bg-green-500/10 text-green-400" : "bg-amber-500/10 text-amber-400"}`}>
                            {act.confidence_score}% confidence
                          </span>
                        )}
                        <span className="text-xs text-muted-foreground ml-auto">
                          {new Date(act.created_at).toLocaleString()}
                        </span>
                      </div>
                      {act.summary && <p className="text-sm text-white/90 mt-1">{act.summary}</p>}
                      {act.reasoning && (
                        <p className="text-xs text-muted-foreground mt-1 italic">"{act.reasoning}"</p>
                      )}
                      <div className="flex items-center gap-3 mt-2 flex-wrap">
                        {act.lead_name && (
                          <span className="text-xs text-blue-400 flex items-center gap-1">
                            <Users size={12} /> {act.lead_name}
                          </span>
                        )}
                        {act.channel && (
                          <span className="text-xs text-cyan-400 flex items-center gap-1 capitalize">
                            <ChannelIcon channel={act.channel ?? ""} size={12} />
                            {act.channel}
                          </span>
                        )}
                        {act.next_planned_action && (
                          <span className="text-xs text-emerald-400 flex items-center gap-1">
                            <Zap size={12} /> {act.next_planned_action}
                          </span>
                        )}
                      </div>
                      {act.is_expandable && (
                        <button
                          onClick={() => setExpandedActivity(isExpanded ? null : act.id)}
                          className="flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 mt-2"
                        >
                          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          {isExpanded ? "Hide details" : "Show AI reasoning & details"}
                        </button>
                      )}
                      {isExpanded && act.details && (
                        <div className="mt-3 p-3 rounded-lg bg-white/5 border border-white/10 space-y-2">
                          {Object.entries(act.details).map(([key, val]) => (
                            <div key={key}>
                              <span className="text-xs font-medium text-purple-400 capitalize">{key.replace(/_/g, " ")}:</span>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {typeof val === "string" ? val : JSON.stringify(val)}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}

      {/* AI Reasoning Tab */}
      {activeTab === "reasoning" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <Brain size={16} className="text-purple-500" />
            <p className="text-sm text-muted-foreground">AI decision logs showing why the SDR chose each action</p>
          </div>
          {reasoningLogs.length === 0 ? (
            <div className="card p-8 text-center text-muted-foreground">
              <Brain size={40} className="mx-auto mb-3 text-purple-500/50" />
              <p>No AI reasoning logs yet. These appear as the SDR makes decisions.</p>
            </div>
          ) : (
            reasoningLogs.map((log, i) => (
              <div key={log.id || i} className="card p-4">
                <div className="flex items-start gap-3">
                  <Brain size={18} className="text-purple-500 mt-0.5 shrink-0" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium capitalize">{log.decision_type.replace(/_/g, " ")}</span>
                      {log.ai_confidence_score && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">
                          {log.ai_confidence_score}% confidence
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground ml-auto">
                        {new Date(log.created_at).toLocaleString()}
                      </span>
                    </div>
                    {log.human_readable_reasoning && (
                      <p className="text-sm text-white/90 mb-2">"{log.human_readable_reasoning}"</p>
                    )}
                    <div className="flex flex-wrap gap-3 text-xs">
                      {log.channel_selected && (
                        <span className="text-cyan-400">Channel: {log.channel_selected}</span>
                      )}
                      {log.timing_explanation && (
                        <span className="text-amber-400">Timing: {log.timing_explanation}</span>
                      )}
                      {log.personalization_strategy && (
                        <span className="text-emerald-400">Strategy: {log.personalization_strategy}</span>
                      )}
                      {log.industry_context && (
                        <span className="text-blue-400">Industry: {log.industry_context}</span>
                      )}
                      {log.country_context && (
                        <span className="text-indigo-400">Country: {log.country_context}</span>
                      )}
                    </div>
                    {log.context_summary && (
                      <p className="text-xs text-muted-foreground mt-2">{log.context_summary}</p>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Lead Pipeline Tab */}
      {activeTab === "leads" && (
        <div className="card p-5">
          {leadStates.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No leads in the pipeline. Import leads or enable Apollo auto-discovery.
            </p>
          ) : (
            <div className="space-y-2">
              {leadStates.map((ls) => (
                <div key={ls.lead_id} className="flex items-center justify-between p-3 rounded-lg border bg-white/5">
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
                      {ls.channels_used.length > 0 && <span>via {ls.channels_used.join(", ")}</span>}
                      {ls.lead_company && <span>at {ls.lead_company}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {ls.is_paused ? (
                      <button onClick={() => resumeLead(ls.lead_id)} className="p-2 rounded-lg hover:bg-green-500/10 text-green-600" title="Resume">
                        <PlayCircle size={18} />
                      </button>
                    ) : ls.state !== "archived" && ls.state !== "closed_won" && ls.state !== "closed_lost" ? (
                      <button onClick={() => pauseLead(ls.lead_id)} className="p-2 rounded-lg hover:bg-yellow-500/10 text-yellow-600" title="Pause">
                        <PauseCircle size={18} />
                      </button>
                    ) : null}
                    {ls.state !== "archived" && ls.state !== "closed_won" && ls.state !== "closed_lost" && (
                      <button onClick={() => stopLead(ls.lead_id)} className="p-2 rounded-lg hover:bg-red-500/10 text-red-500" title="Stop">
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

      {/* Stage Progress Tab */}
      {activeTab === "stages" && (
        <div className="card p-5">
          <p className="text-sm text-muted-foreground mb-4">Activity stages completed by the SDR</p>
          {stageSummaries.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No stages completed yet.</p>
          ) : (
            <div className="space-y-3">
              {STAGE_ORDER.filter(s => stageSummaries.find(ss => ss.stage === s)).map((stage) => {
                const ss = stageSummaries.find(s => s.stage === stage)!
                const StageIcon = STAGE_ICONS[stage] || Activity
                const maxCount = Math.max(...stageSummaries.map(s => s.count), 1)
                return (
                  <div key={stage} className="flex items-center gap-3">
                    <StageIcon size={16} className="text-purple-500 shrink-0" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm">{STAGE_LABELS[stage] || stage.replace(/_/g, " ")}</span>
                        <span className="text-xs text-muted-foreground">{ss.count}x</span>
                      </div>
                      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-purple-500 to-violet-500 transition-all"
                          style={{ width: `${(ss.count / maxCount) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

