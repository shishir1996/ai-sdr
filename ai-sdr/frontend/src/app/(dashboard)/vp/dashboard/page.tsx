"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api-client"

export default function VPDashboardPage() {
  const [vp, setVp] = useState<any>(null)
  const [dashboard, setDashboard] = useState<any>(null)
  const [situation, setSituation] = useState<any>(null)
  const [decisions, setDecisions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showWizard, setShowWizard] = useState(false)
  const [form, setForm] = useState({
    name: "VP Sales AI",
    product_name: "",
    product_description: "",
    service_description: "",
    business_goals: "",
    icp_description: "",
    target_country: "",
    target_audience: "",
    sales_objectives: "",
  })

  const load = async () => {
    try {
      const vpRes = await api.get<any>("/vp/profile")
      setVp(vpRes)
      if (vpRes && !vpRes.error) {
        const [dash, sit, dec] = await Promise.all([
          api.get<any>("/vp/dashboard"),
          api.get<any>("/vp/situation"),
          api.get<any>("/vp/decisions"),
        ])
        setDashboard(dash)
        setSituation(sit)
        setDecisions(dec.decisions || [])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const createVP = async () => {
    try {
      await api.post("/vp/profile", form)
      setShowWizard(false)
      load()
    } catch (e) {
      console.error(e)
    }
  }

  const [executing, setExecuting] = useState(false)
  const [lastResult, setLastResult] = useState<any>(null)

  const runDecision = async () => {
    setExecuting(true)
    setLastResult(null)
    try {
      const dec = await api.post<any>("/vp/decide")
      setLastResult(dec)
      setDecisions((prev: any[]) => [{ action_type: dec.action, reasoning: dec.reasoning, details: { summary: dec.summary, actions: dec.actions_executed }, created_at: new Date().toISOString() }, ...prev])
      load()
    } catch (e) {
      console.error(e)
    } finally {
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!vp || vp.error === "no_vp") {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Welcome to VP Sales AI</h1>
          <p className="text-gray-400 mb-8">
            Your strategic sales director. Create a VP to oversee your entire sales operation.
          </p>
        </div>

        {!showWizard ? (
          <button onClick={() => setShowWizard(true)} className="w-full py-3 px-6 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition-colors">
            Create VP Sales AI
          </button>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-1">Name</label>
                <input className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Product Name</label>
                <input className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Target Country</label>
                <input className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={form.target_country} onChange={(e) => setForm({ ...form, target_country: e.target.value })} />
              </div>
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-1">Product / Service Description</label>
                <textarea className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm h-20" value={form.product_description} onChange={(e) => setForm({ ...form, product_description: e.target.value })} />
              </div>
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-1">Ideal Customer Profile</label>
                <textarea className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm h-20" placeholder="Describe your ideal customer..." value={form.icp_description} onChange={(e) => setForm({ ...form, icp_description: e.target.value })} />
              </div>
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-1">Business Goals</label>
                <textarea className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm h-20" value={form.business_goals} onChange={(e) => setForm({ ...form, business_goals: e.target.value })} />
              </div>
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-1">Target Audience</label>
                <input className="w-full bg-[#1a1a2e] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={form.target_audience} onChange={(e) => setForm({ ...form, target_audience: e.target.value })} />
              </div>
            </div>
            <button onClick={createVP} className="w-full py-3 px-6 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition-colors">
              Create VP Sales AI
            </button>
          </div>
        )}

        <div className="mt-8 space-y-3">
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
            <h3 className="text-white font-medium mb-1">Step 1: Create VP</h3>
            <p className="text-sm text-gray-400">Define your sales strategy, ICP, and target market.</p>
          </div>
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800 opacity-50">
            <h3 className="text-white font-medium mb-1">Step 2: Configure Sources</h3>
            <p className="text-sm text-gray-400">Enable lead discovery sources for research agents.</p>
          </div>
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800 opacity-50">
            <h3 className="text-white font-medium mb-1">Step 3: Research Leads</h3>
            <p className="text-sm text-gray-400">Create research agents to discover leads automatically.</p>
          </div>
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800 opacity-50">
            <h3 className="text-white font-medium mb-1">Step 4: Review Leads</h3>
            <p className="text-sm text-gray-400">Review discovered leads in the central CRM.</p>
          </div>
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800 opacity-50">
            <h3 className="text-white font-medium mb-1">Step 5: Create SDR</h3>
            <p className="text-sm text-gray-400">Launch SDRs to execute outreach campaigns.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">VP Sales Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">{vp.name} &middot; {vp.target_country || "No country set"}</p>
        </div>
        <button onClick={runDecision} disabled={executing} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2">
          {executing ? <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" /> : null}
          {executing ? "Executing..." : "Run Decision Engine"}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Active Agents", value: dashboard?.active_agents ?? 0, color: "text-emerald-400" },
          { label: "Leads Collected", value: dashboard?.leads_collected ?? 0, color: "text-blue-400" },
          { label: "SDRs Created", value: dashboard?.sdrs_created ?? 0, color: "text-purple-400" },
          { label: "Meetings Generated", value: dashboard?.meetings_generated ?? 0, color: "text-amber-400" },
        ].map((stat) => (
          <div key={stat.label} className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
            <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
            <div className="text-sm text-gray-400 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
          <h2 className="text-lg font-semibold text-white mb-3">Enabled Sources</h2>
          <div className="flex flex-wrap gap-2">
            {(dashboard?.sources_used ?? []).map((s: string) => (
              <span key={s} className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-xs font-medium">
                {s.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>

        <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
          <h2 className="text-lg font-semibold text-white mb-3">Situation Overview</h2>
          {situation ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-400">Total Leads</span><span className="text-white">{situation.total_leads}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Unconverted Research</span><span className="text-white">{situation.unconverted_research}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Active SDRs</span><span className="text-white">{situation.active_sdrs}/{situation.total_sdrs}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Has ICP Defined</span><span className={situation.has_icp ? "text-emerald-400" : "text-red-400"}>{situation.has_icp ? "Yes" : "No"}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Has Product Info</span><span className={situation.has_product_info ? "text-emerald-400" : "text-red-400"}>{situation.has_product_info ? "Yes" : "No"}</span></div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">Loading...</p>
          )}
        </div>
      </div>

      <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
        <h2 className="text-lg font-semibold text-white mb-3">Recent Decisions &amp; Reasoning</h2>
        {decisions.length === 0 ? (
          <p className="text-gray-500 text-sm">No decisions recorded yet. Click "Run Decision Engine" to start.</p>
        ) : (
          <div className="space-y-3">
            {decisions.slice(0, 10).map((d: any) => (
              <div key={d.id || d.created_at} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded text-xs font-medium">{d.action_type}</span>
                  <span className="text-xs text-gray-500">{d.created_at ? new Date(d.created_at).toLocaleString() : ""}</span>
                </div>
                <p className="text-sm text-gray-300">{d.reasoning}</p>
                {d.details?.summary && (
                  <p className="text-xs text-emerald-400 mt-1">{d.details.summary}</p>
                )}
                {d.details?.actions && d.details.actions.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {d.details.actions.map((a: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px]">{a}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
