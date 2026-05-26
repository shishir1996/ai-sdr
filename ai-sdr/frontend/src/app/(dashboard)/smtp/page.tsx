"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Mail, Plus, Settings, TestTube, RefreshCw, AlertTriangle, CheckCircle, XCircle, Globe, Shield, ArrowRight } from "lucide-react"

interface SMTPConfig {
  id: string
  provider: string
  host: string
  port: number
  use_tls: boolean
  use_ssl: boolean
  username: string
  sender_name: string
  sender_email: string
  reply_to: string | null
  daily_limit: number
  hourly_limit: number
  warmup_enabled: boolean
  warmup_current_daily: number
  is_active: boolean
  created_at: string
}

const SMTP_PROVIDERS = [
  { id: "hostinger", name: "Hostinger" },
  { id: "gmail", name: "Gmail SMTP" },
  { id: "outlook", name: "Outlook SMTP" },
  { id: "hotmail", name: "Hotmail" },
  { id: "zoho", name: "Zoho Mail" },
  { id: "zoho_eu", name: "Zoho Mail (EU)" },
  { id: "yahoo", name: "Yahoo Mail" },
  { id: "yandex", name: "Yandex Mail" },
  { id: "protonmail", name: "ProtonMail (Bridge)" },
  { id: "sendgrid", name: "SendGrid" },
  { id: "mailgun", name: "Mailgun" },
  { id: "postmark", name: "Postmark" },
  { id: "amazon_ses", name: "Amazon SES" },
  { id: "sendinblue", name: "Brevo (Sendinblue)" },
  { id: "elasticemail", name: "Elastic Email" },
  { id: "custom", name: "Custom SMTP" },
]

