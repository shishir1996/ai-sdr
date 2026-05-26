"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Phone, PhoneCall, PhoneOff, Clock, BarChart3, RefreshCw, Headphones } from "lucide-react"

interface CallRecord {
  id: string
  lead_id: string
  lead_name: string
  lead_company: string
  phone_number: string
  status: string
  duration_seconds: number | null
  outcome: string | null
  cost: number | null
  recording_url: string | null
  called_at: string | null
}

export default function CallsPage() {
  const [records, setRecords] = useState<CallRecord[]>([])
  const [analytics, setAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const [recordsData, analyticsData] = await Promise.all([
        api.get<{ items: CallRecord[] }>("/calls?per_page=100"),
        api.get<any>("/calls/analytics"),
      ])
      setRecords(recordsData.items || [])
      setAnalytics(analyticsData)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  if (loading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>
  }

  const a = analytics
  const outcomes: Record<string, number> = a?.outcomes || {}
  const made = records.filter((c) => c.status === "completed")

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Phone size={28} className="text-purple-500" />
          <h1 className="text-2xl font-semibold">Phone Call Analytics</h1>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {a && (<>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-5 text-center">
            <PhoneCall size={20} className="mx-auto text-blue-500" />
            <p className="text-2xl font-bold mt-2">{a.total}</p>
            <p className="text-sm text-muted-foreground">Total Calls</p>
          </div>
          <div className="card p-5 text-center">
            <PhoneCall size={20} className="mx-auto text-green-500" />
            <p className="text-2xl font-bold mt-2">{a.connected}</p>
            <p className="text-sm text-muted-foreground">Connected</p>
          </div>
          <div className="card p-5 text-center">
            <Clock size={20} className="mx-auto text-amber-500" />
            <p className="text-2xl font-bold mt-2">{a.total_duration_minutes}m</p>
            <p className="text-sm text-muted-foreground">Total Talk Time</p>
          </div>
          <div className="card p-5 text-center">
            <Headphones size={20} className="mx-auto text-purple-500" />
            <p className="text-2xl font-bold mt-2">{a.positive_outcomes}</p>
            <p className="text-sm text-muted-foreground">Positive Outcomes</p>
          </div>
        </div>

        {Object.keys(outcomes).length > 0 && (
          <div className="card p-5">
            <h3 className="font-medium mb-4">Call Outcomes</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(outcomes).map(([outcome, count]) => (
              <div key={outcome} className="p-3 rounded-lg border text-center">
                <p className="text-lg font-bold">{count}</p>
                <p className="text-xs text-muted-foreground capitalize">{outcome.replace(/_/g, " ")}</p>
              </div>
            ))}
            </div>
          </div>
        )}
      </>)}

      <div className="card overflow-hidden">
        <div className="p-4 border-b border-border">
          <h3 className="font-medium">Call History</h3>
        </div>
        {records.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">No calls yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left p-3 font-medium">Lead ID</th>
                  <th className="text-left p-3 font-medium">Phone</th>
                  <th className="text-center p-3 font-medium">Status</th>
                  <th className="text-center p-3 font-medium">Duration</th>
                  <th className="text-left p-3 font-medium">Outcome</th>
                  <th className="text-center p-3 font-medium">Called At</th>
                </tr>
              </thead>
              <tbody>
                {records.map((c) => (
                  <tr key={c.id} className="border-b border-border hover:bg-muted/50 transition-colors">
                    <td className="p-3 text-xs text-muted-foreground">{c.lead_id?.slice(0, 8) || "-"}...</td>
                    <td className="p-3 text-xs">{c.phone_number}</td>
                    <td className="p-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        c.status === "completed" ? "bg-green-500/10 text-green-600"
                        : c.status === "queued" ? "bg-blue-500/10 text-blue-600"
                        : c.status === "ringing" ? "bg-yellow-500/10 text-yellow-600"
                        : "bg-red-500/10 text-red-500"
                      }`}>{c.status}</span>
                    </td>
                    <td className="p-3 text-center text-xs text-muted-foreground">
                      {c.duration_seconds ? `${c.duration_seconds}s` : "-"}
                    </td>
                    <td className="p-3">
                      <span className="text-xs capitalize">{c.outcome?.replace(/_/g, " ") || "-"}</span>
                    </td>
                    <td className="p-3 text-center text-xs text-muted-foreground">
                      {c.called_at ? new Date(c.called_at).toLocaleString() : "-"}
                    </td>
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
