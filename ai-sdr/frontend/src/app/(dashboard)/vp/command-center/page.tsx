"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api-client"

type VPMission = {
  id: string
  name: string
  objective: string
  status: string
  tasks: VPTask[]
  created_at: string
}

type VPTask = {
  id: string
  agent_type: string
  agent_id: string
  objective: string
  status: string
  confidence_score: number
  vp_feedback: string
  report_summary: string
}

type VPReport = {
  id: string
  action_type: string
  reasoning: string
  details: any
  created_at: string
}

export default function VPCommandCenter() {
  const [vp, setVp] = useState<any>(null)
  const [dashboard, setDashboard] = useState<any>(null)
  const [missions, setMissions] = useState<VPMission[]>([])
  const [decisions, setDecisions] = useState<VPReport[]>([])
  const [situation, setSituation] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [selectedMission, setSelectedMission] = useState<string | null>(null)
  const [missionDetail, setMissionDetail] = useState<any>(null)
  const [pipeline, setPipeline] = useState<any>(null)

  const load = async () => {
    try {
      const [vpRes, cmdRes] = await Promise.all([
        api.get<any>("/vp/profile"),
        api.get<any>("/vp/command-center"),
      ])
      setVp(vpRes)
      if (cmdRes && !cmdRes.error) {
        setDashboard(cmdRes.dashboard)
        setMissions(cmdRes.missions || [])
        setDecisions(cmdRes.recent_decisions || [])
        setSituation(cmdRes.situation)
        setPipeline(cmdRes.intelligence_pipeline)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const runDecision = async () => {
    setExecuting(true)
    try {
      await api.post("/vp/decide")
      load()
    } catch (e) {
      console.error(e)
    } finally {
      setExecuting(false)
    }
  }

  const openMissionDetail = async (missionId: string) => {
    setSelectedMission(missionId)
    try {
      const detail = await api.get<any>(`/vp/missions/${missionId}`)
      setMissionDetail(detail)
    } catch (e) {
      console.error(e)
    }
  }

  const evaluateMission = async (missionId: string) => {
    try {
      const res = await api.post<any>(`/vp/missions/${missionId}/evaluate`)
      alert(`Evaluation: ${res.verdict.toUpperCase()}\n${res.vp_recommendation}`)
      load()
    } catch (e: any) {
      alert("Evaluation failed: " + e.message)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "text-emerald-400"
      case "in_progress": return "text-blue-400"
      case "blocked": return "text-red-400"
      case "draft": return "text-gray-400"
      default: return "text-gray-400"
    }
  }

  const getAgentIcon = (type: string) => {
    switch (type) {
      case "research": return "🔍"
      case "outreach": return "📧"
      case "linkedin": return "💼"
      case "calling": return "📞"
      default: return "🤖"
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
      <div className="max-w-2xl mx-auto py-12 px-4 text-center">
        <h1 className="text-2xl font-bold text-white mb-4">No VP Sales AI Found</h1>
        <p className="text-gray-400 mb-4">Create a VP Sales profile from the VP Dashboard to enable the Command Center.</p>
        <a href="/vp/dashboard" className="text-emerald-400 hover:text-emerald-300 underline">Go to VP Dashboard →</a>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">VP Command Center</h1>
          <p className="text-sm text-gray-400 mt-1">
            {vp.name} &middot; {vp.product_name || "No product"} &middot; {vp.target_country || "No country"}
            {vp.outreach_active && <span className="ml-2 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-xs">Sales Team Active</span>}
          </p>
        </div>
        <button
          onClick={runDecision}
          disabled={executing}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium flex items-center gap-2"
        >
          {executing ? (
            <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
          ) : null}
          {executing ? "VP Thinking..." : "Run VP Decision"}
        </button>
      </div>

      {/* Situation Overview */}
      {situation && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {[
            { label: "CRM Leads", value: situation.total_leads, color: "text-blue-400" },
            { label: "Unconverted", value: situation.unconverted_research, color: "text-amber-400" },
            { label: "Research Agents", value: situation.total_agents, color: "text-purple-400" },
            { label: "Active SDRs", value: `${situation.active_sdrs}/${situation.total_sdrs}`, color: "text-emerald-400" },
            { label: "Active Missions", value: situation.active_missions, color: "text-cyan-400" },
            { label: "Product Info", value: situation.has_product_info ? "Yes" : "No", color: situation.has_product_info ? "text-emerald-400" : "text-red-400" },
            { label: "ICP Defined", value: situation.has_icp ? "Yes" : "No", color: situation.has_icp ? "text-emerald-400" : "text-red-400" },
          ].map((stat) => (
            <div key={stat.label} className="p-3 bg-[#1a1a2e] rounded-lg border border-gray-800">
              <div className={`text-lg font-bold ${stat.color}`}>{stat.value}</div>
              <div className="text-xs text-gray-500 mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Missions Column */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              Active Missions
              <span className="text-xs text-gray-500 font-normal ml-auto">
                {missions.filter(m => m.status === "in_progress" || m.status === "draft").length} active
              </span>
            </h2>

            {missions.length === 0 ? (
              <p className="text-gray-500 text-sm">No missions yet. Click "Run VP Decision" to start.</p>
            ) : (
              <div className="space-y-3">
                {missions.map((mission) => {
                  const taskCount = mission.tasks?.length || 0
                  const completed = mission.tasks?.filter(t => t.status === "completed").length || 0
                  const isExpanded = selectedMission === mission.id

                  return (
                    <div key={mission.id} className="border border-gray-700 rounded-lg overflow-hidden">
                      <button
                        onClick={() => openMissionDetail(mission.id)}
                        className="w-full flex items-center justify-between p-3 hover:bg-gray-800/30 transition-colors text-left"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className={`w-2 h-2 rounded-full shrink-0 ${
                            mission.status === "completed" ? "bg-emerald-400" :
                            mission.status === "in_progress" ? "bg-blue-400" :
                            mission.status === "blocked" ? "bg-red-400" :
                            "bg-gray-400"
                          }`} />
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-white truncate">{mission.name}</div>
                            <div className="text-xs text-gray-500 truncate mt-0.5">{mission.objective.substring(0, 120)}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0 ml-2">
                          <span className={`text-xs font-medium ${getStatusColor(mission.status)}`}>
                            {taskCount > 0 ? `${completed}/${taskCount} tasks` : mission.status}
                          </span>
                          <svg className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      </button>

                      {isExpanded && missionDetail && missionDetail.id === mission.id && (
                        <div className="border-t border-gray-700 p-3 space-y-2 bg-gray-800/20">
                          {missionDetail.vp_reasoning && (
                            <div className="p-2 bg-gray-800/50 rounded text-xs text-gray-400">
                              <span className="text-gray-500">VP Reasoning: </span>{missionDetail.vp_reasoning}
                            </div>
                          )}
                          {missionDetail.tasks?.length > 0 ? (
                            <div className="space-y-2">
                              {missionDetail.tasks.map((task: any) => (
                                <div key={task.id} className="p-2 bg-gray-800/30 rounded border border-gray-700/50">
                                  <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <span className="text-sm">{getAgentIcon(task.agent_type)}</span>
                                      <div className="min-w-0">
                                        <div className="text-xs text-white font-medium">
                                          {task.agent_type.charAt(0).toUpperCase() + task.agent_type.slice(1)} Agent
                                        </div>
                                        <div className="text-xs text-gray-500 truncate">{task.objective.substring(0, 100)}</div>
                                      </div>
                                    </div>
                                    <span className={`text-xs shrink-0 ${
                                      task.status === "completed" ? "text-emerald-400" :
                                      task.status === "in_progress" ? "text-blue-400" :
                                      task.status === "failed" ? "text-red-400" :
                                      "text-gray-500"
                                    }`}>{task.status}</span>
                                  </div>
                                  {task.report_summary && (
                                    <p className="text-xs text-gray-500 mt-1 ml-6">{task.report_summary}</p>
                                  )}
                                  {task.confidence_score !== null && (
                                    <div className="flex items-center gap-2 mt-1 ml-6">
                                      <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
                                        <div
                                          className={`h-full rounded-full ${
                                            task.confidence_score >= 0.7 ? "bg-emerald-500" :
                                            task.confidence_score >= 0.4 ? "bg-amber-500" :
                                            "bg-red-500"
                                          }`}
                                          style={{ width: `${(task.confidence_score || 0) * 100}%` }}
                                        />
                                      </div>
                                      <span className="text-[10px] text-gray-500">{(task.confidence_score * 100).toFixed(0)}%</span>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-gray-500">No tasks assigned yet.</p>
                          )}
                          <div className="flex gap-2 mt-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); evaluateMission(mission.id) }}
                              className="px-2 py-1 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 rounded text-xs"
                            >
                              Evaluate Mission
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Agent Performance */}
          {dashboard?.agent_performance && dashboard.agent_performance.length > 0 && (
            <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
              <h2 className="text-lg font-semibold text-white mb-3">Agent Performance KPIs</h2>
              <div className="space-y-2">
                {dashboard.agent_performance.map((perf: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-800/30 rounded">
                    <div>
                      <span className="text-xs text-gray-300">{perf.agent_type}</span>
                      <span className="text-xs text-gray-500 ml-2">{perf.metric_name.replace(/_/g, " ")}</span>
                    </div>
                    <span className="text-sm font-medium text-white">{perf.metric_value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Decisions & Reports */}
        <div className="space-y-4">
          {/* VP Status */}
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
            <h2 className="text-lg font-semibold text-white mb-3">VP Status</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Product</span>
                <span className="text-white">{vp.product_name || "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Target Country</span>
                <span className="text-white">{vp.target_country || "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Business Types</span>
                <span className="text-white">{(vp.target_business_types || "—").substring(0, 40)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Outreach</span>
                <span className={vp.outreach_active ? "text-emerald-400" : "text-gray-500"}>{vp.outreach_active ? "Active" : "Inactive"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Missions Active</span>
                <span className="text-white">{dashboard?.active_missions || 0}</span>
              </div>
            </div>
          </div>

          {/* Lead Intelligence Pipeline */}
          {pipeline && (
            <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
              <h2 className="text-lg font-semibold text-white mb-3">Lead Intelligence Pipeline</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Pipeline Health</span>
                  <span className={`font-medium ${
                    pipeline.pipeline_health === "healthy" ? "text-emerald-400" :
                    pipeline.pipeline_health === "partial" ? "text-amber-400" :
                    pipeline.pipeline_health === "unscored" ? "text-yellow-400" :
                    "text-red-400"
                  }`}>{pipeline.pipeline_health}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Leads in CRM</span>
                  <span className="text-white">{pipeline.leads_in_crm}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Leads Scored</span>
                  <span className="text-white">{pipeline.leads_scored}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Avg Lead Score</span>
                  <span className="text-white">{pipeline.avg_lead_score}/100</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Companies Analyzed</span>
                  <span className="text-white">{pipeline.companies_analyzed}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Buying Signals</span>
                  <span className="text-white">{pipeline.buying_signals_detected}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Validations</span>
                  <span className="text-white">{pipeline.validations_completed}</span>
                </div>
              </div>
            </div>
          )}

          {/* Recent VP Decisions */}
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
            <h2 className="text-lg font-semibold text-white mb-3">VP Decisions</h2>
            {decisions.length === 0 ? (
              <p className="text-gray-500 text-sm">No decisions yet.</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {decisions.map((d: any) => (
                  <div key={d.id || d.created_at} className="p-2 bg-gray-800/30 rounded border border-gray-700/50">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded text-[10px] font-medium">{d.action_type}</span>
                      <span className="text-[10px] text-gray-600">{d.created_at ? new Date(d.created_at).toLocaleString() : ""}</span>
                    </div>
                    <p className="text-xs text-gray-400">{d.reasoning}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sources */}
          <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
            <h2 className="text-lg font-semibold text-white mb-3">Enabled Sources</h2>
            <div className="flex flex-wrap gap-1.5">
              {(dashboard?.sources_used ?? []).map((s: string) => (
                <span key={s} className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px] font-medium">
                  {s.replace(/_/g, " ")}
                </span>
              ))}
              {(!dashboard?.sources_used || dashboard.sources_used.length === 0) && (
                <span className="text-xs text-gray-500">No sources enabled</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
