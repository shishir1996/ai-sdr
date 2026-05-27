"use client"

import { useState, useEffect } from "react"
import { api, API_BASE } from "@/lib/api-client"
import {
  Phone, PhoneCall, PhoneOff, Settings, Shield, Activity, Zap,
  CheckCircle, XCircle, AlertTriangle, Loader, RefreshCw, Save,
  ExternalLink, Plus, Trash2, Play, Square, Download,
  ChevronDown, ChevronRight, Mic, Volume2, Globe, Server,
} from "lucide-react"

export default function CallingAdminPage() {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [vapiKey, setVapiKey] = useState("")
  const [twilioSid, setTwilioSid] = useState("")
  const [twilioToken, setTwilioToken] = useState("")
  const [connecting, setConnecting] = useState(false)
  const [testPhone, setTestPhone] = useState("")
  const [testResult, setTestResult] = useState<any>(null)
  const [syncResult, setSyncResult] = useState<any>(null)
  const [activeTab, setActiveTab] = useState("dashboard")

  const loadStatus = async () => {
    try {
      const data = await api.get("/admin/calling/status")
      setStatus(data)
    } catch { } finally { setLoading(false) }
  }

  useEffect(() => { loadStatus() }, [])

  const connectVapi = async () => {
    if (!vapiKey) return
    setConnecting(true)
    try {
      await api.post("/admin/calling/connect/vapi", { api_key: vapiKey })
      await loadStatus()
    } catch (e: any) { alert(e.message) }
    finally { setConnecting(false) }
  }

  const connectTwilio = async () => {
    if (!twilioSid || !twilioToken) return
    setConnecting(true)
    try {
      await api.post("/admin/calling/connect/twilio", { account_sid: twilioSid, auth_token: twilioToken })
      await loadStatus()
    } catch (e: any) { alert(e.message) }
    finally { setConnecting(false) }
  }

  const autoCreateAssistant = async () => {
    try {
      const r = await api.post<any>("/admin/calling/assistants/auto-create")
      alert(r.message || "Assistant created!")
      await loadStatus()
    } catch (e: any) { alert(e.message) }
  }

  const testCall = async () => {
    if (!testPhone) return
    setTestResult(null)
    try {
      const agents = status?.voice_agents || []
      const defaultAgent = agents.find((a: any) => a.is_default) || agents[0]
      const r = await api.post("/admin/calling/test-call", {
        phone_number: testPhone,
        voice_agent_id: defaultAgent?.id || "",
      })
      setTestResult(r)
    } catch (e: any) { setTestResult({ error: e.message }) }
  }

  const runSync = async () => {
    setSyncResult(null)
    try {
      const r = await api.post("/admin/calling/sync")
      setSyncResult(r)
    } catch (e: any) { setSyncResult({ error: e.message }) }
  }

  if (loading) return <div className="p-8 text-gray-400">Loading calling dashboard...</div>

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <PhoneCall size={22} className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">AI Calling</h1>
            <p className="text-sm text-gray-400">Vapi.ai + Twilio — fully automated outbound calling</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={runSync} className="btn-ghost text-xs flex items-center gap-1">
            <RefreshCw size={14} /> Sync
          </button>
          <button onClick={loadStatus} className="btn-secondary text-xs flex items-center gap-1">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {syncResult && (
        <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs flex items-center gap-2">
          <CheckCircle size={14} />
          Synced: {syncResult.agents_synced} agents, {syncResult.phones_found} phones, {syncResult.call_logs_synced} call logs
        </div>
      )}

      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 mb-2">
            <Zap size={16} className={status?.vapi?.connected ? "text-emerald-400" : "text-gray-500"} />
            <span className="text-xs text-gray-400">Vapi</span>
          </div>
          <div className="text-lg font-bold text-white flex items-center gap-2">
            {status?.vapi?.connected ? <CheckCircle size={16} className="text-emerald-400" /> : <XCircle size={16} className="text-red-400" />}
            {status?.vapi?.connected ? "Connected" : "Disconnected"}
          </div>
          <div className="text-xs text-gray-500 mt-1">{status?.vapi?.assistants_count || 0} assistants</div>
        </div>
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 mb-2">
            <Globe size={16} className={status?.twilio?.connected ? "text-emerald-400" : "text-gray-500"} />
            <span className="text-xs text-gray-400">Twilio</span>
          </div>
          <div className="text-lg font-bold text-white flex items-center gap-2">
            {status?.twilio?.connected ? <CheckCircle size={16} className="text-emerald-400" /> : <XCircle size={16} className="text-red-400" />}
            {status?.twilio?.connected ? "Connected" : "Not configured"}
          </div>
          <div className="text-xs text-gray-500 mt-1">{status?.twilio?.available_numbers?.length || 0} numbers</div>
        </div>
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 mb-2">
            <Mic size={16} className="text-purple-400" />
            <span className="text-xs text-gray-400">Voice Agents</span>
          </div>
          <div className="text-lg font-bold text-white">{status?.voice_agents?.length || 0}</div>
          <div className="text-xs text-gray-500 mt-1">
            {status?.voice_agents?.filter((a: any) => a.is_active).length || 0} active
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 mb-2">
            <Shield size={16} className="text-amber-400" />
            <span className="text-xs text-gray-400">Kill Switch</span>
          </div>
          <div className="text-lg font-bold text-amber-400">Active</div>
          <div className="text-xs text-gray-500 mt-1">All systems operational</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-700/50">
        {[
          { id: "dashboard", label: "Dashboard" },
          { id: "connect", label: "Connect" },
          { id: "assistants", label: "Voice Agents" },
          { id: "test", label: "Test Call" },
        ].map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id ? "text-purple-400 border-purple-500" : "text-gray-500 border-transparent hover:text-gray-300"
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Dashboard Tab */}
      {activeTab === "dashboard" && (
        <div className="space-y-4">
          <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-5">
            <h3 className="text-sm font-medium text-white mb-3">Quick Actions</h3>
            <div className="flex flex-wrap gap-2">
              <button onClick={autoCreateAssistant} className="btn-primary text-xs flex items-center gap-1">
                <Plus size={14} /> Auto-Create Assistant
              </button>
              <button onClick={runSync} className="btn-secondary text-xs flex items-center gap-1">
                <RefreshCw size={14} /> Sync Vapi Resources
              </button>
            </div>
          </div>

          {status?.voice_agents?.length > 0 && (
            <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-5">
              <h3 className="text-sm font-medium text-white mb-3">Voice Agents</h3>
              <div className="space-y-2">
                {status.voice_agents.map((agent: any) => (
                  <div key={agent.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                    <div>
                      <div className="text-sm text-white font-medium">{agent.name}</div>
                      <div className="text-xs text-gray-400">
                        {agent.ai_model} · {agent.voice_provider} · {agent.vapi_assistant_id ? "Vapi connected" : "Not linked"}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {agent.is_default && <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">Default</span>}
                      {agent.is_active ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">Active</span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-500/10 text-gray-400">Inactive</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {status?.twilio?.available_numbers?.length > 0 && (
            <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-5">
              <h3 className="text-sm font-medium text-white mb-3">Twilio Numbers</h3>
              <div className="space-y-1 text-xs text-gray-400">
                {status.twilio.available_numbers.map((n: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded bg-gray-800/50">
                    <span className="text-white">{n.phone_number}</span>
                    <span className="text-gray-500">{n.friendly_name || n.phone_number}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Connect Tab */}
      {activeTab === "connect" && (
        <div className="space-y-6">
          <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-5">
            <h3 className="text-sm font-medium text-white mb-1 flex items-center gap-2">
              <Zap size={16} className="text-emerald-400" /> Vapi.ai
            </h3>
            <p className="text-xs text-gray-400 mb-4">Enter your Vapi API key. Found in Vapi dashboard → API Keys.</p>
            <div className="flex items-center gap-3">
              <input type="password" value={vapiKey} onChange={(e) => setVapiKey(e.target.value)}
                placeholder="sk-..." className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white" />
              <button onClick={connectVapi} disabled={connecting || !vapiKey}
                className="btn-primary text-sm disabled:opacity-50">
                {connecting ? <Loader size={14} className="animate-spin" /> : <Save size={14} />} Connect
              </button>
            </div>
            {status?.vapi?.connected && (
              <div className="mt-2 flex items-center gap-1 text-xs text-emerald-400">
                <CheckCircle size={12} /> Connected — {status.vapi.assistants_count} assistants found
              </div>
            )}
          </div>

          <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-5">
            <h3 className="text-sm font-medium text-white mb-1 flex items-center gap-2">
              <Globe size={16} className="text-blue-400" /> Twilio
            </h3>
            <p className="text-xs text-gray-400 mb-4">Enter Twilio credentials. Vapi uses Twilio numbers for outbound calling.</p>
            <div className="space-y-3">
              <input type="text" value={twilioSid} onChange={(e) => setTwilioSid(e.target.value)}
                placeholder="Account SID (AC...)" className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white" />
              <input type="password" value={twilioToken} onChange={(e) => setTwilioToken(e.target.value)}
                placeholder="Auth Token" className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white" />
              <button onClick={connectTwilio} disabled={connecting || !twilioSid || !twilioToken}
                className="btn-primary text-sm disabled:opacity-50">
                {connecting ? <Loader size={14} className="animate-spin" /> : <Save size={14} />} Connect Twilio
              </button>
            </div>
            {status?.twilio?.connected && (
              <div className="mt-2 flex items-center gap-1 text-xs text-emerald-400">
                <CheckCircle size={12} /> Connected — {status.twilio.available_numbers?.length || 0} phone numbers available
              </div>
            )}
          </div>
        </div>
      )}

      {/* Assistants Tab */}
      {activeTab === "assistants" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <button onClick={autoCreateAssistant} className="btn-primary text-xs flex items-center gap-1">
              <Plus size={14} /> Auto-Create Default Assistant
            </button>
          </div>
          {status?.voice_agents?.length === 0 && (
            <div className="p-8 text-center text-gray-500 text-sm">
              <Mic size={32} className="mx-auto mb-2 opacity-50" />
              No voice agents yet. Click "Auto-Create Default Assistant" to create one.
            </div>
          )}
          {status?.voice_agents?.map((agent: any) => (
            <div key={agent.id} className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-white">{agent.name}</h4>
                <div className="flex items-center gap-2">
                  {agent.is_default && <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">Default</span>}
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div><span className="text-gray-500">Model:</span> <span className="text-gray-300">{agent.ai_model}</span></div>
                <div><span className="text-gray-500">Voice:</span> <span className="text-gray-300">{agent.voice_provider}/{agent.voice_id}</span></div>
                <div><span className="text-gray-500">Temperature:</span> <span className="text-gray-300">{agent.temperature}</span></div>
                <div><span className="text-gray-500">Max Duration:</span> <span className="text-gray-300">{agent.max_duration_seconds}s</span></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Test Call Tab */}
      {activeTab === "test" && (
        <div className="space-y-4">
          <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-5">
            <h3 className="text-sm font-medium text-white mb-1">Test Call</h3>
            <p className="text-xs text-gray-400 mb-4">Make a test call to verify your Vapi + Twilio configuration.</p>
            <div className="flex items-center gap-3">
              <input type="tel" value={testPhone} onChange={(e) => setTestPhone(e.target.value)}
                placeholder="+14155551234" className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white" />
              <button onClick={testCall} disabled={!testPhone || !status?.vapi?.connected}
                className="btn-primary text-sm disabled:opacity-50 flex items-center gap-1">
                <Phone size={14} /> Call
              </button>
            </div>
            {testResult && (
              <div className="mt-3 p-3 rounded-xl bg-gray-800/50 border border-gray-700/50 text-xs">
                {testResult.error ? (
                  <div className="text-red-400">Error: {testResult.error}</div>
                ) : (
                  <div className="space-y-1 text-gray-300">
                    <div>Call ID: <span className="text-white font-mono">{testResult.callId || testResult.id || "N/A"}</span></div>
                    <div>Status: <span className="text-emerald-400">{testResult.status}</span></div>
                    {testResult.cost && <div>Cost: ${testResult.cost}</div>}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
