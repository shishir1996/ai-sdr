"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api-client"

export default function VPResearchAgentsPage() {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await api.get<{ agents: any[] }>("/vp/agents")
      setAgents(res.agents || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const runAgent = async (agentId: string) => {
    try {
      const res = await api.post<any>(`/vp/agents/${agentId}/run`)
      alert(res.message)
      load()
    } catch (e) {
      console.error(e)
    }
  }

  const deleteAgent = async (agentId: string, name: string) => {
    if (!confirm(`Delete research agent "${name}"? This cannot be undone.`)) return
    try {
      await api.delete(`/vp/agents/${agentId}`)
      load()
    } catch (e: any) {
      alert("Failed to delete: " + (e.message || "Unknown error"))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Research Agents</h1>
          <p className="text-sm text-gray-400 mt-1">
            VP-managed agents that discover leads from public web sources.
          </p>
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="text-center py-12">
          <div className="w-12 h-12 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <p className="text-gray-400">No research agents created yet.</p>
          <p className="text-gray-500 text-sm mt-1">
            The VP Sales AI autonomously creates and manages research agents. Go to the VP Dashboard and click <strong>"Run Decision Engine"</strong> to start.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {agents.map((agent: any) => (
            <div key={agent.id} className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-white font-semibold">{agent.name}</h3>
                  <p className="text-sm text-gray-400 mt-1">
                    {agent.target_industry && `${agent.target_industry} · `}
                    {agent.target_country && `${agent.target_country}`}
                  </p>
                </div>
                  <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    agent.status === "running" ? "bg-emerald-500/10 text-emerald-400" :
                    agent.status === "completed" ? "bg-blue-500/10 text-blue-400" :
                    "bg-gray-500/10 text-gray-400"
                  }`}>
                    {agent.status}
                  </span>
                  <button
                    onClick={() => runAgent(agent.id)}
                    disabled={agent.status === "running"}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded text-xs font-medium transition-colors"
                  >
                    Run
                  </button>
                  <button
                    onClick={() => deleteAgent(agent.id, agent.name)}
                    className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded text-xs font-medium transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
              {agent.search_queries && (
                <div className="mt-3">
                  <p className="text-xs text-gray-500 mb-1">Queries:</p>
                  <div className="flex flex-wrap gap-1">
                    {agent.search_queries.split("\n").filter(Boolean).map((q: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-gray-700/50 text-gray-300 rounded text-xs">{q}</span>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex gap-4 mt-3 text-xs text-gray-500">
                <span>Leads discovered: <strong className="text-white">{agent.leads_discovered || 0}</strong></span>
                <span>Max leads: <strong className="text-white">{agent.max_leads}</strong></span>
                {agent.last_run_at && <span>Last run: {new Date(agent.last_run_at).toLocaleDateString()}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
