"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api-client"
import {
  Bot, ArrowLeft, Check, ChevronRight, Mail, Linkedin,
  Globe, Target, Users, Sparkles, Save, Play, RefreshCw,
  AlertCircle, Plus, X, Clock, Phone, Upload, FileText,
  Download, Key, Building2, CheckCircle, Eye, EyeOff, ExternalLink,
} from "lucide-react"

const STEPS = [
  { key: "identity", label: "Identity", icon: Bot, description: "Name and region" },
  { key: "connect", label: "Connect Accounts", icon: Mail, description: "Link email & LinkedIn" },
  { key: "sources", label: "Lead Sources", icon: Globe, description: "Import or scrape leads" },
  { key: "settings", label: "Settings", icon: Target, description: "Tone, limits & targeting" },
  { key: "review", label: "Review & Launch", icon: Sparkles, description: "Final checks" },
]

const LEAD_SOURCE_OPTIONS = [
  { key: "manual", label: "Manual Upload / CSV", icon: Users, color: "text-blue-500", desc: "Upload your own lead list" },
  { key: "web_scrape", label: "Web Scraped Leads", icon: Globe, color: "text-green-500", desc: "Scrape from directories" },
  { key: "apollo", label: "Apollo.io", icon: Target, color: "text-purple-500", desc: "B2B lead database" },
]

interface SetupForm {
  name: string
  region: string
  sell_type: string
  product_name: string
  product_description: string
  service_description: string
  target_titles: string
  target_industries: string
  target_locations: string
  outreach_tone: string
  sdr_personality: string
  max_daily_emails: number
  max_daily_linkedin: number
  max_daily_calls: number
  leads_target: number
}

