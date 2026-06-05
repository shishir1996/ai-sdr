"use client"

import { useEffect, useState, useRef } from "react"
import { api } from "@/lib/api-client"
import {
  Brain, Target, Users, Mail, Globe, RefreshCw, Play, AlertTriangle,
  Search, BarChart3, MessageCircle, Power, X, ChevronRight, Activity,
  Database, Upload, Globe2, Phone, Linkedin, Check, ArrowRight,
} from "lucide-react"

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
  const [resetting, setResetting] = useState(false)
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [actionError, setActionError] = useState("")
  const [form, setForm] = useState({
    name: "VP Sales AI", product_name: "", product_description: "", service_description: "",
    business_goals: "", icp_description: "", target_country: "", target_audience: "",
    sales_objectives: "", target_business_types: "",
  })
  const [wizardStep, setWizardStep] = useState(1)
  const [dataSource, setDataSource] = useState<"manual" | "web_scraping" | "third_party">("web_scraping")
  const [searchQueries, setSearchQueries] = useState("100 salons in India\nrestaurants in Mumbai\nsmall businesses in Bangalore")
  const [platforms, setPlatforms] = useState<string[]>(["apollo"])

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
      const payload = {
        ...form,
        data_source: dataSource,
        data_source_config: dataSource === "web_scraping"
          ? { search_queries: searchQueries }
          : dataSource === "third_party"
          ? { platforms }
          : {},
      }
      await api.post("/vp/profile", payload)
      setShowWizard(false)
      setWizardStep(1)
      load()
    } catch (e: any) { setVpError(e.message) }
  }

  const runDecision = async (force = false) => {
    setExecuting(true)
    setActionError("")
    setProgress([])
    const sid = Math.random().toString(36).slice(2)
    setProgressSession(sid)
    try {
      await api.post("/vp/decide", { progress_session: sid, force_research: force })
      load()
    } catch (e: any) { setActionError(e.message || "VP decision failed") }
    finally { setExecuting(false); setProgressSession("") }
  }

  const resetAll = async () => {
    setResetting(true)
    setActionError("")
    try {
      await api.post("/vp/reset", {})
      setShowResetConfirm(false)
      load()
    } catch (e: any) { setActionError(e.message || "Reset failed") }
    finally { setResetting(false) }
  }

  const toggleOutreach = async () => {
    setActionError("")
    try {
      await api.post("/vp/toggle-outreach")
      load()
    } catch (e: any) { setActionError(e.message || "Toggle failed") }
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
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!vp || vp.error === "no_vp") {
    return (
      <div className="max-w-xl mx-auto py-12 px-4">
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-blue-500/10 border border-emerald-500/20 mb-4">
            <Brain size={32} className="text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">AI Sales Team</h1>
          <p className="text-gray-400">Create a VP of Sales to autonomously research, find leads, and run outbound campaigns.</p>
        </div>
        {!showWizard ? (
          <button onClick={() => setShowWizard(true)}
            className="w-full py-3 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white rounded-xl font-medium transition-all">
            Create VP Sales AI
          </button>
        ) : (
          <div className="space-y-5 bg-gray-800/40 p-6 rounded-xl border border-gray-700/50 backdrop-blur">
            {/* Step indicator */}
            <div className="flex items-center gap-2 text-xs">
              <span className={`px-2.5 py-1 rounded-full ${wizardStep === 1 ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-gray-700/50 text-gray-500"}`}>1. Product &amp; Target</span>
              <ArrowRight size={12} className="text-gray-600" />
              <span className={`px-2.5 py-1 rounded-full ${wizardStep === 2 ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-gray-700/50 text-gray-500"}`}>2. Data Source</span>
            </div>

            {wizardStep === 1 && (
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Product Name</label>
                  <input className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500" value={form.product_name} onChange={e => setForm({...form, product_name: e.target.value})} placeholder="e.g. SaaS Platform" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Product Description</label>
                  <textarea className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm h-16 focus:outline-none focus:border-emerald-500" value={form.product_description} onChange={e => setForm({...form, product_description: e.target.value})} placeholder="What does your product do?" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Target Country</label>
                    <input className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500" value={form.target_country} onChange={e => setForm({...form, target_country: e.target.value})} placeholder="e.g. India" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">ICP Description</label>
                    <input className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500" value={form.icp_description} onChange={e => setForm({...form, icp_description: e.target.value})} placeholder="e.g. small business owners" />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Target Business Types</label>
                  <input className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500" value={form.target_business_types} onChange={e => setForm({...form, target_business_types: e.target.value})} placeholder="restaurants, salons, clinics (comma separated)" />
                </div>
                <div className="flex gap-3 pt-2">
                  <button onClick={() => setWizardStep(2)} className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2">
                    Next: Choose Data Source <ArrowRight size={14} />
                  </button>
                  <button onClick={() => setShowWizard(false)} className="py-2.5 px-4 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm">Cancel</button>
                </div>
              </div>
            )}

            {wizardStep === 2 && (
              <div className="space-y-4">
                <p className="text-sm text-gray-300">How should the VP obtain leads?</p>

                <div className="space-y-2">
                  {[
                    { id: "manual", icon: Upload, label: "Manual Upload", desc: "You'll upload leads via CSV. VP waits for you.", color: "emerald" },
                    { id: "web_scraping", icon: Globe2, label: "Web Scraping", desc: "VP creates scraping agents (Google, Bing, directories).", color: "blue" },
                    { id: "third_party", icon: Database, label: "Third-Party APIs", desc: "VP fetches from Apollo, Lusha, ZoomInfo.", color: "purple" },
                  ].map(opt => {
                    const Icon = opt.icon
                    const selected = dataSource === opt.id
                    return (
                      <button key={opt.id} onClick={() => setDataSource(opt.id as any)}
                        className={`w-full text-left p-4 rounded-xl border transition-all flex items-center gap-3 ${
                          selected
                            ? "bg-emerald-500/10 border-emerald-500/40"
                            : "bg-gray-900/40 border-gray-700/50 hover:border-gray-600"
                        }`}>
                        <div className={`p-2 rounded-lg ${selected ? "bg-emerald-500/20" : "bg-gray-800"}`}>
                          <Icon size={18} className={selected ? "text-emerald-400" : "text-gray-400"} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={`text-sm font-medium ${selected ? "text-emerald-300" : "text-white"}`}>{opt.label}</div>
                          <div className="text-xs text-gray-500 mt-0.5">{opt.desc}</div>
                        </div>
                        {selected && <Check size={16} className="text-emerald-400 shrink-0" />}
                      </button>
                    )
                  })}
                </div>

                {dataSource === "web_scraping" && (
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Search Queries (one per line)</label>
                    <textarea className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs h-24 focus:outline-none focus:border-emerald-500" value={searchQueries} onChange={e => setSearchQueries(e.target.value)} />
                  </div>
                )}

                {dataSource === "third_party" && (
                  <div>
                    <label className="text-xs text-gray-400 block mb-2">Platforms</label>
                    <div className="grid grid-cols-2 gap-2">
                      {["apollo", "lusha", "zoominfo", "rocketreach"].map(p => {
                        const selected = platforms.includes(p)
                        return (
                          <button key={p} onClick={() => setPlatforms(selected ? platforms.filter(x => x !== p) : [...platforms, p])}
                            className={`px-3 py-2 rounded-lg text-sm capitalize border transition-all ${
                              selected ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300" : "bg-gray-900/40 border-gray-700/50 text-gray-400 hover:border-gray-600"
                            }`}>
                            {selected && "✓ "}{p}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}

                {dataSource === "manual" && (
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-xs text-blue-300">
                    After creating the VP, go to <strong>Leads → Import CSV</strong> to upload your leads file. Then click "Mark Upload Done" on the VP page to continue.
                  </div>
                )}

                {vpError && <p className="text-red-400 text-sm">{vpError}</p>}
                <div className="flex gap-3 pt-2">
                  <button onClick={() => setWizardStep(1)} className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm">Back</button>
                  <button onClick={createVP} className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2">
                    <Check size={14} /> Create VP
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  const metrics = [
    { label: "CRM Leads", value: dash?.leads ?? 0, icon: Users, color: "from-blue-500 to-blue-600" },
    { label: "Research Findings", value: dash?.unconverted_research ?? 0, icon: Search, color: "from-amber-500 to-amber-600" },
    { label: "Research Agents", value: dash?.research_agents ?? 0, icon: Brain, color: "from-purple-500 to-purple-600" },
    { label: "Active SDRs", value: `${dash?.active_sdrs ?? 0}`, icon: MessageCircle, color: "from-emerald-500 to-emerald-600" },
    { label: "Meetings", value: dash?.meetings ?? 0, icon: Target, color: "from-rose-500 to-rose-600" },
    { label: "Active Missions", value: dash?.active_missions ?? 0, icon: Activity, color: "from-cyan-500 to-cyan-600" },
  ]

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-500/10 to-blue-500/10 border border-emerald-500/20">
            <Brain size={22} className="text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-white">AI Sales Team</h1>
              {dash?.outreach_active && (
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-medium border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                  Active
                </span>
              )}
            </div>
            <p className="text-sm text-gray-400 mt-0.5">
              {vp.product_name || "No product"} &middot; {vp.target_country || "No target"}
              <button onClick={openEdit} className="ml-2 text-xs text-emerald-500 hover:text-emerald-400 underline">Edit Profile</button>
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={toggleOutreach}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              dash?.outreach_active
                ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/30"
                : "bg-gray-700/50 text-gray-400 border border-gray-600/30 hover:bg-gray-700"
            }`}>
            <Power size={14} />
            {dash?.outreach_active ? "Sales Team ON" : "Sales Team OFF"}
          </button>
          <button onClick={() => runDecision(false)} disabled={executing}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-all flex items-center gap-2">
            <Play size={14} />
            {executing ? "Running..." : "Run Decision"}
          </button>
          <button onClick={() => runDecision(true)} disabled={executing}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-all flex items-center gap-2">
            <Search size={14} />
            {executing ? "Searching..." : "Force Research"}
          </button>
          <button onClick={() => setShowResetConfirm(true)} disabled={resetting}
            className="px-3 py-2 bg-red-700/50 hover:bg-red-600/70 disabled:opacity-50 text-red-300 rounded-lg text-xs font-medium transition-all border border-red-700/30">
            {resetting ? "Resetting..." : "Reset All"}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {actionError && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
          <AlertTriangle size={14} className="shrink-0" />
          <span className="flex-1">{actionError}</span>
          <button onClick={() => setActionError("")} className="text-red-400 hover:text-red-300"><X size={14} /></button>
        </div>
      )}

      {/* Manual Mode Banner */}
      {vp.data_source === "manual" && !vp.manual_upload_done && (
        <div className="flex items-center gap-3 px-4 py-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <Upload size={16} className="text-blue-400 shrink-0" />
          <div className="flex-1">
            <div className="text-sm text-blue-300 font-medium">Manual Mode: Waiting for upload</div>
            <div className="text-xs text-blue-400/70 mt-0.5">Go to <strong>Leads → Import CSV</strong> to upload your leads. Then click "Mark Upload Done" below.</div>
          </div>
          <button onClick={async () => { try { await api.post("/vp/mark-manual-upload-done", {}); load() } catch (e: any) { setActionError(e.message) } }}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition-all">
            Mark Upload Done
          </button>
        </div>
      )}

      {/* Data Source Display */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span>Data Source:</span>
        <span className={`px-2 py-0.5 rounded-full ${
          vp.data_source === "manual" ? "bg-amber-500/10 text-amber-400 border border-amber-500/30" :
          vp.data_source === "third_party" ? "bg-purple-500/10 text-purple-400 border border-purple-500/30" :
          "bg-blue-500/10 text-blue-400 border border-blue-500/30"
        }`}>
          {vp.data_source === "manual" ? "Manual Upload" : vp.data_source === "third_party" ? "Third-Party APIs" : "Web Scraping"}
        </span>
        {vp.data_source === "third_party" && vp.data_source_config?.platforms && (
          <span className="text-gray-600">· {vp.data_source_config.platforms.join(", ")}</span>
        )}
      </div>

      {/* Profile Edit Modal */}
      {showEdit && (
        <div className="bg-gray-800/40 p-5 rounded-xl border border-gray-700/50">
          <h3 className="text-white font-medium mb-4">Edit VP Profile</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Product Name</label>
              <input className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                value={editForm.product_name} onChange={e => setEditForm({...editForm, product_name: e.target.value})} />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Target Country</label>
              <input className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                value={editForm.target_country} onChange={e => setEditForm({...editForm, target_country: e.target.value})} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-400 block mb-1">Business Types</label>
              <input className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                value={editForm.target_business_types} onChange={e => setEditForm({...editForm, target_business_types: e.target.value})} />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-400 block mb-1">ICP</label>
              <textarea className="w-full bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm h-16 focus:outline-none focus:border-emerald-500"
                value={editForm.icp_description} onChange={e => setEditForm({...editForm, icp_description: e.target.value})} />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={saveProfile} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm transition-all">Save</button>
            <button onClick={() => setShowEdit(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition-all">Cancel</button>
          </div>
        </div>
      )}

      {/* Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {metrics.map(m => {
          const Icon = m.icon
          return (
            <div key={m.label} className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-4 hover:border-gray-600/50 transition-all">
              <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-lg bg-gradient-to-br ${m.color} bg-opacity-20`}>
                  <Icon size={14} className="text-white" />
                </div>
                <div className={`text-2xl font-bold text-white tabular-nums`}>{m.value}</div>
              </div>
              <div className="text-[11px] text-gray-500 uppercase tracking-wider">{m.label}</div>
            </div>
          )
        })}
      </div>

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowResetConfirm(false)}>
          <div className="bg-gray-800 p-6 rounded-xl border border-red-800/50 max-w-sm mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-red-500/10">
                <AlertTriangle size={18} className="text-red-400" />
              </div>
              <h3 className="text-white font-semibold">Reset All Data?</h3>
            </div>
            <p className="text-gray-400 text-sm mb-5">
              This permanently deletes <strong className="text-white">all leads, SDRs, missions, campaigns, and research</strong> for this organization. This cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowResetConfirm(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition-all">Cancel</button>
              <button onClick={resetAll} disabled={resetting} className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white rounded-lg text-sm transition-all">
                {resetting ? "Resetting..." : "Yes, Reset Everything"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left column — Missions & Research */}
        <div className="lg:col-span-2 space-y-4">

          {/* Active Missions */}
          <div className="bg-gray-800/20 rounded-xl border border-gray-700/50 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-semibold flex items-center gap-2">
                <Target size={16} className="text-emerald-400" />
                Active Missions
              </h2>
              <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
                {missions.filter(m => m.status === "in_progress" || m.status === "draft").length} active
              </span>
            </div>
            {missions.length === 0 ? (
              <div className="text-center py-8">
                <Target size={32} className="mx-auto text-gray-600 mb-2" />
                <p className="text-gray-500 text-sm">No missions yet</p>
                <p className="text-gray-600 text-xs mt-1">Click &quot;Run Decision&quot; to start</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {missions.slice(0, 15).map(m => (
                  <div key={m.id} className="p-3 bg-gray-800/40 rounded-lg border border-gray-700/30 hover:border-gray-600/50 transition-all">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className={`w-2 h-2 rounded-full shrink-0 ${
                          m.status === "completed" ? "bg-emerald-400" :
                          m.status === "in_progress" ? "bg-blue-400 animate-pulse" : "bg-gray-500"
                        }`} />
                        <span className="text-sm text-white truncate">{m.name}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs shrink-0 ml-2">
                        <span className="text-gray-500">{m.tasks?.filter((t: any) => t.status === "completed").length || 0}/{m.tasks?.length || 0} tasks</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                          m.status === "completed" ? "bg-emerald-500/10 text-emerald-400" :
                          m.status === "in_progress" ? "bg-blue-500/10 text-blue-400" :
                          "bg-gray-700/50 text-gray-500"
                        }`}>{m.status}</span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1 truncate">{m.objective}</p>
                    {m.tasks?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {m.tasks.map((t: any) => (
                          <span key={t.id} className={`px-1.5 py-0.5 rounded text-[10px] ${
                            t.status === "completed" ? "bg-emerald-500/10 text-emerald-400" :
                            t.status === "in_progress" ? "bg-blue-500/10 text-blue-400 animate-pulse" :
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

          {/* Live Search Progress */}
          {progress.length > 0 && (
            <div className="bg-gray-800/20 rounded-xl border border-emerald-800/30 p-5">
              <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                Search Progress
              </h2>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {progress.map((p: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 text-sm py-2 border-b border-gray-800/50 last:border-0">
                    <span className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px] font-mono whitespace-nowrap">{p.source.replace(/_/g, " ")}</span>
                    <span className="text-gray-400 flex-1 truncate">{p.query}</span>
                    <span className="text-white font-mono text-xs tabular-nums">{p.found} leads</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 pt-2 border-t border-gray-700/30 text-xs text-gray-500 flex justify-between">
                <span>Total found: {progress.reduce((s: number, p: any) => s + p.found, 0)} leads</span>
                <span>{progress.length} sources</span>
              </div>
            </div>
          )}

          {/* Sources */}
          {dash?.sources && dash.sources.length > 0 && (
            <div className="bg-gray-800/20 rounded-xl border border-gray-700/50 p-5">
              <h2 className="text-white font-semibold mb-3">Enabled Lead Sources</h2>
              <div className="flex flex-wrap gap-1.5">
                {(dash?.sources ?? []).map((s: string) => (
                  <span key={s} className="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs border border-emerald-500/20">{s.replace(/_/g, " ")}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">

          {/* VP Status Card */}
          <div className="bg-gray-800/20 rounded-xl border border-gray-700/50 p-5">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Brain size={16} className="text-emerald-400" />
              VP Status
            </h2>
            <div className="space-y-3">
              {[
                { label: "Product", value: vp.product_name || "—" },
                { label: "Target Country", value: vp.target_country || "—" },
                { label: "Business Types", value: vp.target_business_types || "—" },
                { label: "ICP", value: vp.icp_description || "—" },
                { label: "Outreach", value: vp.outreach_active ? "Active" : "Inactive", highlight: vp.outreach_active },
                { label: "Active Missions", value: dash?.active_missions ?? 0 },
                { label: "SDRs Active", value: `${dash?.active_sdrs ?? 0}/${dash?.sdrs ?? 0}` },
              ].map(s => (
                <div key={s.label} className="flex justify-between text-sm">
                  <span className="text-gray-400">{s.label}</span>
                  <span className={`${s.highlight ? "text-emerald-400 font-medium" : "text-white"}`}>{s.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* VP Decisions */}
          <div className="bg-gray-800/20 rounded-xl border border-gray-700/50 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-semibold">VP Decisions</h2>
              <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">{decisions.length}</span>
            </div>
            {decisions.length === 0 ? (
              <p className="text-gray-500 text-sm py-4 text-center">No decisions yet</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {decisions.slice(0, 20).map((d: any) => (
                  <div key={d.id || d.created_at || Math.random()} className="p-2.5 bg-gray-800/40 rounded-lg border border-gray-700/30">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        d.action_type === "research" ? "bg-blue-500/10 text-blue-400" :
                        d.action_type === "deploy_sdr" ? "bg-emerald-500/10 text-emerald-400" :
                        d.action_type === "campaign" ? "bg-purple-500/10 text-purple-400" :
                        d.action_type === "monitor" ? "bg-gray-500/10 text-gray-400" :
                        d.action_type === "wait" ? "bg-amber-500/10 text-amber-400" :
                        "bg-blue-500/10 text-blue-400"
                      }`}>{d.action_type}</span>
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
