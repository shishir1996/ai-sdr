"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Mail, Send, Eye, MessageCircle, AlertTriangle, MousePointerClick, RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react"

interface EmailStats {
  total: number
  sent: number
  opened: number
  replied: number
  bounced: number
  clicked: number
  open_rate: number
  reply_rate: number
  bounce_rate: number
  click_rate: number
}

interface EmailDetail {
  id: string
  to_email: string
  subject: string
  status: string
  opened_at: string | null
  replied_at: string | null
  clicked_at: string | null
  bounced_at: string | null
  sent_at: string | null
  lead_id: string
}

export default function EmailsPage() {
  const [stats, setStats] = useState<EmailStats | null>(null)
  const [emails, setEmails] = useState<EmailDetail[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const [s, e] = await Promise.all([
        api.get<EmailStats>("/analytics/email-stats"),
        api.get<EmailDetail[]>("/analytics/email-details"),
      ])
      setStats(s)
      setEmails(e)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading...</div>
  }

  if (!stats) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mail size={28} className="text-green-500" />
            <h1 className="text-2xl font-semibold text-white">Email Analytics</h1>
          </div>
          <button onClick={load} className="btn-secondary text-sm flex items-center gap-2"><RefreshCw size={14} /> Refresh</button>
        </div>
        <div className="card p-12 text-center">
          <p className="text-gray-400 text-sm">No email stats available. Send some emails first or check that the backend is running.</p>
        </div>
      </div>
    )
  }

  const s = stats

  const rateCards = [
    { label: "Open Rate", value: `${s.open_rate}%`, icon: Eye, color: "text-green-500", bg: "bg-green-500/10", trend: s.open_rate > 20 ? "up" : s.open_rate > 10 ? "neutral" : "down" },
    { label: "Reply Rate", value: `${s.reply_rate}%`, icon: MessageCircle, color: "text-amber-500", bg: "bg-amber-500/10", trend: s.reply_rate > 10 ? "up" : s.reply_rate > 5 ? "neutral" : "down" },
    { label: "Bounce Rate", value: `${s.bounce_rate}%`, icon: AlertTriangle, color: "text-red-500", bg: "bg-red-500/10", trend: s.bounce_rate < 3 ? "up" : s.bounce_rate < 8 ? "neutral" : "down" },
    { label: "Click Rate", value: `${s.click_rate}%`, icon: MousePointerClick, color: "text-blue-500", bg: "bg-blue-500/10", trend: s.click_rate > 5 ? "up" : "neutral" },
  ]

  const TrendIcon = ({ trend }: { trend: string }) => {
    if (trend === "up") return <TrendingUp size={14} className="text-green-500" />
    if (trend === "down") return <TrendingDown size={14} className="text-red-500" />
    return <Minus size={14} className="text-gray-400" />
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Mail size={28} className="text-green-500" />
          <h1 className="text-2xl font-semibold text-white">Email Analytics</h1>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2"><RefreshCw size={14} /> Refresh</button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-5 text-center"><Send size={20} className="mx-auto text-blue-500" /><p className="text-2xl font-bold mt-2 text-white">{s.sent}</p><p className="text-sm text-gray-400">Sent</p></div>
        <div className="card p-5 text-center"><Eye size={20} className="mx-auto text-green-500" /><p className="text-2xl font-bold mt-2 text-white">{s.opened}</p><p className="text-sm text-gray-400">Opened</p></div>
        <div className="card p-5 text-center"><MessageCircle size={20} className="mx-auto text-amber-500" /><p className="text-2xl font-bold mt-2 text-white">{s.replied}</p><p className="text-sm text-gray-400">Replies</p></div>
        <div className="card p-5 text-center"><AlertTriangle size={20} className="mx-auto text-red-500" /><p className="text-2xl font-bold mt-2 text-white">{s.bounced}</p><p className="text-sm text-gray-400">Bounced</p></div>
      </div>

      {/* Rate Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {rateCards.map((rc) => {
          const Icon = rc.icon
          return (
            <div key={rc.label} className="card p-4">
              <div className="flex items-center justify-between">
                <div className={`p-2 rounded-lg ${rc.bg}`}><Icon size={18} className={rc.color} /></div>
                <TrendIcon trend={rc.trend} />
              </div>
              <p className="text-xl font-bold mt-2 text-white">{rc.value}</p>
              <p className="text-xs text-gray-400">{rc.label}</p>
            </div>
          )
        })}
      </div>

      {/* Email Detail Table */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-white/10">
          <h3 className="font-medium text-white">Recent Email Activity</h3>
        </div>
        {emails.length === 0 ? (
          <p className="p-8 text-center text-sm text-gray-400">No emails sent yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/[0.03]">
                  <th className="text-left p-3 font-medium text-gray-300">To</th>
                  <th className="text-left p-3 font-medium text-gray-300">Subject</th>
                  <th className="text-center p-3 font-medium text-gray-300">Status</th>
                  <th className="text-center p-3 font-medium text-gray-300">Opened</th>
                  <th className="text-center p-3 font-medium text-gray-300">Clicked</th>
                  <th className="text-center p-3 font-medium text-gray-300">Replied</th>
                  <th className="text-center p-3 font-medium text-gray-300">Bounced</th>
                  <th className="text-right p-3 font-medium text-gray-300">Sent</th>
                </tr>
              </thead>
              <tbody>
                {emails.map((e) => (
                  <tr key={e.id} className="border-b border-white/10 hover:bg-white/[0.03] transition-colors">
                    <td className="p-3 text-gray-400 max-w-[150px] truncate">{e.to_email}</td>
                    <td className="p-3 font-medium text-white max-w-[200px] truncate">{e.subject}</td>
                    <td className="p-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${e.status === "sent" ? "bg-green-500/10 text-green-400" : "bg-white/10 text-gray-400"}`}>{e.status}</span>
                    </td>
                    <td className="p-3 text-center">{e.opened_at ? <span className="text-green-400 text-xs">{new Date(e.opened_at).toLocaleDateString()}</span> : <span className="text-gray-500">-</span>}</td>
                    <td className="p-3 text-center">{e.clicked_at ? <span className="text-blue-400 text-xs">{new Date(e.clicked_at).toLocaleDateString()}</span> : <span className="text-gray-500">-</span>}</td>
                    <td className="p-3 text-center">{e.replied_at ? <span className="text-amber-400 text-xs">{new Date(e.replied_at).toLocaleDateString()}</span> : <span className="text-gray-500">-</span>}</td>
                    <td className="p-3 text-center">{e.bounced_at ? <span className="text-red-400 text-xs">{new Date(e.bounced_at).toLocaleDateString()}</span> : <span className="text-gray-500">-</span>}</td>
                    <td className="p-3 text-right text-xs text-gray-400">{e.sent_at ? new Date(e.sent_at).toLocaleString() : <span className="text-gray-500">-</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