export default function SDRSetupPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [saving, setSaving] = useState(false)
  const [sdrId, setSdrId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [form, setForm] = useState<SetupForm>({
    name: "AI SDR", region: "",
    sell_type: "product", product_name: "", product_description: "",
    service_description: "",
    target_titles: "", target_industries: "", target_locations: "",
    outreach_tone: "professional", sdr_personality: "",
    max_daily_emails: 20, max_daily_linkedin: 15, max_daily_calls: 10, leads_target: 100,
  })

  const [leadSources, setLeadSources] = useState<string[]>([])
  const [hasEmail, setHasEmail] = useState(false)
  const [hasLinkedin, setHasLinkedin] = useState(false)

  // Email connection state
  const [emailMethod, setEmailMethod] = useState<"oauth" | "smtp" | null>(null)
  const [smtpForm, setSmtpForm] = useState({
    host: "", port: 587, username: "", password: "",
    sender_email: "", sender_name: "",
    imap_host: "", imap_port: 993, imap_use_ssl: true,
    imap_username: "", imap_password: "",
  })
  const [showPwd, setShowPwd] = useState(false)

  // CSV upload state
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [listName, setListName] = useState("")
  const [csvUploading, setCsvUploading] = useState(false)
  const [csvResult, setCsvResult] = useState<{ imported: number } | null>(null)

  // Google My Business state
  const [gmbEnabled, setGmbEnabled] = useState(false)
  const [gmbCategory, setGmbCategory] = useState("")
  const [gmbLocation, setGmbLocation] = useState("")

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const editId = params.get("edit")
    if (editId) {
      setSdrId(editId)
      loadExisting(editId)
    }
  }, [])

  const loadExisting = async (id: string) => {
    try {
      const sdr = await api.get<any>(`/sdr/profiles/${id}`)
      setForm({
        name: sdr.name || "AI SDR", region: sdr.region || "",
        sell_type: sdr.sell_type || "product",
        product_name: sdr.product_name || "", product_description: sdr.product_description || "",
        service_description: sdr.service_description || "",
        target_titles: sdr.target_titles || "", target_industries: sdr.target_industries || "",
        target_locations: sdr.target_locations || "",
        outreach_tone: sdr.outreach_tone || "professional",
        sdr_personality: sdr.sdr_personality || "",
        max_daily_emails: sdr.max_daily_emails || 20,
        max_daily_linkedin: sdr.max_daily_linkedin || 15,
        max_daily_calls: sdr.max_daily_calls || 10,
        leads_target: sdr.leads_target || 100,
      })
      if (sdr.lead_sources) {
        setLeadSources(sdr.lead_sources.split(",").filter(Boolean))
      }
      setHasEmail(sdr.has_email)
      setHasLinkedin(sdr.has_linkedin)
    } catch {}
  }

  const updateField = (key: string, val: any) => setForm((f) => ({ ...f, [key]: val }))

  const isManual = leadSources.includes("manual")

  const toggleSource = (key: string) => {
    setLeadSources((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]
    )
    if (key !== "manual") setCsvResult(null)
  }

  const handleCsvUpload = async () => {
    if (!csvFile || !listName.trim()) return
    setCsvUploading(true)
    try {
      const formData = new FormData()
      formData.append("file", csvFile)
      const result = await api.post<{ imported: number }>("/leads/import/csv", formData, true)
      setCsvResult(result)
    } catch (e: any) {
      alert(e.message || "CSV upload failed")
    } finally {
      setCsvUploading(false)
    }
  }

  const handleOAuth = async (provider: string) => {
    try {
      const info = await api.get<{ auth_url: string }>(`/admin/integrations/${provider}/oauth/init`)
      if (info.auth_url) {
        window.open(info.auth_url, "_blank", "width=600,height=700")
        if (provider === "gmail" || provider === "outlook") setHasEmail(true)
        if (provider === "linkedin") setHasLinkedin(true)
      }
    } catch (e: any) {
      alert(e.message || `Cannot initiate ${provider} OAuth. Configure provider credentials in Admin Integrations panel first.`)
    }
  }

  const saveSdr = async () => {
    const payload: any = {
      ...form,
      lead_sources: leadSources.join(","),
      linkedin_connect_enabled: true,
      linkedin_dm_enabled: true,
    }
    if (isManual) {
      payload.target_titles = ""
      payload.target_industries = ""
      payload.target_locations = ""
    }
    if (sdrId) {
      await api.put(`/sdr/profiles/${sdrId}`, payload)
    } else {
      const created = await api.post<any>("/sdr/profiles", payload)
      setSdrId(created.id)
    }
    return sdrId
  }

  const saveEmailCreds = async () => {
    if (!sdrId) return
    const creds = {
      provider: "smtp",
      host: smtpForm.host,
      port: smtpForm.port,
      username: smtpForm.username,
      password: smtpForm.password,
      sender_email: smtpForm.sender_email,
      sender_name: smtpForm.sender_name || form.name,
      imap_host: smtpForm.imap_host || smtpForm.host,
      imap_port: smtpForm.imap_port,
      imap_username: smtpForm.imap_username || smtpForm.username,
      imap_password: smtpForm.imap_password || smtpForm.password,
    }
    await api.put(`/sdr/profiles/${sdrId}/email-creds`, creds)
    setHasEmail(true)
  }

  const saveAndNext = async () => {
    setSaving(true)
    try {
      if (step === 1 && emailMethod === "smtp") {
        if (!smtpForm.sender_email || !smtpForm.host || !smtpForm.username || !smtpForm.password) {
          alert("Please fill in all required SMTP fields (Sender Email, Host, Username, Password)")
          setSaving(false)
          return
        }
        await saveSdr()
        if (sdrId) await saveEmailCreds()
      } else {
        await saveSdr()
      }

      if (step === 2 && isManual && csvFile && !csvResult) {
        await handleCsvUpload()
      }

      if (step < STEPS.length - 1) {
        setStep(step + 1)
      } else {
        router.push(sdrId ? `/sdr/${sdrId}` : "/sdr")
      }
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => router.push("/sdr")} className="p-2 rounded-lg hover:bg-white/5">
          <ArrowLeft size={18} className="text-muted-foreground" />
        </button>
        <Bot size={28} className="text-purple-500" />
        <div>
          <h1 className="text-2xl font-semibold">Create AI SDR</h1>
          <p className="text-sm text-muted-foreground">Set up your AI sales development representative</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-0">
        {STEPS.map((s, i) => {
          const StepIcon = s.icon
          const isActive = i === step
          const isDone = i < step
          return (
            <div key={s.key} className="flex-1">
              <button
                onClick={() => i <= step && setStep(i)}
                className={`w-full flex flex-col items-center gap-1.5 p-3 rounded-lg transition-colors ${isActive ? "bg-purple-500/10" : isDone ? "bg-green-500/5" : "opacity-50"}`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  isDone ? "bg-green-500/20 text-green-500" :
                  isActive ? "bg-purple-500/20 text-purple-500" :
                  "bg-white/5 text-gray-500"
                }`}>
                  {isDone ? <Check size={14} /> : <StepIcon size={14} />}
                </div>
                <span className="text-[10px] font-medium text-center leading-tight">{s.label}</span>
                <span className="text-[8px] text-muted-foreground text-center">{s.description}</span>
              </button>
            </div>
          )
        })}
      </div>

      {/* ======================== STEP 0: IDENTITY ======================== */}
      {step === 0 && (
        <div className="card p-6 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Bot size={18} className="text-purple-500" />
            SDR Identity
          </h2>
          <div>
            <label className="label">SDR Name</label>
            <input value={form.name} onChange={(e) => updateField("name", e.target.value)} className="input w-full" placeholder="e.g. Alex, Sarah, AI SDR" />
          </div>
          <div>
            <label className="label">Target Region</label>
            <input value={form.region} onChange={(e) => updateField("region", e.target.value)} className="input w-full" placeholder="e.g. US, UK, India, Global" />
            <p className="text-xs text-muted-foreground mt-1">The SDR will adapt communication style per region</p>
          </div>
          <div>
            <label className="label">What are you selling?</label>
            <div className="flex gap-2">
              <button onClick={() => updateField("sell_type", "product")} className={`flex-1 p-3 rounded-lg border text-sm text-center ${form.sell_type === "product" ? "border-purple-500 bg-purple-500/10 text-purple-400" : "border-white/10 hover:border-white/20"}`}>
                <Sparkles size={20} className="mx-auto mb-1" />Product
              </button>
              <button onClick={() => updateField("sell_type", "service")} className={`flex-1 p-3 rounded-lg border text-sm text-center ${form.sell_type === "service" ? "border-purple-500 bg-purple-500/10 text-purple-400" : "border-white/10 hover:border-white/20"}`}>
                <Users size={20} className="mx-auto mb-1" />Service
              </button>
            </div>
          </div>
          {form.sell_type === "product" ? (
            <>
              <div>
                <label className="label">Product Name</label>
                <input value={form.product_name} onChange={(e) => updateField("product_name", e.target.value)} className="input w-full" placeholder="e.g. OutreachAI, SalesPro" />
              </div>
              <div>
                <label className="label">Product Description</label>
                <textarea value={form.product_description} onChange={(e) => updateField("product_description", e.target.value)} className="input w-full h-20" placeholder="Describe what your product does and the problem it solves..." />
              </div>
            </>
          ) : (
            <div>
              <label className="label">Service Description</label>
              <textarea value={form.service_description} onChange={(e) => updateField("service_description", e.target.value)} className="input w-full h-20" placeholder="Describe your service..." />
            </div>
          )}
          <div className="flex justify-end pt-2">
            <button onClick={saveAndNext} disabled={saving} className="btn-primary text-sm flex items-center gap-1.5">
              {saving ? "Saving..." : "Continue"} <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ======================== STEP 1: CONNECT ACCOUNTS ======================== */}
      {step === 1 && (
        <div className="space-y-4">
          {/* Email Section */}
          <div className="card p-6 space-y-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Mail size={18} className="text-blue-500" />
              Connect Email
            </h2>
            <p className="text-sm text-muted-foreground">
              Choose how your SDR will send and track emails. OAuth is recommended for auto token management.
            </p>

            {/* Gmail OAuth */}
            <div className={`p-4 rounded-lg border transition-all ${emailMethod === "oauth" ? "border-blue-500/50 bg-blue-500/5" : "border-white/10"}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail size={22} className="text-red-500" />
                  <div>
                    <p className="text-sm font-medium">Gmail / Google Workspace</p>
                    <p className="text-xs text-muted-foreground">Connect via Google OAuth — one click</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {hasEmail ? (
                    <span className="text-xs px-2.5 py-1 rounded-full bg-green-500/10 text-green-500 flex items-center gap-1">
                      <CheckCircle size={12} /> Connected
                    </span>
                  ) : (
                    <button onClick={() => handleOAuth("gmail")} className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 border border-white/20 flex items-center gap-1.5">
                      <ExternalLink size={12} /> Connect Gmail
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Outlook OAuth */}
            <div className={`p-4 rounded-lg border transition-all ${emailMethod === "oauth" ? "border-blue-500/50 bg-blue-500/5" : "border-white/10"}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail size={22} className="text-blue-500" />
                  <div>
                    <p className="text-sm font-medium">Outlook / Microsoft 365</p>
                    <p className="text-xs text-muted-foreground">Connect via Microsoft OAuth — one click</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {hasEmail ? (
                    <span className="text-xs px-2.5 py-1 rounded-full bg-green-500/10 text-green-500 flex items-center gap-1">
                      <CheckCircle size={12} /> Connected
                    </span>
                  ) : (
                    <button onClick={() => handleOAuth("outlook")} className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 border border-white/20 flex items-center gap-1.5">
                      <ExternalLink size={12} /> Connect Outlook
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* SMTP Manual */}
            <div className={`p-4 rounded-lg border transition-all ${emailMethod === "smtp" ? "border-amber-500/50 bg-amber-500/5" : "border-white/10"}`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <Key size={22} className="text-amber-500" />
                  <div>
                    <p className="text-sm font-medium">SMTP + IMAP (Manual)</p>
                    <p className="text-xs text-muted-foreground">For Hostinger, Zoho, cPanel, or custom mail servers</p>
                  </div>
                </div>
                <button
                  onClick={() => setEmailMethod(emailMethod === "smtp" ? null : "smtp")}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${emailMethod === "smtp" ? "bg-amber-500/10 border-amber-500/30 text-amber-500" : "bg-white/10 border-white/20 hover:bg-white/20"}`}
                >
                  {emailMethod === "smtp" ? "Collapse" : "Configure"}
                </button>
              </div>
              {emailMethod === "smtp" && (<>
                <div className="grid grid-cols-2 gap-3 pt-3 border-t border-white/10">
                  <div className="col-span-2">
                    <label className="label">Sender Name</label>
                    <input
                      value={smtpForm.sender_name}
                      onChange={(e) => setSmtpForm((f) => ({ ...f, sender_name: e.target.value }))}
                      className="input w-full" placeholder="AI SDR"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="label">Sender Email</label>
                    <input
                      value={smtpForm.sender_email}
                      onChange={(e) => setSmtpForm((f) => ({ ...f, sender_email: e.target.value }))}
                      className="input w-full" placeholder="sdr@yourcompany.com"
                    />
                  </div>
                  <div>
                    <label className="label">SMTP Host</label>
                    <input value={smtpForm.host} onChange={(e) => setSmtpForm((f) => ({ ...f, host: e.target.value }))} className="input w-full" placeholder="smtp.hostinger.com" />
                  </div>
                  <div>
                    <label className="label">SMTP Port</label>
                    <input type="number" value={smtpForm.port} onChange={(e) => setSmtpForm((f) => ({ ...f, port: parseInt(e.target.value) || 587 }))} className="input w-full" />
                  </div>
                  <div>
                    <label className="label">SMTP Username</label>
                    <input value={smtpForm.username} onChange={(e) => setSmtpForm((f) => ({ ...f, username: e.target.value }))} className="input w-full" placeholder="sdr@yourcompany.com" />
                  </div>
                  <div>
                    <label className="label">SMTP Password</label>
                    <div className="relative">
                      <input type={showPwd ? "text" : "password"} value={smtpForm.password} onChange={(e) => setSmtpForm((f) => ({ ...f, password: e.target.value }))} className="input w-full pr-8" placeholder="••••••••" />
                      <button onClick={() => setShowPwd(!showPwd)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground">
                        {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="label">IMAP Host</label>
                    <input value={smtpForm.imap_host} onChange={(e) => setSmtpForm((f) => ({ ...f, imap_host: e.target.value }))} className="input w-full" placeholder="imap.hostinger.com" />
                  </div>
                  <div>
                    <label className="label">IMAP Port</label>
                    <input type="number" value={smtpForm.imap_port} onChange={(e) => setSmtpForm((f) => ({ ...f, imap_port: parseInt(e.target.value) || 993 }))} className="input w-full" />
                  </div>
                  <div>
                    <label className="label">IMAP Username</label>
                    <input value={smtpForm.imap_username} onChange={(e) => setSmtpForm((f) => ({ ...f, imap_username: e.target.value }))} className="input w-full" placeholder="Same as SMTP if blank" />
                  </div>
                  <div>
                    <label className="label">IMAP Password</label>
                    <input type="password" value={smtpForm.imap_password} onChange={(e) => setSmtpForm((f) => ({ ...f, imap_password: e.target.value }))} className="input w-full" placeholder="Same as SMTP if blank" />
                  </div>
                </div>
                <div className="flex justify-end pt-3 border-t border-white/10 mt-3">
                  <button
                    onClick={async () => {
                      if (!smtpForm.sender_email || !smtpForm.host || !smtpForm.username || !smtpForm.password) {
                        alert("Please fill Sender Email, SMTP Host, Username, and Password")
                        return
                      }
                      setSaving(true)
                      try {
                        await saveSdr()
                        if (sdrId) await saveEmailCreds()
                        alert("SMTP configuration saved successfully!")
                      } catch (e: any) {
                        alert(e.message || "Failed to save SMTP configuration")
                      } finally {
                        setSaving(false)
                      }
                    }}
                    disabled={saving}
                    className="text-xs px-4 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-500 hover:bg-amber-500/20 flex items-center gap-1.5"
                  >
                    <CheckCircle size={14} /> Save SMTP Configuration
                  </button>
                </div>
              </>)}
            </div>
          </div>

          {/* LinkedIn Section */}
          <div className="card p-6 space-y-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Linkedin size={18} className="text-cyan-500" />
              Connect LinkedIn
            </h2>
            <p className="text-sm text-muted-foreground">
              Connect LinkedIn for profile management — sending invites, messaging, likes, comments, and prospecting.
              The SDR uses LinkedIn profiles to research who it's reaching and tailor outreach accordingly.
            </p>
            <div className="p-4 rounded-lg border border-white/10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Linkedin size={22} className="text-cyan-500" />
                  <div>
                    <p className="text-sm font-medium">LinkedIn Account</p>
                    <p className="text-xs text-muted-foreground">
                      {hasLinkedin
                        ? "LinkedIn connected — the SDR can manage invites, DMs, likes & comments"
                        : "Connect to enable LinkedIn outreach and prospect research"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {hasLinkedin ? (
                    <span className="text-xs px-2.5 py-1 rounded-full bg-green-500/10 text-green-500 flex items-center gap-1">
                      <CheckCircle size={12} /> Connected
                    </span>
                  ) : (
                    <button onClick={() => handleOAuth("linkedin")} className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 border border-white/20 flex items-center gap-1.5">
                      <ExternalLink size={12} /> Connect LinkedIn
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button onClick={saveAndNext} disabled={saving} className="btn-primary text-sm flex items-center gap-1.5">
              {saving ? "Saving..." : "Continue"} <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ======================== STEP 2: LEAD SOURCES ======================== */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="card p-6 space-y-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Globe size={18} className="text-green-500" />
              Lead Sources
            </h2>
            <p className="text-sm text-muted-foreground">
              Select how your SDR will find leads. Choose <strong>Manual Upload</strong> to provide your own list, or let the SDR discover leads.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {LEAD_SOURCE_OPTIONS.map((src) => {
                const Icon = src.icon
                const selected = leadSources.includes(src.key)
                return (
                  <button
                    key={src.key}
                    onClick={() => toggleSource(src.key)}
                    className={`p-4 rounded-lg border text-left transition-all ${
                      selected ? "border-purple-500 bg-purple-500/10" : "border-white/10 hover:border-white/20"
                    }`}
                  >
                    <Icon size={22} className={`mb-2 ${src.color}`} />
                    <p className="text-sm font-medium">{src.label}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{src.desc}</p>
                    {selected && <Check size={14} className="mt-1 text-purple-500" />}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Manual Upload Section */}
          {isManual && (
            <div className="card p-6 space-y-4">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Upload size={16} className="text-blue-500" />
                Upload Your Lead List
              </h3>

              {/* List Name */}
              <div>
                <label className="label">Name Your Lead List</label>
                <input
                  value={listName}
                  onChange={(e) => setListName(e.target.value)}
                  className="input w-full"
                  placeholder="e.g. Q2 Prospects, Tech Conference Leads"
                />
              </div>

              {/* CSV Upload */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  csvFile ? "border-green-500/50 bg-green-500/5" : "border-white/20 hover:border-white/40"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) setCsvFile(file)
                  }}
                />
                {csvFile ? (
                  <div>
                    <FileText size={32} className="mx-auto mb-2 text-green-500" />
                    <p className="text-sm font-medium">{csvFile.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">{(csvFile.size / 1024).toFixed(1)} KB</p>
                    <button onClick={(e) => { e.stopPropagation(); setCsvFile(null); setCsvResult(null) }} className="text-xs text-red-500 mt-2">Remove</button>
                  </div>
                ) : (
                  <div>
                    <Upload size={32} className="mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm font-medium">Drop CSV file here or click to browse</p>
                    <p className="text-xs text-muted-foreground mt-1">First row must be column headers</p>
                  </div>
                )}
              </div>

              {/* Sample CSV */}
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/leads/sample-csv`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
              >
                <Download size={12} /> Download sample CSV template
              </a>

              {/* Upload Button */}
              {csvFile && listName.trim() && !csvResult && (
                <button
                  onClick={handleCsvUpload}
                  disabled={csvUploading}
                  className="btn-primary text-sm flex items-center gap-1.5"
                >
                  {csvUploading ? "Uploading..." : <><Upload size={14} /> Upload & Import Leads</>}
                </button>
              )}

              {/* Upload Result */}
              {csvResult && (
                <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30">
                  <div className="flex items-center gap-2">
                    <CheckCircle size={18} className="text-green-500" />
                    <div>
                      <p className="text-sm font-medium text-green-500">Import Complete</p>
                      <p className="text-xs text-muted-foreground">{csvResult.imported} leads imported to "{listName}"</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Google My Business Section */}
          <div className="card p-6 space-y-4">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Building2 size={16} className="text-amber-500" />
              Google My Business
            </h3>
            <p className="text-sm text-muted-foreground">
              Scrape business listings from Google Maps for local lead generation
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Business Category</label>
                <input value={gmbCategory} onChange={(e) => setGmbCategory(e.target.value)} className="input w-full" placeholder="e.g. Real Estate, Dentist" />
              </div>
              <div>
                <label className="label">Location</label>
                <input value={gmbLocation} onChange={(e) => setGmbLocation(e.target.value)} className="input w-full" placeholder="e.g. New York, London" />
              </div>
            </div>
            <button
              onClick={() => setGmbEnabled(!gmbEnabled)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${gmbEnabled ? "bg-green-500/10 border-green-500/30 text-green-500" : "bg-white/10 border-white/20 hover:bg-white/20"}`}
            >
              {gmbEnabled ? "Google My Business Enabled" : "Enable Google My Business Scraping"}
            </button>
          </div>

          <div className="flex justify-end pt-2">
            <button onClick={saveAndNext} disabled={saving} className="btn-primary text-sm flex items-center gap-1.5">
              {saving ? "Saving..." : "Continue"} <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ======================== STEP 3: SETTINGS ======================== */}
      {step === 3 && (
        <div className="card p-6 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Target size={18} className="text-purple-500" />
            {isManual ? "SDR Behavior Settings" : "ICP & Settings"}
          </h2>
          <p className="text-sm text-muted-foreground">
            {isManual
              ? "Since you uploaded your own lead list, the SDR will analyze your data and adapt its outreach automatically. Configure tone and limits below."
              : "Define your ideal customer profile so the SDR can find and target the right prospects."}
          </p>

          {/* ICP fields - hidden when manual */}
          {!isManual && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Target Job Titles</label>
                <input value={form.target_titles} onChange={(e) => updateField("target_titles", e.target.value)} className="input w-full" placeholder="e.g. CEO, CTO, VP of Sales" />
              </div>
              <div>
                <label className="label">Target Industries</label>
                <input value={form.target_industries} onChange={(e) => updateField("target_industries", e.target.value)} className="input w-full" placeholder="e.g. SaaS, Real Estate, Healthcare" />
              </div>
              <div className="md:col-span-2">
                <label className="label">Target Locations</label>
                <input value={form.target_locations} onChange={(e) => updateField("target_locations", e.target.value)} className="input w-full" placeholder="e.g. US, UK, Remote" />
              </div>
            </div>
          )}

          {/* Always visible settings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="label">Outreach Tone</label>
              <select value={form.outreach_tone} onChange={(e) => updateField("outreach_tone", e.target.value)} className="input w-full">
                <option value="professional">Professional</option>
                <option value="friendly">Friendly</option>
                <option value="casual">Casual</option>
                <option value="formal">Formal</option>
              </select>
            </div>
            <div>
              <label className="label">SDR Personality</label>
              <input value={form.sdr_personality} onChange={(e) => updateField("sdr_personality", e.target.value)} className="input w-full" placeholder="e.g. Confident, empathetic, solution-oriented" />
            </div>
            <div>
              <label className="label">Daily Email Limit</label>
              <input type="number" value={form.max_daily_emails} onChange={(e) => updateField("max_daily_emails", parseInt(e.target.value) || 0)} className="input w-full" />
            </div>
            <div>
              <label className="label">Daily LinkedIn Limit</label>
              <input type="number" value={form.max_daily_linkedin} onChange={(e) => updateField("max_daily_linkedin", parseInt(e.target.value) || 0)} className="input w-full" />
            </div>
            <div>
              <label className="label">Daily Call Limit</label>
              <input type="number" value={form.max_daily_calls} onChange={(e) => updateField("max_daily_calls", parseInt(e.target.value) || 0)} className="input w-full" />
            </div>
            <div>
              <label className="label">Monthly Lead Target</label>
              <input type="number" value={form.leads_target} onChange={(e) => updateField("leads_target", parseInt(e.target.value) || 0)} className="input w-full" />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button onClick={saveAndNext} disabled={saving} className="btn-primary text-sm flex items-center gap-1.5">
              {saving ? "Saving..." : "Continue"} <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ======================== STEP 4: REVIEW & LAUNCH ======================== */}
      {step === 4 && (
        <div className="card p-6 space-y-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Sparkles size={18} className="text-amber-500" />
            Review & Launch
          </h2>
          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between">
              <span className="text-xs text-muted-foreground">SDR Name</span>
              <span className="text-sm font-medium">{form.name}</span>
            </div>
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between">
              <span className="text-xs text-muted-foreground">Region</span>
              <span className="text-sm">{form.region || "Global"}</span>
            </div>
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between">
              <span className="text-xs text-muted-foreground">Selling</span>
              <span className="text-sm capitalize">{form.sell_type}: {form.product_name || form.service_description?.slice(0, 50) || "Not specified"}</span>
            </div>
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between">
              <span className="text-xs text-muted-foreground">Email</span>
              <span className={`text-sm ${hasEmail ? "text-green-500" : "text-amber-500"}`}>{hasEmail ? "Connected" : "Not connected (setup later)"}</span>
            </div>
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between">
              <span className="text-xs text-muted-foreground">LinkedIn</span>
              <span className={`text-sm ${hasLinkedin ? "text-green-500" : "text-amber-500"}`}>{hasLinkedin ? "Connected" : "Not connected (setup later)"}</span>
            </div>
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between">
              <span className="text-xs text-muted-foreground">Lead Sources</span>
              <span className="text-sm capitalize">{leadSources.join(", ") || "None selected"}</span>
            </div>
            {csvResult && (
              <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between">
                <span className="text-xs text-muted-foreground">Uploaded List</span>
                <span className="text-sm">{listName} ({csvResult.imported} leads)</span>
              </div>
            )}
            <div className="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between">
              <span className="text-xs text-muted-foreground">Limits</span>
              <span className="text-sm">{form.max_daily_emails} emails/day | {form.max_daily_linkedin} LinkedIn/day | {form.max_daily_calls} calls/day</span>
            </div>
          </div>
          <div className="flex items-center justify-end gap-3 pt-2">
            <button onClick={() => setStep(0)} className="btn-secondary text-sm">Edit</button>
            <button
              onClick={async () => {
                setSaving(true)
                try {
                  const id = await saveSdr()
                  router.push(id ? `/sdr/${id}` : "/sdr")
                } catch (e) { console.error(e) }
                finally { setSaving(false) }
              }}
              disabled={saving}
              className="btn-primary text-sm flex items-center gap-1.5"
            >
              <Save size={14} /> {saving ? "Saving..." : sdrId ? "Update SDR" : "Create SDR"}
            </button>
            <button
              onClick={async () => {
                setSaving(true)
                try {
                  const id = await saveSdr()
                  if (id) {
                    await api.post(`/sdr/profiles/${id}/activate`)
                    router.push(`/sdr/${id}`)
                  }
                } catch (e) { console.error(e) }
                finally { setSaving(false) }
              }}
              disabled={saving}
              className="text-sm px-4 py-2 rounded-lg bg-green-500/20 border border-green-500/30 text-green-500 hover:bg-green-500/30 flex items-center gap-1.5"
            >
              <Play size={14} /> Create & Activate
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
