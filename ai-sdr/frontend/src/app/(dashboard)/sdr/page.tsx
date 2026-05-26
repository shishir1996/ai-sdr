"use client"

import { useState, useEffect, useCallback } from "react"
import { api, API_BASE } from "@/lib/api-client"
import {
  Bot, Plus, Trash2, Play, Square, Save, Settings, Globe, Mail, Phone, Linkedin,
  MessageCircle, ThumbsUp, MessageSquare, Sparkles, Target, Users, MapPin, Building2,
  Layers, ArrowRight, Clock, ChevronLeft, ChevronRight, Check, CheckCircle, Loader, Bookmark,
  Database, RefreshCw, Key, Unlink, Shield, Server, ExternalLink, AlertCircle,
  Upload, FileText, Download, XCircle, TestTube,
} from "lucide-react"

const LEAD_SOURCES = [
  { key: "web_scrape", label: "Web Scraped Leads", icon: Globe, color: "text-green-500" },
  { key: "manual", label: "Manual Upload / CSV", icon: Database, color: "text-blue-500" },
  { key: "apollo", label: "Apollo.io Extraction", icon: Target, color: "text-purple-500" },
  { key: "google_business", label: "Google Business Profiles", icon: Building2, color: "text-amber-500" },
  { key: "directory_india", label: "India Directories", icon: Globe, color: "text-orange-500" },
  { key: "directory_unknown", label: "Other Directories", icon: Globe, color: "text-teal-500" },
]

const SEQUENCE_CHANNEL_ICONS: Record<string, any> = {
  email: Mail,
  linkedin_connect: Linkedin,
  linkedin_dm: MessageCircle,
  linkedin_like: ThumbsUp,
  linkedin_comment: MessageSquare,
  call: Phone,
}

const SEQUENCE_CHANNEL_COLORS: Record<string, string> = {
  email: "text-blue-500 bg-blue-500/10",
  linkedin_connect: "text-cyan-500 bg-cyan-500/10",
  linkedin_dm: "text-cyan-600 bg-cyan-500/10",
  linkedin_like: "text-pink-500 bg-pink-500/10",
  linkedin_comment: "text-purple-500 bg-purple-500/10",
  call: "text-amber-500 bg-amber-500/10",
}

const DEFAULT_SEQUENCE = [
  { channel: "email", delay_days: 0, label: "Initial Email" },
  { channel: "linkedin_connect", delay_days: 2, label: "LinkedIn Connect" },
  { channel: "linkedin_dm", delay_days: 4, label: "LinkedIn DM" },
  { channel: "email", delay_days: 7, label: "Follow-up Email" },
  { channel: "call", delay_days: 10, label: "Phone Call" },
  { channel: "email", delay_days: 17, label: "Final Email" },
]

type ConnectionStatus = "idle" | "connecting" | "connected" | "error"

