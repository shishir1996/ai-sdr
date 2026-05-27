"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import Link from "next/link"
import { Target, Mail, Phone, Users, RefreshCw, CheckCircle, Clock, BarChart3, MessageCircle, Bot, ChevronRight } from "lucide-react"

interface CampaignDetail {
  id: string
  name: string
  description: string | null
  status: string
  ai_generated: boolean
  sdr_profile_id: string | null
  sdr_name: string
  created_at: string
  steps: { channel: string; step_order: number; delay_days: number }[]
  leads_count: number
  emails_sent: number
  emails_opened: number
  emails_replied: number
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<CampaignDetail[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const c = await api.get<CampaignDetail[]>("/campaigns/with-stats")
      setCampaigns(c)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  if (loading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>
  }

  const channelIcon: Record<string, any> = { email: Mail, phone: Phone, linkedin: Users }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Target size={28} className="text-purple-500" />
          <h1 className="text-2xl font-semibold">Campaigns</h1>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2"><RefreshCw size={14} /> Refresh</button>
      </div>

      {campaigns.length === 0 ? (
        <div className="card p-8 text-center text-muted-foreground">
          <p>No campaigns yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns.map((c) => {
            const sent = c.emails_sent || 0
            const openRate = sent > 0 ? Math.round((c.emails_opened || 0) / sent * 100) : 0
            const replyRate = sent > 0 ? Math.round((c.emails_replied || 0) / sent * 100) : 0

            return (
              <Link key={c.id} href={`/campaigns/${c.id}`} className="card p-5 block group hover:border-purple-500/30 transition-colors">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-lg group-hover:text-purple-400 transition-colors">{c.name}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === "active" ? "bg-green-500/10 text-green-600" : c.status === "completed" ? "bg-blue-500/10 text-blue-600" : "bg-muted text-muted-foreground"}`}>{c.status}</span>
                      {c.ai_generated && <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-600">AI Generated</span>}
                      {c.sdr_name && <span className="text-xs px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-600 flex items-center gap-1"><Bot size={10} /> {c.sdr_name}</span>}
                    </div>
                    {c.description && <p className="text-sm text-muted-foreground mt-1">{c.description}</p>}
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-5 gap-3 mb-4">
                  <div className="p-3 rounded-lg bg-muted/50 text-center">
                    <Users size={16} className="mx-auto text-blue-500" />
                    <p className="text-lg font-bold mt-1">{c.leads_count}</p>
                    <p className="text-xs text-muted-foreground">Leads</p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50 text-center">
                    <Mail size={16} className="mx-auto text-green-500" />
                    <p className="text-lg font-bold mt-1">{c.emails_sent}</p>
                    <p className="text-xs text-muted-foreground">Sent</p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50 text-center">
                    <MessageCircle size={16} className="mx-auto text-amber-500" />
                    <p className="text-lg font-bold mt-1">{c.emails_replied}</p>
                    <p className="text-xs text-muted-foreground">Replies</p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50 text-center">
                    <BarChart3 size={16} className="mx-auto text-emerald-500" />
                    <p className="text-lg font-bold mt-1">{openRate}%</p>
                    <p className="text-xs text-muted-foreground">Open Rate</p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50 text-center">
                    <CheckCircle size={16} className="mx-auto text-indigo-500" />
                    <p className="text-lg font-bold mt-1">{replyRate}%</p>
                    <p className="text-xs text-muted-foreground">Reply Rate</p>
                  </div>
                </div>

                {/* Steps */}
                {c.steps && c.steps.length > 0 && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-2 font-medium">Steps</p>
                    <div className="flex items-center gap-2">
                      {c.steps.map((step, i) => {
                        const Icon = channelIcon[step.channel] || Mail
                        return (
                          <div key={i} className="flex items-center gap-2">
                            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-muted text-xs">
                              <Icon size={14} />
                              <span className="capitalize">{step.channel}</span>
                            </div>
                            {step.delay_days > 0 && (
                              <span className="text-xs text-muted-foreground flex items-center gap-1">
                                <Clock size={12} />{step.delay_days}d
                              </span>
                            )}
                            {i < c.steps.length - 1 && <span className="text-muted-foreground">→</span>}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              <div className="flex items-center gap-1 mt-2 text-xs text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity">
                View details <ChevronRight size={12} />
              </div>
            </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
