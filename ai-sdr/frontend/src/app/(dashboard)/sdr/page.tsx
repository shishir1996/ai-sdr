"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { api } from "@/lib/api-client"
import {
  Bot, Plus, Mail, Activity, Clock,
  Users, Target, Play, Square,
  AlertCircle, RefreshCw, Linkedin,
  Phone, Calendar, ChevronRight,
} from "lucide-react"
import SDRStatusBadge, { type SDRRunState } from "@/components/ui/SDRStatusBadge"
import SDRNotificationPanel, { useSDRNotifications } from "@/components/ui/SDRNotification"

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

function toBadgeState(s: string | undefined): SDRRunState {
  if (!s || s === "idle" || s === "inactive") return "idle"
  if (s === "paused") return "paused"
  if (s === "error") return "error"
  return "running"
}

function getActiveChannel(sdr: any): { label: string; icon: any; color: string } | null {
  if (sdr.has_email) return { label: "Email", icon: Mail, color: "text-green-500" }
  if (sdr.has_linkedin) return { label: "LinkedIn", icon: Linkedin, color: "text-cyan-500" }
  return null
}

export default function SDRListPage() {
  const [sdrs, setSdrs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusInfo, setStatusInfo] = useState<Record<string, any>>({})
  const [performance, setPerformance] = useState<Record<string, any>>({})
  const [campaigns, setCampaigns] = useState<Record<string, any[]>>({})
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())
  const mounted = useRef(true)

  const rawNotifications = useSDRNotifications(sdrs, statusInfo)
  const notifications = rawNotifications.filter(n => !dismissed.has(n.id))

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const list = await api.get<any[]>("/sdr/profiles")
      if (!mounted.current) return
      setSdrs(list)

      const statusMap: Record<string, any> = {}
      const perfMap: Record<string, any> = {}
      const campMap: Record<string, any[]> = {}
      for (const sdr of list) {
        try {
          const s = await api.get<any>(`/sdr/status?sdr_profile_id=${sdr.id}`)
          statusMap[sdr.id] = s
        } catch {}
        try {
          const p = await api.get<any>(`/sdr/activity/performance?sdr_profile_id=${sdr.id}`)
          perfMap[sdr.id] = p
        } catch {}
        try {
          const c = await api.get<any[]>(`/campaigns?sdr_profile_id=${sdr.id}`)
          campMap[sdr.id] = c
        } catch {}
      }
      if (mounted.current) {
        setStatusInfo(statusMap)
        setPerformance(perfMap)
        setCampaigns(campMap)
      }
    } catch (e) { console.error(e) }
    finally { if (mounted.current) setLoading(false) }
  }

  const toggleActivation = async (sdr: any) => {
    try {
      if (sdr.is_active) {
        await api.post(`/sdr/profiles/${sdr.id}/deactivate`)
      } else {
        await api.post(`/sdr/profiles/${sdr.id}/activate`)
      }
      await load()
    } catch (e) { console.error(e) }
  }

  const deleteSDR = async (sdr: any) => {
    if (!confirm(`Remove SDR "${sdr.name}"? It will be deactivated and hidden.`)) return
    try {
      await api.delete(`/vp/sdrs/${sdr.id}`)
      await load()
    } catch (e) { console.error(e) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Bot size={40} className="mx-auto mb-3 text-purple-500/50 animate-pulse" />
          <p className="text-muted-foreground">Loading SDRs...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <SDRNotificationPanel
        notifications={notifications}
        onDismiss={(id) => setDismissed(prev => new Set(prev).add(id))}
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bot size={28} className="text-purple-500" />
          <div>
            <h1 className="text-2xl font-semibold">AI SDRs</h1>
            <p className="text-sm text-muted-foreground">Manage your AI sales development representatives</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="btn-ghost text-xs flex items-center gap-1">
            <RefreshCw size={14} /> Refresh
          </button>
          <Link href="/sdr/setup" className="btn-primary text-sm flex items-center gap-2">
            <Plus size={16} />
            Create New SDR
          </Link>
        </div>
      </div>

      {notifications.length > 0 && (
        <div className="flex items-center gap-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
          <AlertCircle size={16} className="text-amber-400 shrink-0" />
          <p className="text-sm text-amber-300">
            {notifications.length} issue{notifications.length > 1 ? "s" : ""} need{notifications.length === 1 ? "s" : ""} your attention
          </p>
          <button
            onClick={() => setDismissed(new Set())}
            className="ml-auto text-xs text-gray-500 hover:text-gray-300 underline underline-offset-2"
          >
            Dismiss all
          </button>
        </div>
      )}

      {sdrs.length === 0 && (
        <div className="card p-12 text-center">
          <Bot size={60} className="mx-auto mb-4 text-purple-500/40" />
          <h2 className="text-xl font-semibold mb-2">No AI SDRs Yet</h2>
          <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
            Create your first AI SDR to automate lead outreach, follow-ups, and meeting booking.
          </p>
          <Link href="/sdr/setup" className="btn-primary inline-flex items-center gap-2">
            <Plus size={18} />
            Create New SDR
          </Link>
        </div>
      )}

      {sdrs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sdrs.map((sdr) => {
            const status = statusInfo[sdr.id] || {}
            const perf = performance[sdr.id] || {}
            const sdrCamps = campaigns[sdr.id] || []
            const sdrStatus = sdr.is_active ? "active" : "draft"
            const state = toBadgeState(status.current_status)
            const isLive = state === "running"
            const totalLeads = (perf.leads_processed || 0) + (status.leads_processed || 0)
            const meetings = perf.meetings_booked || 0
            const channel = getActiveChannel(sdr)
            const campaignName = sdrCamps.length > 0 ? sdrCamps[0].name || sdrCamps[0].campaign_name : null

            return (
              <Link
                key={sdr.id}
                href={`/sdr/${sdr.id}`}
                className="card p-4 group hover:border-purple-500/40 transition-all hover:shadow-lg hover:shadow-purple-500/5"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      isLive ? "bg-emerald-500/15" : sdr.is_active ? "bg-blue-500/10" : "bg-white/5"
                    }`}>
                      <Bot size={22} className={
                        isLive ? "text-emerald-500" : sdr.is_active ? "text-blue-500" : "text-gray-500"
                      } />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold truncate group-hover:text-purple-400 transition-colors">
                        {sdr.name || "AI SDR"}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <SDRStatusBadge state={state} label={status.current_status || (sdr.is_active ? "Active" : "Draft")} />
                        {campaignName && (
                          <span className="text-[10px] text-muted-foreground truncate max-w-[100px]">
                            {campaignName}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={(e) => { e.preventDefault(); toggleActivation(sdr) }}
                      className={`p-2 rounded-lg transition-colors ${
                        sdr.is_active
                          ? "hover:bg-red-500/10 text-red-500 hover:text-red-400"
                          : "hover:bg-green-500/10 text-green-500 hover:text-green-400"
                      }`}
                      title={sdr.is_active ? "Deactivate" : "Activate"}
                    >
                      {sdr.is_active ? <Square size={15} /> : <Play size={15} />}
                    </button>
                    <button
                      onClick={(e) => { e.preventDefault(); deleteSDR(sdr) }}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-red-500/50 hover:text-red-400 transition-colors"
                      title="Remove SDR"
                    >
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2 mb-3">
                  {channel && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${channel.color} bg-white/5 border border-white/10 flex items-center gap-1`}>
                      <channel.icon size={10} /> {channel.label}
                    </span>
                  )}
                  {!channel && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full text-red-500 bg-red-500/10 border border-red-500/20 flex items-center gap-1">
                      <AlertCircle size={10} /> No channel
                    </span>
                  )}
                  {meetings > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-1">
                      <Calendar size={10} /> {meetings} meeting{meetings !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div className="text-center p-2 rounded-lg bg-white/5">
                    <Users size={13} className="mx-auto text-blue-500" />
                    <p className="text-xs font-bold mt-0.5">{totalLeads}</p>
                    <p className="text-[9px] text-muted-foreground">Leads</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-white/5">
                    <Mail size={13} className="mx-auto text-green-500" />
                    <p className="text-xs font-bold mt-0.5">{perf.emails_drafted || status.emails_drafted || 0}</p>
                    <p className="text-[9px] text-muted-foreground">Emails</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-white/5">
                    <Target size={13} className="mx-auto text-purple-500" />
                    <p className="text-xs font-bold mt-0.5">{perf.campaigns_created || 0}</p>
                    <p className="text-[9px] text-muted-foreground">Campaigns</p>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-2 border-t border-white/5">
                  <span className="flex items-center gap-1 truncate">
                    <Activity size={10} />
                    {status.current_action || "Idle"}
                  </span>
                  <span className="flex items-center gap-1 shrink-0">
                    <Clock size={10} />
                    {fmtDate(status.last_active_at)}
                  </span>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
