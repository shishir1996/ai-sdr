"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { api } from "@/lib/api-client"
import {
  Bot, Plus, Mail, MessageCircle, Phone, Activity, Clock,
  Users, Target, Play, Square, ChevronRight, Sparkles,
  AlertCircle, RefreshCw, Globe, Linkedin,
} from "lucide-react"

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  active: { label: "Active", color: "bg-green-500/10 text-green-500 border-green-500/30" },
  idle: { label: "Idle", color: "bg-gray-500/10 text-gray-400 border-gray-500/30" },
  paused: { label: "Paused", color: "bg-amber-500/10 text-amber-500 border-amber-500/30" },
  draft: { label: "Draft", color: "bg-blue-500/10 text-blue-500 border-blue-500/30" },
}

export default function SDRListPage() {
  const [sdrs, setSdrs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusInfo, setStatusInfo] = useState<Record<string, any>>({})
  const [performance, setPerformance] = useState<Record<string, any>>({})

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const list = await api.get<any[]>("/sdr/profiles")
      setSdrs(list)

      const statusMap: Record<string, any> = {}
      const perfMap: Record<string, any> = {}
      for (const sdr of list) {
        try {
          const s = await api.get<any>(`/sdr/status?sdr_profile_id=${sdr.id}`)
          statusMap[sdr.id] = s
        } catch {}
        try {
          const p = await api.get<any>(`/sdr/activity/performance?sdr_profile_id=${sdr.id}`)
          perfMap[sdr.id] = p
        } catch {}
      }
      setStatusInfo(statusMap)
      setPerformance(perfMap)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
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
      {/* Header */}
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

      {/* Empty State */}
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

      {/* SDR Cards Grid */}
      {sdrs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sdrs.map((sdr) => {
            const status = statusInfo[sdr.id] || {}
            const perf = performance[sdr.id] || {}
            const sdrStatus = sdr.is_active ? "active" : "draft"
            const cfg = STATUS_CONFIG[sdrStatus] || STATUS_CONFIG.draft
            const isLive = status.current_status && status.current_status !== "idle" && status.current_status !== "inactive"
            const totalLeads = (perf.leads_processed || 0)
            return (
              <Link
                key={sdr.id}
                href={`/sdr/${sdr.id}`}
                className="card p-5 group hover:border-purple-500/40 transition-all hover:shadow-lg hover:shadow-purple-500/5"
              >
                {/* Top row: name + status */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      sdr.is_active ? "bg-green-500/15" : "bg-white/5"
                    }`}>
                      <Bot size={22} className={sdr.is_active ? "text-green-500" : "text-gray-500"} />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold truncate group-hover:text-purple-400 transition-colors">
                        {sdr.name || "AI SDR"}
                      </h3>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${cfg.color}`}>
                          {cfg.label}
                        </span>
                        {isLive && (
                          <span className="flex items-center gap-1 text-[10px] text-green-500">
                            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                            {status.current_status}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.preventDefault(); toggleActivation(sdr) }}
                    className={`p-2 rounded-lg transition-colors shrink-0 ${
                      sdr.is_active
                        ? "hover:bg-red-500/10 text-red-500 hover:text-red-400"
                        : "hover:bg-green-500/10 text-green-500 hover:text-green-400"
                    }`}
                    title={sdr.is_active ? "Deactivate" : "Activate"}
                  >
                    {sdr.is_active ? <Square size={16} /> : <Play size={16} />}
                  </button>
                </div>

                {/* Connected Channels */}
                <div className="flex items-center gap-2 mb-3">
                  {sdr.has_email && (
                    <span className="text-[10px] px-2 py-1 rounded-full bg-green-500/10 text-green-500 border border-green-500/20 flex items-center gap-1">
                      <Mail size={10} /> Email
                    </span>
                  )}
                  {sdr.has_linkedin && (
                    <span className="text-[10px] px-2 py-1 rounded-full bg-cyan-500/10 text-cyan-500 border border-cyan-500/20 flex items-center gap-1">
                      <Linkedin size={10} /> LinkedIn
                    </span>
                  )}
                  {!sdr.has_email && !sdr.has_linkedin && (
                    <span className="text-[10px] px-2 py-1 rounded-full bg-gray-500/10 text-gray-500 border border-gray-500/20">
                      No channels connected
                    </span>
                  )}
                </div>

                {/* Metrics row */}
                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div className="text-center p-2 rounded-lg bg-white/5">
                    <Users size={14} className="mx-auto text-blue-500" />
                    <p className="text-xs font-bold mt-0.5">{totalLeads}</p>
                    <p className="text-[10px] text-muted-foreground">Leads</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-white/5">
                    <Mail size={14} className="mx-auto text-green-500" />
                    <p className="text-xs font-bold mt-0.5">{perf.emails_drafted || 0}</p>
                    <p className="text-[10px] text-muted-foreground">Emails</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-white/5">
                    <Target size={14} className="mx-auto text-purple-500" />
                    <p className="text-xs font-bold mt-0.5">{perf.campaigns_created || 0}</p>
                    <p className="text-[10px] text-muted-foreground">Campaigns</p>
                  </div>
                </div>

                {/* Current status + last active */}
                <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-2 border-t border-white/5">
                  <span className="flex items-center gap-1 truncate">
                    <Activity size={10} />
                    {status.current_action || "No current action"}
                  </span>
                  <span className="flex items-center gap-1 shrink-0">
                    <Clock size={10} />
                    {status.last_active_at
                      ? new Date(status.last_active_at).toLocaleDateString()
                      : "Never"}
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
