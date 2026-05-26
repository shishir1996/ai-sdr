"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Activity, Cpu, Bell, CheckCircle } from "lucide-react"

export default function AuditPage() {
  const [activeTab, setActiveTab] = useState<"activity" | "ai" | "notifications">("activity")
  const [logs, setLogs] = useState<any[]>([])
  const [aiUsage, setAiUsage] = useState<any>(null)
  const [notifications, setNotifications] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = async (tab: string) => {
    setLoading(true)
    try {
      if (tab === "activity") {
        const data = await api.get<any[]>("/audit/logs")
        setLogs(data)
      } else if (tab === "ai") {
        const data = await api.get<any>("/audit/ai-usage")
        setAiUsage(data)
      } else if (tab === "notifications") {
        const data = await api.get<any[]>("/audit/notifications")
        setNotifications(data)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(activeTab)
  }, [activeTab])

  const markRead = async (id: string) => {
    await api.put(`/audit/notifications/${id}/read`)
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)))
  }

  const tabs = [
    { id: "activity", label: "Activity Log", icon: Activity },
    { id: "ai", label: "AI Usage", icon: Cpu },
    { id: "notifications", label: "Notifications", icon: Bell },
  ]

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Monitoring & Audit</h1>

      <div className="flex gap-2 border-b border-gray-700 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t text-sm ${
              activeTab === tab.id ? "bg-gray-800 text-white border-b-2 border-indigo-500" : "text-gray-400 hover:text-white"
            }`}
          >
            <tab.icon size={16} /> {tab.label}
          </button>
        ))}
      </div>

      {loading && <div className="text-gray-400">Loading...</div>}

      {!loading && activeTab === "activity" && (
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="bg-gray-800 rounded border border-gray-700 p-3 flex items-start gap-3">
              <Activity size={16} className="text-indigo-400 mt-1" />
              <div className="flex-1">
                <div className="text-white text-sm font-medium">{log.action}</div>
                <div className="text-gray-400 text-xs mt-1">
                  {log.resource_type} · {log.ip_address || "N/A"}
                </div>
                {log.details && (
                  <pre className="text-gray-500 text-xs mt-1">{JSON.stringify(log.details, null, 2)}</pre>
                )}
              </div>
              <div className="text-gray-500 text-xs">{new Date(log.created_at).toLocaleString()}</div>
            </div>
          ))}
          {logs.length === 0 && <div className="text-gray-500 text-center py-8">No activity logs yet.</div>}
        </div>
      )}

      {!loading && activeTab === "ai" && aiUsage && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="text-2xl font-bold text-white">{aiUsage.summary?.total_tokens?.toLocaleString() || 0}</div>
              <div className="text-gray-400 text-sm">Total Tokens Used</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="text-2xl font-bold text-green-400">${(aiUsage.summary?.total_cost || 0).toFixed(4)}</div>
              <div className="text-gray-400 text-sm">Total AI Cost</div>
            </div>
          </div>
          <div className="space-y-2">
            {aiUsage.logs?.map((log: any) => (
              <div key={log.id} className="bg-gray-800 rounded border border-gray-700 p-3">
                <div className="flex justify-between">
                  <span className="text-white text-sm font-medium">{log.provider} · {log.model}</span>
                  <span className="text-gray-400 text-xs">{new Date(log.created_at).toLocaleString()}</span>
                </div>
                <div className="text-gray-400 text-xs mt-1">
                  Action: {log.action} · Tokens: {log.total_tokens} · Cost: ${log.cost?.toFixed(6)} · Duration: {log.duration_ms}ms
                </div>
              </div>
            ))}
            {(!aiUsage.logs || aiUsage.logs.length === 0) && (
              <div className="text-gray-500 text-center py-8">No AI usage yet.</div>
            )}
          </div>
        </div>
      )}

      {!loading && activeTab === "notifications" && (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`bg-gray-800 rounded border p-3 flex items-start gap-3 cursor-pointer ${
                n.is_read ? "border-gray-700 opacity-60" : "border-indigo-700"
              }`}
              onClick={() => !n.is_read && markRead(n.id)}
            >
              <Bell size={16} className={n.is_read ? "text-gray-500" : "text-indigo-400"} />
              <div className="flex-1">
                <div className="text-white text-sm font-medium">{n.title}</div>
                {n.body && <div className="text-gray-400 text-xs mt-1">{n.body}</div>}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500 text-xs">{new Date(n.created_at).toLocaleString()}</span>
                {!n.is_read && <CheckCircle size={14} className="text-indigo-400" />}
              </div>
            </div>
          ))}
          {notifications.length === 0 && <div className="text-gray-500 text-center py-8">No notifications yet.</div>}
        </div>
      )}
    </div>
  )
}
