"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Phone, PhoneCall, PhoneOff, Clock, BarChart3, RefreshCw, Headphones } from "lucide-react"

interface CallDetail {
  id: string
  lead_id: string
  status: string
  duration_seconds: number | null
  outcome: string | null
  called_at: string | null
  recording_url: string | null
}

export default function CallsPage() {
  const [calls, setCalls] = useState<CallDetail[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const c = await api.get<CallDetail[]>("/analytics/call-details")
      setCalls(c)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  if (loading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>
  }

  const made = calls.filter((c) => c.status === "completed")
  const connected = made.filter((c) => c.outcome)
  const totalDuration = made.reduce((acc, c) => acc + (c.duration_seconds || 0), 0)
  const outcomes = made.reduce<Record<string, number>>((acc, c) => {
    if (c.outcome) acc[c.outcome] = (acc[c.outcome] || 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Phone size={28} className="text-purple-500" />
          <h1 className="text-2xl font-semibold">Phone Call Analytics</h1>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2"><RefreshCw size={14} /> Refresh</button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-5 text-center">
          <PhoneCall size={20} className="mx-auto text-blue-500" />
          <p className="text-2xl font-bold mt-2">{made.length}</p>
          <p className="text-sm text-muted-foreground">Calls Made</p>
        </div>
        <div className="card p-5 text-center">
          <Headphones size={20} className="mx-auto text-green-500" />
          <p className="text-2xl font-bold mt-2">{connected.length}</p>
          <p className="text-sm text-muted-foreground">Connected</p>
        </div>
        <div className="card p-5 text-center">
          <Clock size={20} className="mx-auto text-amber-500" />
          <p className="text-2xl font-bold mt-2">{Math.round(totalDuration / 60)}m {totalDuration % 60}s</p>
          <p className="text-sm text-muted-foreground">Total Talk Time</p>
        </div>
        <div className="card p-5 text-center">
          <PhoneOff size={20} className="mx-auto text-red-500" />
          <p className="text-2xl font-bold mt-2">{calls.length - made.length}</p>
          <p className="text-sm text-muted-foreground">Missed/Failed</p>
        </div>
      </div>

      {/* Outcomes */}
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

      {/* Call Log */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-border">
          <h3 className="font-medium">Call History</h3>
        </div>
        {calls.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">No calls yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left p-3 font-medium">Lead ID</th>
                  <th className="text-center p-3 font-medium">Status</th>
                  <th className="text-center p-3 font-medium">Duration</th>
                  <th className="text-left p-3 font-medium">Outcome</th>
                  <th className="text-center p-3 font-medium">Called At</th>
                </tr>
              </thead>
              <tbody>
                {calls.map((c) => (
                  <tr key={c.id} className="border-b border-border hover:bg-muted/50 transition-colors">
                    <td className="p-3 text-xs text-muted-foreground">{c.lead_id.slice(0, 8)}...</td>
                    <td className="p-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === "completed" ? "bg-green-500/10 text-green-600" : "bg-red-500/10 text-red-500"}`}>{c.status}</span>
                    </td>
                    <td className="p-3 text-center text-xs text-muted-foreground">
                      {c.duration_seconds ? `${c.duration_seconds}s` : "-"}
                    </td>
                    <td className="p-3">
                      <span className="text-xs capitalize">{c.outcome || "-"}</span>
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
