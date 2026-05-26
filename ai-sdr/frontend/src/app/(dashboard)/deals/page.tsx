"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { BarChart3, DollarSign, CheckCircle, Calendar, CreditCard, Link as LinkIcon, RefreshCw, TrendingUp } from "lucide-react"

interface DealDetail {
  id: string
  name: string
  value: number
  source: string | null
  status: string
  closed_at: string | null
  won_at: string | null
  lead_name: string
  stage_name: string
}

interface Forecast {
  monthly_won: { month: string; count: number; value: number }[]
  pipeline: { stage: string; probability: number; count: number; value: number; weighted_value: number }[]
  total_forecast: number
}

const sourceIcons: Record<string, any> = {
  payment_link: CreditCard,
  website_purchase: LinkIcon,
  meeting_booked: Calendar,
}

export default function DealsPage() {
  const [deals, setDeals] = useState<DealDetail[]>([])
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  const load = async () => {
    setLoading(true)
    try {
      const [d, f] = await Promise.all([
        api.get<DealDetail[]>("/deals/won"),
        api.get<Forecast>("/analytics/forecast"),
      ])
      setDeals(d)
      setForecast(f)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  if (loading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 size={28} className="text-amber-500" />
          <h1 className="text-2xl font-semibold">Deals</h1>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2"><RefreshCw size={14} /> Refresh</button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-5 text-center">
          <CheckCircle size={20} className="mx-auto text-green-500" />
          <p className="text-2xl font-bold mt-2">{deals.length}</p>
          <p className="text-sm text-muted-foreground">Won Deals</p>
        </div>
        <div className="card p-5 text-center">
          <DollarSign size={20} className="mx-auto text-amber-500" />
          <p className="text-2xl font-bold mt-2">${deals.reduce((a, d) => a + d.value, 0).toLocaleString()}</p>
          <p className="text-sm text-muted-foreground">Total Revenue</p>
        </div>
        <div className="card p-5 text-center">
          <TrendingUp size={20} className="mx-auto text-indigo-500" />
          <p className="text-2xl font-bold mt-2">${(forecast?.total_forecast || 0).toLocaleString()}</p>
          <p className="text-sm text-muted-foreground">Forecast (weighted)</p>
        </div>
        <div className="card p-5 text-center">
          <CreditCard size={20} className="mx-auto text-purple-500" />
          <p className="text-2xl font-bold mt-2">{forecast?.pipeline.reduce((a, p) => a + p.count, 0) || 0}</p>
          <p className="text-sm text-muted-foreground">Open in Pipeline</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline Forecast */}
        {forecast && forecast.pipeline.length > 0 && (
          <div className="card p-5">
            <h3 className="font-medium mb-4">Pipeline Forecast</h3>
            <div className="space-y-2">
              {forecast.pipeline.map((p) => (
                <div key={p.stage} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="capitalize">{p.stage}</span>
                    <span className="text-xs text-muted-foreground">({p.count})</span>
                  </div>
                  <div className="flex gap-4 text-xs">
                    <span>${p.value.toLocaleString()}</span>
                    <span className="text-muted-foreground">{p.probability}%</span>
                    <span className="font-medium text-green-600">${p.weighted_value.toLocaleString()}</span>
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-between pt-2 border-t border-border font-medium text-sm">
                <span>Total Forecast</span>
                <span>${forecast.total_forecast.toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        {/* Monthly Breakdown */}
        {forecast && forecast.monthly_won.length > 0 && (
          <div className="card p-5">
            <h3 className="font-medium mb-4">Monthly Won Deals</h3>
            <div className="space-y-2">
              {forecast.monthly_won.map((m) => (
                <div key={m.month} className="flex items-center justify-between text-sm">
                  <span>{m.month}</span>
                  <div className="flex gap-4">
                    <span>{m.count} deals</span>
                    <span className="text-muted-foreground">${m.value.toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Won Deals Table */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-border">
          <h3 className="font-medium">Closed Won Deals</h3>
        </div>
        {deals.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-foreground">No won deals yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left p-3 font-medium">Deal Name</th>
                  <th className="text-left p-3 font-medium">Lead</th>
                  <th className="text-right p-3 font-medium">Value</th>
                  <th className="text-left p-3 font-medium">Source</th>
                  <th className="text-center p-3 font-medium">Won At</th>
                </tr>
              </thead>
              <tbody>
                {deals.map((d) => {
                  const SourceIcon = sourceIcons[d.source || ""] || DollarSign
                  return (
                    <tr key={d.id} className="border-b border-border hover:bg-muted/50 transition-colors">
                      <td className="p-3 font-medium">{d.name}</td>
                      <td className="p-3 text-muted-foreground">{d.lead_name || "-"}</td>
                      <td className="p-3 text-right font-medium">${d.value.toLocaleString()}</td>
                      <td className="p-3">
                        <div className="flex items-center gap-1.5">
                          <SourceIcon size={14} className="text-muted-foreground" />
                          <span className="text-xs capitalize">{d.source ? d.source.replace(/_/g, " ") : "manual"}</span>
                        </div>
                      </td>
                      <td className="p-3 text-center text-xs text-muted-foreground">
                        {d.won_at ? new Date(d.won_at).toLocaleDateString() : d.closed_at ? new Date(d.closed_at).toLocaleDateString() : "-"}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