export default function SMTPPage() {
  const [configs, setConfigs] = useState<SMTPConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; error?: string } | null>(null)
  const [dnsGuide, setDnsGuide] = useState<any>(null)
  const [dnsDomain, setDnsDomain] = useState("offdx.in")
  const [dnsCheckResult, setDnsCheckResult] = useState<any>(null)
  const [dnsChecking, setDnsChecking] = useState(false)
  const [dnsError, setDnsError] = useState<string | null>(null)
  const [dnsProvider, setDnsProvider] = useState("hostinger")
  const [dkimSelector, setDkimSelector] = useState("default")
  const [form, setForm] = useState({
    provider: "hostinger",
    host: "",
    port: 465,
    use_tls: false,
    use_ssl: true,
    username: "",
    password: "",
    sender_name: "AI SDR",
    sender_email: "",
    reply_to: "",
    daily_limit: 300,
    hourly_limit: 30,
    warmup_enabled: false,
    is_active: true,
  })

  const fetchConfigs = async () => {
    try {
      const data = await api.get<SMTPConfig[]>("/smtp/configs")
      setConfigs(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const fetchDnsGuide = async (domain: string) => {
    try {
      const data = await api.get(`/smtp/dns-guide?domain=${domain}`)
      setDnsGuide(data)
    } catch { }
  }

  const runDnsCheck = async () => {
    setDnsChecking(true)
    setDnsError(null)
    setDnsCheckResult(null)
    try {
      const result = await api.get(`/smtp/dns-check?domain=${dnsDomain}&dkim_selector=${dkimSelector}`)
      setDnsCheckResult(result)
    } catch (e: any) {
      setDnsError(e.message || "DNS check failed")
    } finally {
      setDnsChecking(false)
    }
  }

  useEffect(() => {
    fetchConfigs()
    fetchDnsGuide("offdx.in")
  }, [])

  const handleProviderChange = (provider: string) => {
    const config: Record<string, { host: string; port: number; use_ssl: boolean; use_tls: boolean }> = {
      hostinger: { host: "smtp.hostinger.com", port: 465, use_ssl: true, use_tls: false },
      gmail: { host: "smtp.gmail.com", port: 587, use_ssl: false, use_tls: true },
      outlook: { host: "smtp.office365.com", port: 587, use_ssl: false, use_tls: true },
      hotmail: { host: "smtp-mail.outlook.com", port: 587, use_ssl: false, use_tls: true },
      zoho: { host: "smtp.zoho.com", port: 587, use_ssl: false, use_tls: true },
      zoho_eu: { host: "smtp.zoho.eu", port: 587, use_ssl: false, use_tls: true },
      yahoo: { host: "smtp.mail.yahoo.com", port: 587, use_ssl: false, use_tls: true },
      yandex: { host: "smtp.yandex.com", port: 587, use_ssl: false, use_tls: true },
      protonmail: { host: "127.0.0.1", port: 1025, use_ssl: false, use_tls: false },
      sendgrid: { host: "smtp.sendgrid.net", port: 587, use_ssl: false, use_tls: true },
      mailgun: { host: "smtp.mailgun.org", port: 587, use_ssl: false, use_tls: true },
      postmark: { host: "smtp.postmarkapp.com", port: 587, use_ssl: false, use_tls: true },
      amazon_ses: { host: "email-smtp.us-east-1.amazonaws.com", port: 587, use_ssl: false, use_tls: true },
      sendinblue: { host: "smtp-relay.sendinblue.com", port: 587, use_ssl: false, use_tls: true },
      elasticemail: { host: "smtp.elasticemail.com", port: 2525, use_ssl: false, use_tls: true },
      custom: { host: "", port: 587, use_ssl: false, use_tls: true },
    }
    const preset = config[provider]
    if (preset) {
      setForm((f) => ({ ...f, provider, ...preset }))
    }
  }

  const handleTest = async () => {
    setTestResult(null)
    try {
      const result = await api.post<{ success: boolean; error?: string }>("/smtp/test", form)
      setTestResult(result)
    } catch (e: any) {
      setTestResult({ success: false, error: e.message })
    }
  }

  const handleSave = async () => {
    try {
      await api.post("/smtp/configs", form)
      setShowForm(false)
      setForm({
        provider: "hostinger", host: "", port: 465, use_tls: false, use_ssl: true,
        username: "", password: "", sender_name: "AI SDR", sender_email: "", reply_to: "",
        daily_limit: 300, hourly_limit: 30, warmup_enabled: false, is_active: true,
      })
      await fetchConfigs()
    } catch (e: any) {
      alert(e.message)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this SMTP configuration?")) return
    await api.delete(`/smtp/configs/${id}`)
    await fetchConfigs()
  }

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">SMTP Configuration</h1>
          <p className="text-gray-400 mt-1">Configure your email sending infrastructure</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          <Plus size={18} /> Add Sender
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="text-2xl font-bold text-white">{configs.length}</div>
          <div className="text-gray-400 text-sm">Configured Senders</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="text-2xl font-bold text-green-400">{configs.filter((c) => c.is_active).length}</div>
          <div className="text-gray-400 text-sm">Active Senders</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="text-2xl font-bold text-blue-400">
            {configs.reduce((sum, c) => sum + c.daily_limit, 0)}
          </div>
          <div className="text-gray-400 text-sm">Daily Capacity</div>
        </div>
      </div>

      {showForm && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-white">Add SMTP Sender</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Provider</label>
              <select
                value={form.provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              >
                {SMTP_PROVIDERS.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Sender Email *</label>
              <input
                type="email"
                value={form.sender_email}
                onChange={(e) => setForm((f) => ({ ...f, sender_email: e.target.value }))}
                placeholder="hello@offdx.in"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Sender Name</label>
              <input
                type="text"
                value={form.sender_name}
                onChange={(e) => setForm((f) => ({ ...f, sender_name: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Reply-To</label>
              <input
                type="email"
                value={form.reply_to}
                onChange={(e) => setForm((f) => ({ ...f, reply_to: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">SMTP Host</label>
              <input
                type="text"
                value={form.host}
                onChange={(e) => setForm((f) => ({ ...f, host: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Port</label>
              <input
                type="number"
                value={form.port}
                onChange={(e) => setForm((f) => ({ ...f, port: parseInt(e.target.value) }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Username</label>
              <input
                type="text"
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Password</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Daily Limit</label>
              <input
                type="number"
                value={form.daily_limit}
                onChange={(e) => setForm((f) => ({ ...f, daily_limit: parseInt(e.target.value) }))}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="flex items-center gap-3 mt-6">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="rounded bg-gray-700 border-gray-600"
                />
                <span className="text-white text-sm">Set as Active</span>
              </label>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.warmup_enabled}
                onChange={(e) => setForm((f) => ({ ...f, warmup_enabled: e.target.checked }))}
                className="rounded bg-gray-700 border-gray-600"
              />
              <span className="text-gray-300 text-sm">Enable Warmup</span>
            </label>
          </div>

          <div className="flex gap-3 pt-2">
            <button onClick={handleTest} className="flex items-center gap-2 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600">
              <TestTube size={16} /> Test
            </button>
            <button onClick={handleSave} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
              Save Configuration
            </button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-gray-400 hover:text-white">Cancel</button>
          </div>

          {testResult && (
            <div className={`flex items-center gap-2 p-3 rounded ${testResult.success ? "bg-green-900/30 text-green-400" : "bg-red-900/30 text-red-400"}`}>
              {testResult.success ? <CheckCircle size={18} /> : <XCircle size={18} />}
              {testResult.success ? "Test email sent successfully!" : `Failed: ${testResult.error}`}
            </div>
          )}

          <div className="mt-4 p-3 rounded-lg bg-amber-900/20 border border-amber-700/30 text-xs text-amber-300">
            <strong>Reply Detection:</strong> To check for email replies on this SMTP account, configure IMAP
            inbox access in the SDR wizard (<strong>SDR Settings → Connect Accounts → SMTP</strong>).
            IMAP settings are saved per-SDR and used for automatic reply detection.
          </div>
        </div>
      )}

      <div className="space-y-3">
        {configs.map((config) => (
          <div key={config.id} className="bg-gray-800 rounded-lg border border-gray-700 p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Mail className="text-indigo-400" size={24} />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-white font-medium">{config.sender_email}</span>
                  {config.is_active && <span className="px-2 py-0.5 bg-green-900 text-green-400 text-xs rounded-full">Active</span>}
                </div>
                <div className="text-gray-400 text-sm">
                  {config.provider} · {config.daily_limit}/day · {config.warmup_enabled ? "Warmup" : "No warmup"}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => handleDelete(config.id)} className="p-2 text-gray-400 hover:text-red-400">
                <XCircle size={18} />
              </button>
            </div>
          </div>
        ))}
        {configs.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Mail size={48} className="mx-auto mb-3 opacity-50" />
            <p>No SMTP senders configured yet.</p>
            <p className="text-sm">Add your Hostinger email or another SMTP provider to start sending.</p>
          </div>
        )}
      </div>

      {dnsGuide && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Globe size={18} /> DNS Configuration Guide
            </h2>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={dnsDomain}
                onChange={(e) => setDnsDomain(e.target.value)}
                placeholder="yourdomain.com"
                className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-white text-sm w-36"
              />
              <select
                value={dkimSelector}
                onChange={(e) => setDkimSelector(e.target.value)}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-white text-sm"
              >
                <option value="default">DKIM: default</option>
                <option value="hostinger">DKIM: hostinger</option>
                <option value="google">DKIM: google</option>
              </select>
              <button
                onClick={runDnsCheck}
                disabled={dnsChecking}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm disabled:opacity-50"
              >
                <Shield size={14} />
                {dnsChecking ? "Checking..." : "Verify DNS"}
              </button>
            </div>
          </div>

          <p className="text-gray-400 text-sm mb-4">
            Add these DNS records to your domain provider to ensure email deliverability, then verify them with the button above.
          </p>

          {dnsCheckResult && (
            <div className="mb-4 space-y-2">
              <h3 className="text-sm font-medium text-white">DNS Verification Results</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {(["spf", "dkim", "dmarc", "mx"] as const).map((key) => {
                  const rec = dnsCheckResult[key]
                  const ok = rec?.found
                  return (
                    <div key={key} className={`p-3 rounded-lg border ${ok ? "border-green-700 bg-green-900/20" : "border-red-700 bg-red-900/20"}`}>
                      <div className="flex items-center gap-1.5 mb-1">
                        {ok ? <CheckCircle size={14} className="text-green-400" /> : <XCircle size={14} className="text-red-400" />}
                        <span className="text-white text-sm font-medium uppercase">{key}</span>
                      </div>
                      {ok ? (
                        <span className="text-green-400 text-xs">Configured</span>
                      ) : (
                        <span className="text-red-400 text-xs">Not found</span>
                      )}
                      {rec?.records?.length > 0 && (
                        <div className="mt-1 text-gray-400 text-[10px] truncate max-w-full">
                          {rec.records.map((r: any, i: number) => (
                            <div key={i} className="truncate">{typeof r === "string" ? r : r.host || r.value}</div>
                          ))}
                        </div>
                      )}
                      {!ok && key === "dkim" && (
                        <div className="text-gray-500 text-[10px] mt-1">Try selector: hostinger</div>
                      )}
                    </div>
                  )
                })}
              </div>
              {dnsCheckResult.all_configured && (
                <div className="flex items-center gap-2 p-2 bg-green-900/30 text-green-400 text-sm rounded">
                  <CheckCircle size={16} /> All DNS records configured correctly!
                </div>
              )}
            </div>
          )}

          {dnsError && (
            <div className="flex items-center gap-2 p-3 bg-red-900/30 text-red-400 text-sm rounded mb-4">
              <XCircle size={16} /> DNS check error: {dnsError}
            </div>
          )}

          <div className="flex items-center gap-2 mb-4">
            <span className="text-gray-400 text-sm">DNS Provider:</span>
            {["hostinger", "cloudflare", "godaddy", "namecheap"].map((p) => (
              <button
                key={p}
                onClick={() => setDnsProvider(p)}
                className={`px-3 py-1 rounded text-sm ${dnsProvider === p ? "bg-indigo-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"}`}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>

          <div className="space-y-4">
            {Object.entries(dnsGuide).map(([key, section]: [string, any]) => (
              <div key={key} className="border border-gray-700 rounded p-4">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-white font-medium capitalize">{key}</h3>
                  {dnsCheckResult?.[key]?.found && <CheckCircle size={14} className="text-green-400" />}
                  {dnsCheckResult?.[key] && !dnsCheckResult[key].found && <XCircle size={14} className="text-red-400" />}
                </div>
                <p className="text-gray-400 text-sm mb-2">{section.description}</p>
                {section.record && (
                  <div className="bg-gray-900 rounded p-3 text-sm font-mono text-gray-300">
                    <div>Type: {section.record.type}</div>
                    <div>Host: {section.record.host}</div>
                    <div>Value: {section.record.value}</div>
                  </div>
                )}
                {section.steps && (
                  <ol className="list-decimal list-inside text-gray-400 text-sm space-y-1 mb-2">
                    {section.steps.map((step: string, i: number) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                )}
                {section.providers?.[dnsProvider] && (
                  <div className="bg-indigo-900/20 border border-indigo-800 rounded p-2 mt-2">
                    <span className="text-indigo-300 text-xs font-medium">{dnsProvider.charAt(0).toUpperCase() + dnsProvider.slice(1)}:</span>
                    <span className="text-gray-300 text-xs ml-1">{section.providers[dnsProvider]}</span>
                  </div>
                )}
                {section.records && section.records.map((r: any, i: number) => (
                  <div key={i} className="bg-gray-900 rounded p-3 text-sm font-mono text-gray-300 mt-2">
                    <div>Type: {r.type} · Host: {r.host} · Value: {r.value} · Priority: {r.priority}</div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
