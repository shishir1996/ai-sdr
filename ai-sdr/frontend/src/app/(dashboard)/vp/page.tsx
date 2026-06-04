"use client"

import { useEffect, useState, useRef } from "react"
import { api } from "@/lib/api-client"

export default function VPPage() {
  const [vp, setVp] = useState<any>(null)
  const [dash, setDash] = useState<any>(null)
  const [missions, setMissions] = useState<any[]>([])
  const [decisions, setDecisions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [showWizard, setShowWizard] = useState(false)
  const [vpError, setVpError] = useState("")
  const [editForm, setEditForm] = useState({ product_name: "", target_country: "", target_business_types: "", icp_description: "" })
  const [showEdit, setShowEdit] = useState(false)
  const [progress, setProgress] = useState<any[]>([])
  const [progressSession, setProgressSession] = useState<string>("")
  const progressRef = useRef<any>(null)
  const [form, setForm] = useState({
    name: "VP Sales AI", product_name: "", product_description: "", service_description: "",
    business_goals: "", icp_description: "", target_country: "", target_audience: "",
    sales_objectives: "", target_business_types: "",
  })

  const load = async () => {
    try {
      const vpRes = await api.get<any>("/vp/profile")
      setVp(vpRes)
      if (vpRes && !vpRes.error) {
        const [d, m, dec] = await Promise.all([
          api.get<any>("/vp/dashboard"),
          api.get<any>("/vp/missions"),
          api.get<any>("/vp/decisions"),
        ])
        setDash(d)
        setMissions(m.missions || [])
        setDecisions(dec.decisions || [])
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (!progressSession) return
    const interval = setInterval(async () => {
      try {
        const p = await api.get<any>(`/vp/search-progress/${progressSession}`)
        if (p.progress) setProgress(p.progress)
      } catch {}
    }, 2000)
    return () => clearInterval(interval)
  }, [progressSession])

  const createVP = async () => {
    setVpError("")
    try {
      await api.post("/vp/profile", form)
      setShowWizard(false)
      load()
    } catch (e: any) { setVpError(e.message) }
  }

  const runDecision = async () => {
    setExecuting(true)
    setProgress([])
    const sid = Math.random().toString(36).slice(2)
    setProgressSession(sid)
    try {
      await api.post("/vp/decide", { progress_session: sid })
      load()
    } catch (e) { console.error(e) }
    finally { setExecuting(false); setProgressSession("") }
  }

  const toggleOutreach = async () => {
    try {
      await api.post("/vp/toggle-outreach")
      load()
    } catch (e) { console.error(e) }
  }

  const openEdit = () => {
    if (!vp) return
    setEditForm({
      product_name: vp.product_name || "", target_country: vp.target_country || "",
      target_business_types: vp.target_business_types || "", icp_description: vp.icp_description || "",
    })
    setShowEdit(true)
  }

  const saveProfile = async () => {
    try {
      await api.put("/vp/profile", editForm)
      setShowEdit(false)
      load()
    } catch (e) { console.error(e) }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">
      <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
    </div>
  }

  if (!vp || vp.error === "no_vp") {
    return (
      <div className="max-w-xl mx-auto py-12 px-4">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">Build Your AI Sales Team</h1>
          <p className="text-gray-400">Create a VP Sales AI to lead your research agents and SDRs.</p>
        </div>
        {!showWizard ? (
          <button onClick={() => setShowWizard(true)} className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium">
            Create VP Sales AI
          </button>
        ) : (
          <div className="space-y-4 bg-[#1a1a2e] p-6 rounded-lg border border-gray-800">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="text-sm text-gray-400">Product Name</label>
                <input className="w-full bg-[#0d0d1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={form.product_name} onChange={e => setForm({...form, product_name: e.target.value})} />
              </div>
              <div>
                <label className="text-sm text-gray-400">Target Country</label>
                <input className="w-full bg-[#0d0d1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={form.target_country} onChange={e => setForm({...form, target_country: e.target.value})} />
              </div>
              <div>
                <label className="text-sm text-gray-400">ICP</label>
                <input className="w-full bg-[#0d0d1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={form.icp_description} onChange={e => setForm({...form, icp_description: e.target.value})} />
              </div>
              <div className="col-span-2">
                <label className="text-sm text-gray-400">Business Types (comma separated)</label>
                <input className="w-full bg-[#0d0d1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={form.target_business_types} onChange={e => setForm({...form, target_business_types: e.target.value})} placeholder="restaurants, salons, small businesses" />
              </div>
            </div>
            {vpError && <p className="text-red-400 text-sm">{vpError}</p>}
            <button onClick={createVP} className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium">Create</button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">AI Sales Team</h1>
            {dash?.outreach_active && (
              <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-xs font-medium">Sales Team Active</span>
            )}
          </div>
          <p className="text-sm text-gray-400 mt-1">
            VP: {vp.name} &middot; {vp.product_name || "No product"} &middot; {vp.target_country || "No country"}
            <button onClick={openEdit} className="ml-2 text-xs text-emerald-500 hover:text-emerald-400 underline">Edit</button>
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={toggleOutreach} className={`px-4 py-2 rounded-lg text-sm font-medium ${dash?.outreach_active ? "bg-emerald-600 text-white" : "bg-gray-700 text-gray-300"}`}>
            {dash?.outreach_active ? "AI Sales Team ON" : "AI Sales Team OFF"}
          </button>
          <button onClick={runDecision} disabled={executing} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium">
            {executing ? "VP Thinking..." : "Run VP Decision"}
          </button>
        </div>
      </div>

      {/* Edit Profile Modal */}
      {showEdit && (
        <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-700">
          <h3 className="text-white font-medium mb-3">Edit VP Profile</h3>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="text-sm text-gray-400">Product</label>
              <input className="w-full bg-[#0d0d1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={editForm.product_name} onChange={e => setEditForm({...editForm, product_name: e.target.value})} /></div>
            <div><label className="text-sm text-gray-400">Country</label>
              <input className="w-full bg-[#0d0d1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={editForm.target_country} onChange={e => setEditForm({...editForm, target_country: e.target.value})} /></div>
            <div className="col-span-2"><label className="text-sm text-gray-400">Business Types</label>
              <input className="w-full bg-[#0d0d1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" value={editForm.target_business_types} onChange={e => setEditForm({...editForm, target_business_types: e.target.value})} /></div>
            <div className="col-span-2"><label className="text-sm text-gray-400">ICP</label>
              <textarea className="w-full bg-[#0d0d1a] border border-gray-700 rounded-lg px-3 py-2 text-white text-sm h-16" value={editForm.icp_description} onChange={e => setEditForm({...editForm, icp_description: e.target.value})} /></div>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={saveProfile} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm">Save</button>
            <button onClick={() => setShowEdit(false)} className="px-4 py-2 bg-gray-700 text-white rounded-lg text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: "CRM Leads", value: dash?.leads ?? 0, color: "text-blue-400" },
          { label: "Research Findings", value: dash?.unconverted_research ?? 0, color: "text-amber-400" },
          { label: "Research Agents", value: dash?.research_agents ?? 0, color: "text-purple-400" },
          { label: "SDRs", value: `${dash?.active_sdrs ?? 0}/${dash?.sdrs ?? 0}`, color: "text-emerald-400" },
          { label: "Meetings", value: dash?.meetings ?? 0, color: "text-rose-400" },
        ].map(s => (
          <div key={s.label} className="p-3 bg-[#1a1a2e] rounded-lg border border-gray-800">
            <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left column — Missions & Research */}
        <div className="lg:col-span-2 space-y-4">

          {/* Active Missions */}
          <div className="bg-[#1a1a2e] rounded-lg border border-gray-800 p-4">
            <h2 className="text-white font-semibold mb-3">
              Active Missions
              <span className="text-xs text-gray-500 font-normal ml-2">
                {missions.filter(m => m.status === "in_progress" || m.status === "draft").length} active
              </span>
            </h2>
            {missions.length === 0 ? (
              <p className="text-gray-500 text-sm">No missions. Click "Run VP Decision" to start.</p>
            ) : (
              <div className="space-y-2">
                {missions.slice(0, 10).map(m => (
                  <div key={m.id} className="p-3 bg-gray-800/30 rounded border border-gray-700/50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${
                          m.status === "completed" ? "bg-emerald-400" :
                          m.status === "in_progress" ? "bg-blue-400" : "bg-gray-400"
                        }`} />
                        <span className="text-sm text-white">{m.name}</span>
                      </div>
                      <div className="flex gap-2 text-xs">
                        <span className="text-gray-500">{m.tasks?.filter((t: any) => t.status === "completed").length}/{m.tasks?.length} tasks</span>
                        <span className="text-gray-600">{m.status}</span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1 truncate">{m.objective}</p>
                    {m.tasks?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {m.tasks.map((t: any) => (
                          <span key={t.id} className={`px-1.5 py-0.5 rounded text-[10px] ${
                            t.status === "completed" ? "bg-emerald-500/10 text-emerald-400" :
                            t.status === "in_progress" ? "bg-blue-500/10 text-blue-400" :
                            "bg-gray-700/50 text-gray-500"
                          }`}>{t.agent_type}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sources */}
          <div className="bg-[#1a1a2e] rounded-lg border border-gray-800 p-4">
            <h2 className="text-white font-semibold mb-3">Enabled Lead Sources</h2>
            <div className="flex flex-wrap gap-1.5">
              {(dash?.sources ?? []).map((s: string) => (
                <span key={s} className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-xs">{s.replace(/_/g, " ")}</span>
              ))}
              {(!dash?.sources || dash.sources.length === 0) && <span className="text-xs text-gray-500">No sources</span>}
            </div>
          </div>

          {/* Live Search Progress */}
          {progress.length > 0 && (
            <div className="bg-[#1a1a2e] rounded-lg border border-emerald-800/50 p-4">
              <h2 className="text-white font-semibold mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                Search Progress
              </h2>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {progress.map((p: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 text-sm py-1.5 border-b border-gray-800/50 last:border-0">
                    <span className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px] font-mono">{p.source.replace(/_/g, " ")}</span>
                    <span className="text-gray-400 flex-1 truncate">{p.query}</span>
                    <span className="text-white font-mono text-xs">{p.found} leads</span>
                  </div>
                ))}
              </div>
              <div className="mt-2 text-xs text-gray-500 text-right">
                Total: {progress.reduce((s: number, p: any) => s + p.found, 0)} leads found
              </div>
            </div>
          )}
        </div>

        {/* Right column — Decisions & SDRs */}
        <div className="space-y-4">
          {/* VP Status */}
          <div className="bg-[#1a1a2e] rounded-lg border border-gray-800 p-4">
            <h2 className="text-white font-semibold mb-3">VP Status</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-400">Product</span><span className="text-white">{vp.product_name || "—"}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Target</span><span className="text-white">{vp.target_country || "—"}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Outreach</span><span className={vp.outreach_active ? "text-emerald-400" : "text-gray-500"}>{vp.outreach_active ? "Active" : "Inactive"}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Missions</span><span className="text-white">{dash?.active_missions ?? 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">SDRs Active</span><span className="text-white">{dash?.active_sdrs ?? 0}</span></div>
            </div>
          </div>

          {/* VP Decisions */}
          <div className="bg-[#1a1a2e] rounded-lg border border-gray-800 p-4">
            <h2 className="text-white font-semibold mb-3">VP Decisions</h2>
            {decisions.length === 0 ? (
              <p className="text-gray-500 text-sm">No decisions yet.</p>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {decisions.slice(0, 15).map((d: any) => (
                  <div key={d.id || d.created_at} className="p-2 bg-gray-800/30 rounded border border-gray-700/50">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded text-[10px]">{d.action_type}</span>
                      <span className="text-[10px] text-gray-600">{d.created_at ? new Date(d.created_at).toLocaleString() : ""}</span>
                    </div>
                    <p className="text-xs text-gray-400">{d.reasoning}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