export default function SDRConfigPage() {
  const [sdrs, setSdrs] = useState<any[]>([])
  const [currentSdr, setCurrentSdr] = useState<any>(null)
  const [step, setStep] = useState(0)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [activating, setActivating] = useState(false)

  const [sequence, setSequence] = useState(DEFAULT_SEQUENCE)
  const [selectedSources, setSelectedSources] = useState<string[]>(["web_scrape", "manual"])

  // Email connection state
  const [emailProvider, setEmailProvider] = useState<"gmail" | "outlook" | "smtp">("gmail")
  const [emailStatus, setEmailStatus] = useState<ConnectionStatus>("idle")
  const [emailError, setEmailError] = useState("")
  const [emailConnecting, setEmailConnecting] = useState(false)
  const [smtpForm, setSmtpForm] = useState({
    host: "", port: 587, username: "", password: "", sender_email: "", sender_name: "",
    use_tls: true, use_ssl: false,
    imap_host: "", imap_port: 993, imap_use_ssl: true, imap_username: "", imap_password: "",
  })
  const [imapTestResult, setImapTestResult] = useState<{ success: boolean; error?: string } | null>(null)
  const [imapTesting, setImapTesting] = useState(false)

  // LinkedIn connection state
  const [liEmail, setLiEmail] = useState("")
  const [liPassword, setLiPassword] = useState("")
  const [liStatus, setLiStatus] = useState<ConnectionStatus>("idle")
  const [liConnecting, setLiConnecting] = useState(false)
  const [liError, setLiError] = useState("")

  useEffect(() => { loadSdrs() }, [])

  const loadSdrs = async () => {
    try {
      const list = await api.get<any[]>("/sdr/profiles")
      setSdrs(list)
      if (list.length > 0) {
        setCurrentSdr(list[0])
        loadSequence(list[0])
        loadCredentials(list[0])
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const loadSequence = (sdr: any) => {
    if (sdr.campaign_sequence) {
      try { setSequence(JSON.parse(sdr.campaign_sequence)) }
      catch { setSequence(DEFAULT_SEQUENCE) }
    } else setSequence(DEFAULT_SEQUENCE)

    if (sdr.lead_sources) {
      try { setSelectedSources(JSON.parse(sdr.lead_sources)) }
      catch { setSelectedSources(sdr.lead_sources.split(",").map((s: string) => s.trim()).filter(Boolean)) }
    }
  }

  const loadCredentials = (sdr: any) => {
    setEmailStatus(sdr.has_email ? "connected" : "idle")
    setLiStatus(sdr.has_linkedin ? "connected" : "idle")
    if (sdr.email_provider) setEmailProvider(sdr.email_provider as any)
    setEmailError("")
    setLiError("")
  }

  const selectSdr = (sdr: any) => {
    setCurrentSdr(sdr)
    loadSequence(sdr)
    loadCredentials(sdr)
    setStep(0)
  }

  const toggleSource = (key: string) => {
    setSelectedSources((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]
    )
  }

  const addSequenceStep = () => {
    setSequence([...sequence, { channel: "email", delay_days: 0, label: "New Step" }])
  }

  const removeSequenceStep = (i: number) => {
    setSequence(sequence.filter((_, idx) => idx !== i))
  }

  const updateSequenceStep = (i: number, field: string, value: any) => {
    const updated = [...sequence]
    ;(updated[i] as any)[field] = value
    setSequence(updated)
  }

  const moveStep = (i: number, dir: number) => {
    const j = i + dir
    if (j < 0 || j >= sequence.length) return
    const updated = [...sequence];
    [updated[i], updated[j]] = [updated[j], updated[i]]
    setSequence(updated)
  }

  const save = async () => {
    if (!currentSdr) return
    setSaving(true)
    try {
      await api.put(`/sdr/profiles/${currentSdr.id}`, {
        ...currentSdr,
        lead_sources: JSON.stringify(selectedSources),
        campaign_sequence: JSON.stringify(sequence),
      })
      loadSdrs()
      setStep(0)
    } catch (e: any) { alert(e.message) }
    finally { setSaving(false) }
  }

  const toggleActive = async () => {
    if (!currentSdr) return
    setActivating(true)
    try {
      if (currentSdr.is_active) {
        await api.post(`/sdr/profiles/${currentSdr.id}/deactivate`)
      } else {
        await api.post(`/sdr/profiles/${currentSdr.id}/activate`)
      }
      loadSdrs()
    } catch (e: any) { alert(e.message) }
    finally { setActivating(false) }
  }

  const createSdr = async () => {
    try {
      const r = await api.post<any>("/sdr/profiles", {
        name: "New AI SDR", region: "", sell_type: "product",
      })
      loadSdrs()
      selectSdr(r)
    } catch (e: any) { alert(e.message) }
  }

  const deleteSdr = async (id: string) => {
    try {
      await api.delete(`/sdr/profiles/${id}`)
      loadSdrs()
      if (currentSdr?.id === id) { setCurrentSdr(null); setStep(0) }
    } catch (e: any) { alert(e.message) }
  }

  const updateField = (field: string, value: any) => {
    setCurrentSdr((prev: any) => ({ ...prev, [field]: value }))
  }

  // ============================================================
  // CSV Upload State
  // ============================================================
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [csvUploading, setCsvUploading] = useState(false)
  const [csvResult, setCsvResult] = useState<{ imported?: number; total_in_file?: number } | null>(null)
  const [csvError, setCsvError] = useState("")

  const handleCsvUpload = async () => {
    if (!csvFile) return
    setCsvUploading(true)
    setCsvError("")
    setCsvResult(null)
    try {
      const formData = new FormData()
      formData.append("file", csvFile)
      const result = await api.post<{ imported: number; total_in_file: number }>("/leads/import/csv", formData, true)
      setCsvResult(result)
    } catch (e: any) {
      setCsvError(e.message || "CSV import failed")
    } finally {
      setCsvUploading(false)
    }
  }

  // ============================================================
  // Gmail OAuth Connection
  // ============================================================
  const connectGmail = useCallback(async () => {
    if (!currentSdr) return
    setEmailConnecting(true)
    setEmailError("")
    try {
      const { auth_url } = await api.get<{ auth_url: string }>(`/email/sdr-auth-url/${currentSdr.id}`)
      const popup = window.open(auth_url, "gmail-oauth", "width=600,height=700")
      const handler = (event: MessageEvent) => {
        if (event.data?.type === "sdr-gmail-connected" && event.data?.sdrId === currentSdr.id) {
          setEmailStatus("connected")
          setEmailConnecting(false)
          loadSdrs()
          window.removeEventListener("message", handler)
        }
      }
      window.addEventListener("message", handler)
      const checkClosed = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkClosed)
          setEmailConnecting(false)
          loadSdrs()
          window.removeEventListener("message", handler)
        }
      }, 1000)
    } catch (e: any) {
      setEmailError(e.message)
      setEmailConnecting(false)
    }
  }, [currentSdr])

  // ============================================================
  // Outlook OAuth Connection
  // ============================================================
  const connectOutlook = useCallback(async () => {
    if (!currentSdr) return
    setEmailConnecting(true)
    setEmailError("")
    try {
      const { auth_url } = await api.get<{ auth_url: string }>(`/email/sdr-outlook-auth-url/${currentSdr.id}`)
      const popup = window.open(auth_url, "outlook-oauth", "width=600,height=700")
      const handler = (event: MessageEvent) => {
        if (event.data?.type === "sdr-outlook-connected" && event.data?.sdrId === currentSdr.id) {
          setEmailStatus("connected")
          setEmailConnecting(false)
          loadSdrs()
          window.removeEventListener("message", handler)
        }
      }
      window.addEventListener("message", handler)
      const checkClosed = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkClosed)
          setEmailConnecting(false)
          loadSdrs()
          window.removeEventListener("message", handler)
        }
      }, 1000)
    } catch (e: any) {
      setEmailError(e.message)
      setEmailConnecting(false)
    }
  }, [currentSdr])

  // ============================================================
  // SMTP Connection
  // ============================================================
  const autoDetectImap = () => {
    const host = smtpForm.host
    let imap_host = host.replace("smtp.", "imap.")
    if (imap_host === host) imap_host = `imap.${host}`
    setSmtpForm(f => ({ ...f, imap_host, imap_port: 993, imap_use_ssl: true, imap_username: f.username, imap_password: f.password }))
  }

  useEffect(() => {
    if (smtpForm.host && !smtpForm.imap_host) {
      autoDetectImap()
    }
  }, [smtpForm.host])

  const testImap = async () => {
    setImapTesting(true)
    setImapTestResult(null)
    try {
      const result = await api.post<{ success: boolean; error?: string }>("/smtp/test-imap", {
        host: smtpForm.imap_host,
        port: smtpForm.imap_port,
        use_ssl: smtpForm.imap_use_ssl,
        username: smtpForm.imap_username || smtpForm.username,
        password: smtpForm.imap_password || smtpForm.password,
      })
      setImapTestResult(result)
    } catch (e: any) { setImapTestResult({ success: false, error: e.message }) }
    finally { setImapTesting(false) }
  }

  const connectSMTP = async () => {
    if (!currentSdr) return
    setEmailConnecting(true)
    setEmailError("")
    try {
      await api.put(`/sdr/profiles/${currentSdr.id}/email-creds`, {
        provider: "smtp", ...smtpForm,
      })
      setEmailStatus("connected")
      loadSdrs()
    } catch (e: any) { setEmailError(e.message) }
    finally { setEmailConnecting(false) }
  }

  // ============================================================
  // LinkedIn Connection
  // ============================================================
  const connectLinkedIn = async () => {
    if (!currentSdr) return
    setLiConnecting(true)
    setLiError("")
    try {
      await api.put(`/sdr/profiles/${currentSdr.id}/linkedin-creds`, {
        email: liEmail, password: liPassword,
      })
      setLiStatus("connected")
      loadSdrs()
    } catch (e: any) { setLiError(e.message) }
    finally { setLiConnecting(false) }
  }

  const testLinkedIn = async () => {
    if (!currentSdr) return
    setLiConnecting(true)
    setLiError("")
    try {
      const result = await api.post<{ status: string }>(`/sdr/profiles/${currentSdr.id}/test-linkedin`)
      setLiStatus(result.status === "connected" ? "connected" : "error")
      if (result.status !== "connected") setLiError("Login failed - check credentials")
    } catch (e: any) { setLiError(e.message) }
    finally { setLiConnecting(false) }
  }

  const disconnectEmail = async () => {
    if (!currentSdr) return
    await api.delete(`/sdr/profiles/${currentSdr.id}/email-creds`)
    setEmailStatus("idle")
    setEmailError("")
    loadSdrs()
  }

  const disconnectLinkedIn = async () => {
    if (!currentSdr) return
    await api.delete(`/sdr/profiles/${currentSdr.id}/linkedin-creds`)
    setLiStatus("idle")
    setLiError("")
    loadSdrs()
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading...</div>
  }

  const steps = ["SDR Identity", "Connect Accounts", "Lead Sources", "Auto-Scrape", "Campaign Sequence", "ICP & Settings"]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bot size={28} className="text-purple-400" />
          <h1 className="text-2xl font-semibold">AI SDR Configuration</h1>
        </div>
        <button onClick={createSdr} className="btn-secondary text-sm flex items-center gap-1"><Plus size={14} /> New SDR</button>
      </div>

      {/* SDR Selector */}
      {sdrs.length > 0 && (
        <div className="glass rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Bookmark size={16} className="text-purple-400" />
            <h3 className="font-medium text-sm text-white">Your AI SDRs</h3>
            <span className="text-xs text-gray-400">({sdrs.length} total)</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {sdrs.map((s) => (
              <div key={s.id} className="flex items-center gap-1">
                <button onClick={() => selectSdr(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                    currentSdr?.id === s.id
                      ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20"
                      : "bg-white/5 text-gray-400 hover:text-white hover:bg-white/10"
                  }`}>
                  <Bot size={12} />
                  {s.name || "AI SDR"}
                  {s.is_active && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_hsl(160,84%,50%)]" />}
                  {s.region && <span className="text-[10px] opacity-70 ml-0.5">({s.region})</span>}
                </button>
                <button onClick={() => deleteSdr(s.id)} className="p-1 text-gray-500 hover:text-red-400 transition-colors">
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
          {currentSdr && (
            <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
              <span>Email: {currentSdr.has_email ? <span className="text-emerald-400">{currentSdr.email_sender || "Connected"}</span> : <span className="text-amber-400">Not set</span>}</span>
              <span>LinkedIn: {currentSdr.has_linkedin ? <span className="text-emerald-400">Connected</span> : <span className="text-amber-400">Not set</span>}</span>
            </div>
          )}
        </div>
      )}

      {/* Main Config Area */}
      {currentSdr && (
        <div className="glass rounded-2xl p-6">
          {/* Progress Steps */}
          <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-2">
            {steps.map((s, i) => (
              <button key={i} onClick={() => setStep(i)} className="flex items-center gap-1 shrink-0">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-all ${
                  i === step ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20" :
                  i < step ? "bg-emerald-600 text-white" : "bg-white/5 text-gray-500"
                }`}>
                  {i < step ? <Check size={14} /> : i + 1}
                </div>
                <span className={`text-xs mr-2 whitespace-nowrap ${
                  i === step ? "text-white font-medium" : "text-gray-500"
                }`}>{s}</span>
                {i < steps.length - 1 && <ChevronRight size={12} className="text-gray-600 shrink-0" />}
              </button>
            ))}
          </div>

          {/* Step 0: SDR Identity */}
          {step === 0 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-white">SDR Identity</h3>
              <p className="text-sm text-gray-400">Name and region for this SDR. Create multiple SDRs for different regions or campaigns.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">SDR Name</label>
                  <input type="text" value={currentSdr.name || ""} onChange={(e) => updateField("name", e.target.value)}
                    className="input" placeholder="e.g. US Sales Bot, India Outreach SDR" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Region / Territory</label>
                  <input type="text" value={currentSdr.region || ""} onChange={(e) => updateField("region", e.target.value)}
                    className="input" placeholder="e.g. North America, India, Europe" />
                </div>
              </div>
            </div>
          )}

          {/* Step 1: Connect Accounts (NEW) */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-white mb-1">Connect Accounts</h3>
                <p className="text-sm text-gray-400">Each SDR gets its own email and LinkedIn accounts for outreach.</p>
              </div>

              {/* Email Connection */}
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${emailStatus === "connected" ? "bg-emerald-500/10" : "bg-purple-500/10"} border border-white/10`}>
                      <Mail size={20} className={emailStatus === "connected" ? "text-emerald-400" : "text-purple-400"} />
                    </div>
                    <div>
                      <h4 className="font-medium text-white text-sm">Email Outbound</h4>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {emailStatus === "connected"
                          ? `Connected via ${currentSdr?.email_provider === "gmail" ? "Gmail" : currentSdr?.email_provider === "outlook" ? "Outlook" : "SMTP"} — ${currentSdr?.email_sender || ""}`
                          : "Connect a mailbox for this SDR to send emails"}
                      </p>
                    </div>
                  </div>
                  {emailStatus === "connected" && (
                    <button onClick={disconnectEmail} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition-colors">
                      <Unlink size={12} /> Disconnect
                    </button>
                  )}
                </div>

                {emailStatus !== "connected" && (
                  <div className="space-y-4">
                    {/* Provider Toggle */}
                    <div className="flex gap-2">
                      <button onClick={() => setEmailProvider("gmail")}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                          emailProvider === "gmail"
                            ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20"
                            : "bg-white/5 text-gray-400 hover:text-white"
                        }`}>
                        <ExternalLink size={14} /> Gmail OAuth
                      </button>
                      <button onClick={() => setEmailProvider("outlook")}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                          emailProvider === "outlook"
                            ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20"
                            : "bg-white/5 text-gray-400 hover:text-white"
                        }`}>
                        <ExternalLink size={14} /> Outlook OAuth
                      </button>
                      <button onClick={() => setEmailProvider("smtp")}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition-all ${
                          emailProvider === "smtp"
                            ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20"
                            : "bg-white/5 text-gray-400 hover:text-white"
                        }`}>
                        <Server size={14} /> SMTP
                      </button>
                    </div>

                    {/* Gmail OAuth */}
                    {emailProvider === "gmail" && (
                      <div className="space-y-3">
                        <p className="text-xs text-gray-400">
                          Authenticate with Google. You need Gmail API credentials configured in Admin &gt; Integrations first.
                        </p>
                        <button onClick={connectGmail} disabled={emailConnecting}
                          className="btn-primary text-sm flex items-center gap-2">
                          {emailConnecting ? (
                            <><Loader size={14} className="animate-spin" /> Connecting...</>
                          ) : (
                            <><ExternalLink size={14} /> Connect Gmail via OAuth</>
                          )}
                        </button>
                      </div>
                    )}

                    {/* Outlook OAuth */}
                    {emailProvider === "outlook" && (
                      <div className="space-y-3">
                        <p className="text-xs text-gray-400">
                          Authenticate with Microsoft. You need Outlook API credentials configured in Admin &gt; Integrations first.
                        </p>
                        <button onClick={connectOutlook} disabled={emailConnecting}
                          className="btn-primary text-sm flex items-center gap-2">
                          {emailConnecting ? (
                            <><Loader size={14} className="animate-spin" /> Connecting...</>
                          ) : (
                            <><ExternalLink size={14} /> Connect Outlook via OAuth</>
                          )}
                        </button>
                      </div>
                    )}

                    {/* SMTP */}
                    {emailProvider === "smtp" && (
                      <div className="space-y-4">
                        <div className="text-xs text-gray-400 bg-white/[0.03] rounded-xl p-3 border border-white/5">
                          <strong className="text-yellow-400">Reply Detection:</strong> SMTP only sends emails. To detect replies,
                          configure IMAP inbox access below. IMAP settings are auto-detected from your SMTP host.
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <label className="text-xs text-gray-400 block mb-1">SMTP Host</label>
                            <input type="text" value={smtpForm.host} onChange={(e) => setSmtpForm(f => ({...f, host: e.target.value}))}
                              className="input" placeholder="smtp.hostinger.com" />
                          </div>
                          <div>
                            <label className="text-xs text-gray-400 block mb-1">Port</label>
                            <input type="number" value={smtpForm.port} onChange={(e) => setSmtpForm(f => ({...f, port: parseInt(e.target.value)}))}
                              className="input" placeholder="587" />
                          </div>
                          <div>
                            <label className="text-xs text-gray-400 block mb-1">Username</label>
                            <input type="text" value={smtpForm.username} onChange={(e) => setSmtpForm(f => ({...f, username: e.target.value}))}
                              className="input" placeholder="hello@offdx.in" />
                          </div>
                          <div>
                            <label className="text-xs text-gray-400 block mb-1">Password</label>
                            <input type="password" value={smtpForm.password} onChange={(e) => setSmtpForm(f => ({...f, password: e.target.value}))}
                              className="input" placeholder="••••••••" />
                          </div>
                          <div>
                            <label className="text-xs text-gray-400 block mb-1">Sender Email</label>
                            <input type="email" value={smtpForm.sender_email} onChange={(e) => setSmtpForm(f => ({...f, sender_email: e.target.value}))}
                              className="input" placeholder="hello@offdx.in" />
                          </div>
                          <div>
                            <label className="text-xs text-gray-400 block mb-1">Sender Name</label>
                            <input type="text" value={smtpForm.sender_name} onChange={(e) => setSmtpForm(f => ({...f, sender_name: e.target.value}))}
                              className="input" placeholder="AI SDR" />
                          </div>
                        </div>

                        {/* IMAP Section */}
                        <details className="rounded-xl border border-white/10 bg-white/[0.02]">
                          <summary className="px-4 py-3 text-xs font-medium text-gray-300 cursor-pointer hover:text-white transition-colors flex items-center gap-2">
                            <Mail size={14} /> IMAP Inbox (for reply detection)
                          </summary>
                          <div className="px-4 pb-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                              <label className="text-xs text-gray-400 block mb-1">IMAP Host</label>
                              <input type="text" value={smtpForm.imap_host}
                                onChange={(e) => setSmtpForm(f => ({...f, imap_host: e.target.value}))}
                                className="input" placeholder="imap.hostinger.com" />
                            </div>
                            <div>
                              <label className="text-xs text-gray-400 block mb-1">IMAP Port</label>
                              <input type="number" value={smtpForm.imap_port}
                                onChange={(e) => setSmtpForm(f => ({...f, imap_port: parseInt(e.target.value)}))}
                                className="input" placeholder="993" />
                            </div>
                            <div>
                              <label className="text-xs text-gray-400 block mb-1">IMAP Username</label>
                              <input type="text" value={smtpForm.imap_username}
                                onChange={(e) => setSmtpForm(f => ({...f, imap_username: e.target.value}))}
                                className="input" placeholder="Same as SMTP if empty" />
                            </div>
                            <div>
                              <label className="text-xs text-gray-400 block mb-1">IMAP Password</label>
                              <input type="password" value={smtpForm.imap_password}
                                onChange={(e) => setSmtpForm(f => ({...f, imap_password: e.target.value}))}
                                className="input" placeholder="Same as SMTP if empty" />
                            </div>
                            <div>
                              <label className="text-xs text-gray-400 block mb-1">Use SSL</label>
                              <select value={smtpForm.imap_use_ssl ? "true" : "false"}
                                onChange={(e) => setSmtpForm(f => ({...f, imap_use_ssl: e.target.value === "true"}))}
                                className="input">
                                <option value="true">Yes (port 993)</option>
                                <option value="false">No (port 143)</option>
                              </select>
                            </div>
                            <div className="flex items-end gap-2">
                              <button onClick={autoDetectImap}
                                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-all">
                                <RefreshCw size={12} /> Auto-Detect
                              </button>
                              <button onClick={testImap} disabled={imapTesting}
                                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 transition-all">
                                {imapTesting ? <Loader size={12} className="animate-spin" /> : <TestTube size={12} />}
                                {imapTesting ? "Testing..." : "Test IMAP"}
                              </button>
                            </div>
                            {imapTestResult && (
                              <div className={`md:col-span-2 flex items-center gap-2 p-3 rounded-xl text-xs ${
                                imapTestResult.success
                                  ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                                  : "bg-red-500/10 border border-red-500/20 text-red-400"
                              }`}>
                                {imapTestResult.success ? <CheckCircle size={14} /> : <XCircle size={14} />}
                                {imapTestResult.success ? "IMAP connection successful!" : imapTestResult.error}
                              </div>
                            )}
                          </div>
                        </details>

                        <button onClick={connectSMTP} disabled={emailConnecting}
                          className="btn-primary text-sm flex items-center gap-2">
                          {emailConnecting ? <><Loader size={14} className="animate-spin" /> Saving...</> : <><Save size={14} /> Save SMTP Config</>}
                        </button>
                      </div>
                    )}

                    {emailError && (
                      <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                        <AlertCircle size={14} /> {emailError}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* LinkedIn Connection */}
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${liStatus === "connected" ? "bg-emerald-500/10" : "bg-blue-500/10"} border border-white/10`}>
                      <Linkedin size={20} className={liStatus === "connected" ? "text-emerald-400" : "text-blue-400"} />
                    </div>
                    <div>
                      <h4 className="font-medium text-white text-sm">LinkedIn Account</h4>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {liStatus === "connected"
                          ? `Connected — ${currentSdr?.has_linkedin ? liEmail || "LinkedIn account active" : ""}`
                          : "Connect a LinkedIn account for this SDR"}
                      </p>
                    </div>
                  </div>
                  {liStatus === "connected" && (
                    <button onClick={disconnectLinkedIn} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition-colors">
                      <Unlink size={12} /> Disconnect
                    </button>
                  )}
                </div>

                {liStatus !== "connected" && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">LinkedIn Email</label>
                        <input type="email" value={liEmail} onChange={(e) => setLiEmail(e.target.value)}
                          className="input" placeholder="linkedin-account@email.com" />
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">LinkedIn Password</label>
                        <input type="password" value={liPassword} onChange={(e) => setLiPassword(e.target.value)}
                          className="input" placeholder="••••••••" />
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <button onClick={connectLinkedIn} disabled={liConnecting}
                        className="btn-primary text-sm flex items-center gap-2">
                        {liConnecting ? <><Loader size={14} className="animate-spin" /> Saving...</> : <><Save size={14} /> Save LinkedIn Account</>}
                      </button>
                    </div>

                    <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-500/5 border border-amber-500/10">
                      <AlertCircle size={14} className="text-amber-400 mt-0.5 shrink-0" />
                      <p className="text-xs text-amber-400">LinkedIn automation may violate their ToS. Credentials are encrypted and only used for browser automation.</p>
                    </div>

                    {liError && (
                      <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                        <AlertCircle size={14} /> {liError}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Lead Sources */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-white">Lead Sources</h3>
                  <p className="text-sm text-gray-400">Select which lead sources this SDR should work on. Combined sources feed into one campaign.</p>
                </div>
                <span className="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded">
                  {selectedSources.length} source{selectedSources.length !== 1 ? "s" : ""} selected
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {LEAD_SOURCES.map((src) => {
                  const Icon = src.icon
                  const isSelected = selectedSources.includes(src.key)
                  return (
                    <label key={src.key} className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                      isSelected ? "border-purple-500/30 bg-purple-500/5" : "border-white/10 bg-white/[0.02] hover:bg-white/[0.04]"
                    }`}>
                      <input type="checkbox" checked={isSelected} onChange={() => toggleSource(src.key)} className="sr-only" />
                      <Icon size={20} className={src.color} />
                      <div className="flex-1">
                        <span className="text-sm font-medium text-white">{src.label}</span>
                      </div>
                      {isSelected && <Check size={16} className="text-purple-400" />}
                    </label>
                  )
                })}
              </div>

              {/* CSV Upload — shown when Manual Upload is selected */}
              {selectedSources.includes("manual") && (
                <div className="mt-4 p-4 rounded-xl border border-blue-500/20 bg-blue-500/5">
                  <div className="flex items-center gap-2 mb-3">
                    <Upload size={16} className="text-blue-400" />
                    <h4 className="text-sm font-medium text-white">Upload Leads via CSV</h4>
                  </div>
                  <p className="text-xs text-gray-400 mb-3">
                    Upload a CSV file with your leads. <a href={`${API_BASE}/leads/sample-csv`}
                    className="text-blue-400 hover:underline inline-flex items-center gap-1"
                    target="_blank" rel="noopener noreferrer">
                      <Download size={12} /> Download sample CSV
                    </a>
                  </p>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 cursor-pointer text-sm text-gray-300">
                      <FileText size={14} />
                      {csvFile ? csvFile.name : "Choose CSV file"}
                      <input type="file" accept=".csv" className="hidden" onChange={(e) => {
                        setCsvFile(e.target.files?.[0] || null)
                        setCsvResult(null)
                        setCsvError("")
                      }} />
                    </label>
                    <button onClick={handleCsvUpload} disabled={!csvFile || csvUploading}
                      className="btn-primary text-sm flex items-center gap-1 disabled:opacity-50">
                      {csvUploading ? <Loader size={14} className="animate-spin" /> : <Upload size={14} />}
                      {csvUploading ? "Uploading..." : "Upload & Import"}
                    </button>
                  </div>

                  {csvResult && (
                    <div className="mt-3 flex items-center gap-2 p-2 rounded bg-emerald-500/10 text-emerald-400 text-xs">
                      <CheckCircle size={14} />
                      Imported {csvResult.imported ?? 0} of {csvResult.total_in_file ?? 0} leads
                      {(csvResult.total_in_file ?? 0) > (csvResult.imported ?? 0) && ` (${(csvResult.total_in_file ?? 0) - (csvResult.imported ?? 0)} duplicates skipped)`}
                    </div>
                  )}

                  {csvError && (
                    <div className="mt-3 flex items-center gap-2 p-2 rounded bg-red-500/10 text-red-400 text-xs">
                      <AlertCircle size={14} /> {csvError}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step 3: Auto-Scrape */}
          {step === 3 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-white">Auto-Scrape Configuration</h3>
              <p className="text-sm text-gray-400">Automatically scrape leads when SDR is activated.</p>
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" checked={currentSdr.auto_scrape_enabled} onChange={(e) => updateField("auto_scrape_enabled", e.target.checked)}
                  className="w-4 h-4 rounded border-gray-600 text-purple-600 bg-white/5" />
                <div>
                  <span className="font-medium text-sm text-white">Enable Auto-Scrape on Activation</span>
                  <p className="text-xs text-gray-400">Automatically scrape leads when SDR is activated</p>
                </div>
              </label>

              {currentSdr.auto_scrape_enabled && (
                <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] space-y-3">
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Business Category</label>
                    <input type="text" value={currentSdr.scrape_business_category || ""} onChange={(e) => updateField("scrape_business_category", e.target.value)}
                      className="input" placeholder="e.g. IT & Technology, Home Services" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Country</label>
                    <input type="text" value={currentSdr.scrape_country || ""} onChange={(e) => updateField("scrape_country", e.target.value)}
                      className="input" placeholder="e.g. India, United States" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Directory URLs (one per line)</label>
                    <textarea value={currentSdr.scrape_directory_urls || ""} onChange={(e) => updateField("scrape_directory_urls", e.target.value)}
                      rows={3} className="input resize-none font-mono" placeholder={"https://www.indiamart.com/\nhttps://www.justdial.com/"} />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Web Scrape Targets</label>
                    <textarea value={currentSdr.web_scrape_targets || ""} onChange={(e) => updateField("web_scrape_targets", e.target.value)}
                      rows={2} className="input resize-none" placeholder={"company1.com\ncompany2.com"} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Campaign Sequence */}
          {step === 4 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-white">Campaign Sequence</h3>
                  <p className="text-sm text-gray-400">Design the multi-step outreach sequence.</p>
                </div>
                <button onClick={addSequenceStep} className="btn-secondary text-xs flex items-center gap-1"><Plus size={12} /> Add Step</button>
              </div>

              <div className="space-y-2">
                {sequence.length === 0 && (
                  <div className="p-8 text-center text-gray-500 text-sm">No steps defined.</div>
                )}
                {sequence.map((s: any, i: number) => {
                  const Icon = SEQUENCE_CHANNEL_ICONS[s.channel] || Mail
                  const colorClass = SEQUENCE_CHANNEL_COLORS[s.channel] || "text-gray-500 bg-gray-500/10"
                  return (
                    <div key={i} className="flex items-center gap-3 p-3 rounded-xl border border-white/10 bg-white/[0.02]">
                      <div className="w-7 h-7 rounded-full bg-purple-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
                        {i + 1}
                      </div>
                      <div className="flex items-center gap-2 min-w-[140px]">
                        <div className={`p-1.5 rounded ${colorClass}`}><Icon size={14} /></div>
                        <select value={s.channel} onChange={(e) => updateSequenceStep(i, "channel", e.target.value)}
                          className="text-xs px-2 py-1 rounded border border-white/10 bg-white/5 text-white">
                          <option value="email">Email</option>
                          <option value="linkedin_connect">LinkedIn Connect</option>
                          <option value="linkedin_dm">LinkedIn DM</option>
                          <option value="linkedin_like">LinkedIn Like</option>
                          <option value="linkedin_comment">LinkedIn Comment</option>
                          <option value="call">Phone Call</option>
                        </select>
                      </div>
                      <input type="text" value={s.label || ""} onChange={(e) => updateSequenceStep(i, "label", e.target.value)}
                        className="flex-1 px-2 py-1 rounded border border-white/10 bg-transparent text-xs text-white" placeholder="Label" />
                      <div className="flex items-center gap-1 min-w-[100px]">
                        <Clock size={12} className="text-gray-500" />
                        <input type="number" min={0} value={s.delay_days} onChange={(e) => updateSequenceStep(i, "delay_days", parseInt(e.target.value) || 0)}
                          className="w-12 px-1 py-1 rounded border border-white/10 bg-transparent text-xs text-white text-center" />
                        <span className="text-xs text-gray-500">days</span>
                      </div>
                      <div className="flex items-center gap-0.5">
                        {i > 0 && <button onClick={() => moveStep(i, -1)} className="p-0.5 text-gray-500 hover:text-white"><ChevronLeft size={12} /></button>}
                        {i < sequence.length - 1 && <button onClick={() => moveStep(i, 1)} className="p-0.5 text-gray-500 hover:text-white"><ChevronRight size={12} /></button>}
                      </div>
                      <button onClick={() => removeSequenceStep(i)} className="p-1 text-gray-500 hover:text-red-400"><Trash2 size={12} /></button>
                    </div>
                  )
                })}
              </div>

              {sequence.length > 0 && (
                <div className="p-4 rounded-xl bg-gradient-to-r from-purple-500/5 to-blue-500/5 border border-purple-500/20">
                  <h4 className="text-xs font-medium text-gray-300 mb-3">Timeline Preview</h4>
                  <div className="flex items-start gap-1 overflow-x-auto pb-2">
                    {sequence.map((s: any, i: number) => {
                      const Icon = SEQUENCE_CHANNEL_ICONS[s.channel] || Mail
                      const colorClass = SEQUENCE_CHANNEL_COLORS[s.channel] || "text-gray-500"
                      const totalDays = sequence.slice(0, i + 1).reduce((sum: number, st: any) => sum + (st.delay_days || 0), 0)
                      return (
                        <div key={i} className="flex items-center shrink-0">
                          <div className="flex flex-col items-center min-w-[80px]">
                            <div className={`p-2 rounded-full ${colorClass} border-2 border-[hsl(224,45%,7%)]`}>
                              <Icon size={16} />
                            </div>
                            <span className="text-[10px] mt-1 font-medium text-gray-300 text-center">{s.label || s.channel}</span>
                            <span className="text-[9px] text-gray-500">Day {totalDays}</span>
                          </div>
                          {i < sequence.length - 1 && (
                            <div className="flex items-center mx-1">
                              <div className="h-0.5 w-6 bg-gray-600" />
                              <ArrowRight size={10} className="text-gray-600 -ml-1" />
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 5: ICP & Settings */}
          {step === 5 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-white">ICP & Outreach Settings</h3>
              <p className="text-sm text-gray-400">Configure Ideal Customer Profile and source-specific settings.</p>

              {/* Active lead sources indicator */}
              <div className="flex flex-wrap gap-1.5 mb-2">
                {selectedSources.map((src) => {
                  const s = LEAD_SOURCES.find((ls) => ls.key === src)
                  if (!s) return null
                  const Icon = s.icon
                  return (
                    <span key={src} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-white/5 text-gray-300 border border-white/10">
                      <Icon size={10} className={s.color} /> {s.label}
                    </span>
                  )
                })}
              </div>

              {/* Source-specific configs */}
              {selectedSources.includes("web_scrape") && (
                <div className="p-4 rounded-xl border border-green-500/20 bg-green-500/5">
                  <h4 className="text-sm font-medium text-white flex items-center gap-2 mb-2">
                    <Globe size={14} className="text-green-400" /> Web Scrape Config
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="md:col-span-2">
                      <label className="text-xs text-gray-400 block mb-1">Target Websites (one per line)</label>
                      <textarea value={currentSdr.web_scrape_targets || ""} onChange={(e) => updateField("web_scrape_targets", e.target.value)}
                        rows={2} className="input resize-none font-mono" placeholder={"acmecorp.com\nexample.com"} />
                    </div>
                  </div>
                </div>
              )}

              {selectedSources.includes("apollo") && (
                <div className="p-4 rounded-xl border border-purple-500/20 bg-purple-500/5">
                  <h4 className="text-sm font-medium text-white flex items-center gap-2 mb-2">
                    <Target size={14} className="text-purple-400" /> Apollo.io Search Criteria
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Target Titles</label>
                      <input type="text" value={currentSdr.target_titles || ""} onChange={(e) => updateField("target_titles", e.target.value)}
                        className="input" placeholder="CTO, VP Engineering, CEO" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Target Locations</label>
                      <input type="text" value={currentSdr.target_locations || ""} onChange={(e) => updateField("target_locations", e.target.value)}
                        className="input" placeholder="Bangalore, New York, London" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Target Industries</label>
                      <input type="text" value={currentSdr.target_industries || ""} onChange={(e) => updateField("target_industries", e.target.value)}
                        className="input" placeholder="Technology, Healthcare, Finance" />
                    </div>
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <label className="text-xs text-gray-400 block mb-1">Min Company Size</label>
                        <input type="number" value={currentSdr.target_company_size_min || ""} onChange={(e) => updateField("target_company_size_min", e.target.value ? parseInt(e.target.value) : null)}
                          className="input" placeholder="10" />
                      </div>
                      <div className="flex-1">
                        <label className="text-xs text-gray-400 block mb-1">Max Company Size</label>
                        <input type="number" value={currentSdr.target_company_size_max || ""} onChange={(e) => updateField("target_company_size_max", e.target.value ? parseInt(e.target.value) : null)}
                          className="input" placeholder="500" />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {selectedSources.includes("google_business") && (
                <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5">
                  <h4 className="text-sm font-medium text-white flex items-center gap-2 mb-2">
                    <MapPin size={14} className="text-amber-400" /> Google Business Profiles Config
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Location / City</label>
                      <input type="text" value={currentSdr.scrape_country || ""} onChange={(e) => updateField("scrape_country", e.target.value)}
                        className="input" placeholder="Bangalore, India" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Business Category</label>
                      <input type="text" value={currentSdr.scrape_business_category || ""} onChange={(e) => updateField("scrape_business_category", e.target.value)}
                        className="input" placeholder="IT Services, Restaurants, etc." />
                    </div>
                  </div>
                </div>
              )}

              {selectedSources.some((s) => s.startsWith("directory")) && (
                <div className="p-4 rounded-xl border border-orange-500/20 bg-orange-500/5">
                  <h4 className="text-sm font-medium text-white flex items-center gap-2 mb-2">
                    <Globe size={14} className="text-orange-400" /> Directory Scraping Config
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="md:col-span-2">
                      <label className="text-xs text-gray-400 block mb-1">Directory URLs (one per line)</label>
                      <textarea value={currentSdr.scrape_directory_urls || ""} onChange={(e) => updateField("scrape_directory_urls", e.target.value)}
                        rows={2} className="input resize-none font-mono" placeholder={"https://www.indiamart.com/search?q=it+services\nhttps://www.justdial.com/"} />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Business Category</label>
                      <input type="text" value={currentSdr.scrape_business_category || ""} onChange={(e) => updateField("scrape_business_category", e.target.value)}
                        className="input" placeholder="IT & Technology" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400 block mb-1">Country</label>
                      <input type="text" value={currentSdr.scrape_country || ""} onChange={(e) => updateField("scrape_country", e.target.value)}
                        className="input" placeholder="India" />
                    </div>
                  </div>
                </div>
              )}

              {/* Universal ICP fields */}
              <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02]">
                <h4 className="text-sm font-medium text-white mb-3">Universal ICP Filters</h4>
                <p className="text-xs text-gray-400 mb-3">These filters apply across ALL selected sources.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Outreach Tone</label>
                    <select value={currentSdr.outreach_tone || "professional"} onChange={(e) => updateField("outreach_tone", e.target.value)}
                      className="input">
                      <option value="professional">Professional</option>
                      <option value="friendly">Friendly</option>
                      <option value="direct">Direct</option>
                      <option value="casual">Casual</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">SDR Personality</label>
                    <input type="text" value={currentSdr.sdr_personality || ""} onChange={(e) => updateField("sdr_personality", e.target.value)}
                      className="input" placeholder="e.g. Friendly but professional" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Lead Target</label>
                    <input type="number" value={currentSdr.leads_target || 100} onChange={(e) => updateField("leads_target", parseInt(e.target.value) || 100)}
                      className="input" />
                  </div>
                </div>
              </div>

              <div className="border-t border-white/10 pt-4">
                <h4 className="text-sm font-medium text-white mb-3">Daily Rate Limits</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { key: "max_daily_emails", label: "Max Emails/Day" },
                    { key: "max_daily_calls", label: "Max Calls/Day" },
                    { key: "max_daily_linkedin", label: "Max LinkedIn/Day" },
                    { key: "max_daily_likes", label: "Max Likes/Day" },
                  ].map((item) => (
                    <div key={item.key}>
                      <label className="text-xs text-gray-400 block mb-1">{item.label}</label>
                      <input type="number" value={(currentSdr as any)[item.key] || 0} onChange={(e) => updateField(item.key, parseInt(e.target.value) || 0)}
                        className="input" />
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t border-white/10 pt-4">
                <h4 className="text-sm font-medium text-white mb-3">LinkedIn Engagement</h4>
                <div className="space-y-2">
                  {[
                    { key: "linkedin_connect_enabled", label: "Connection Requests" },
                    { key: "linkedin_dm_enabled", label: "Direct Messages" },
                    { key: "linkedin_like_enabled", label: "Likes" },
                    { key: "linkedin_comment_enabled", label: "Comments" },
                  ].map((item) => (
                    <label key={item.key} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={(currentSdr as any)[item.key]} onChange={(e) => updateField(item.key, e.target.checked)}
                        className="w-4 h-4 rounded border-gray-600 text-purple-600 bg-white/5" />
                      <span className="text-sm text-gray-300">{item.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Navigation & Save */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
            <div className="flex gap-2">
              <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}
                className="btn-ghost text-sm flex items-center gap-1 disabled:opacity-50">
                <ChevronLeft size={14} /> Previous
              </button>
              <button onClick={() => setStep(Math.min(steps.length - 1, step + 1))} disabled={step === steps.length - 1}
                className="btn-ghost text-sm flex items-center gap-1 disabled:opacity-50">
                Next <ChevronRight size={14} />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={save} disabled={saving} className="btn-primary text-sm flex items-center gap-1">
                {saving ? <Loader size={14} className="animate-spin" /> : <Save size={14} />}
                Save Config
              </button>
              <button onClick={toggleActive} disabled={activating}
                className={`text-sm flex items-center gap-1 px-4 py-2 rounded-xl font-medium transition-all ${
                  currentSdr.is_active
                    ? "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20"
                    : "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20"
                }`}>
                {activating ? <Loader size={14} className="animate-spin" /> : currentSdr.is_active ? <Square size={14} /> : <Play size={14} />}
                {currentSdr.is_active ? "Deactivate" : "Activate"}
              </button>
            </div>
          </div>
        </div>
      )}

      {!currentSdr && sdrs.length === 0 && (
        <div className="glass rounded-2xl p-12 text-center">
          <Bot size={48} className="mx-auto text-gray-500 mb-4" />
          <h2 className="text-lg font-semibold text-white mb-2">No AI SDRs Yet</h2>
          <p className="text-sm text-gray-400 mb-4">Create your first AI SDR with its own email + LinkedIn.</p>
          <button onClick={createSdr} className="btn-primary"><Plus size={16} /> Create Your First SDR</button>
        </div>
      )}
    </div>
  )
}
