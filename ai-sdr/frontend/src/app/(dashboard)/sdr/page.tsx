"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import {
  Bot, Plus, Trash2, Play, Square, Save, Settings, Globe, Mail, Phone, Linkedin,
  MessageCircle, ThumbsUp, MessageSquare, Sparkles, Target, Users, MapPin, Building2,
  Layers, ArrowRight, Clock, ChevronLeft, ChevronRight, Check, Loader, Bookmark,
  Database, RefreshCw
} from "lucide-react"

const LEAD_SOURCES = [
  { key: "web_scrape", label: "Web Scraped Leads", icon: Globe, color: "text-green-500" },
  { key: "manual", label: "Manual Upload / CSV", icon: Database, color: "text-blue-500" },
  { key: "apollo", label: "Apollo.io Extraction", icon: Target, color: "text-purple-500" },
  { key: "google_business", label: "Google Business Profiles", icon: Building2, color: "text-amber-500" },
  { key: "directory_india", label: "India Directories (IndiaMart/JustDial)", icon: Globe, color: "text-orange-500" },
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
  { channel: "linkedin_dm", delay_days: 4, label: "LinkedIn DM Follow-up" },
  { channel: "email", delay_days: 7, label: "Follow-up Email" },
  { channel: "call", delay_days: 10, label: "Phone Call" },
  { channel: "linkedin_comment", delay_days: 14, label: "LinkedIn Engagement" },
  { channel: "email", delay_days: 17, label: "Final Email" },
]

export default function SDRConfigPage() {
  const [sdrs, setSdrs] = useState<any[]>([])
  const [currentSdr, setCurrentSdr] = useState<any>(null)
  const [step, setStep] = useState(0)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [activating, setActivating] = useState(false)

  const [sequence, setSequence] = useState(DEFAULT_SEQUENCE)
  const [selectedSources, setSelectedSources] = useState<string[]>(["web_scrape", "manual"])

  useEffect(() => { loadSdrs() }, [])

  const loadSdrs = async () => {
    try {
      const list = await api.get<any[]>("/sdr/profiles")
      setSdrs(list)
      if (list.length > 0) {
        setCurrentSdr(list[0])
        loadSequence(list[0])
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const loadSequence = (sdr: any) => {
    if (sdr.campaign_sequence) {
      try { setSequence(JSON.parse(sdr.campaign_sequence)) }
      catch { setSequence(DEFAULT_SEQUENCE) }
    } else {
      setSequence(DEFAULT_SEQUENCE)
    }
    if (sdr.lead_sources) {
      try { setSelectedSources(JSON.parse(sdr.lead_sources)) }
      catch { setSelectedSources(sdr.lead_sources.split(",").map((s: string) => s.trim()).filter(Boolean)) }
    }
  }

  const selectSdr = (sdr: any) => {
    setCurrentSdr(sdr)
    loadSequence(sdr)
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
        name: "New AI SDR",
        region: "",
        sell_type: "product",
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

  if (loading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>
  }

  const steps = ["SDR Identity", "Lead Sources", "Auto-Scrape", "Campaign Sequence", "ICP & Settings"]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bot size={28} className="text-brand-500" />
          <h1 className="text-2xl font-semibold">AI SDR Configuration</h1>
        </div>
        <button onClick={createSdr} className="btn-secondary text-sm flex items-center gap-1"><Plus size={14} /> New SDR</button>
      </div>

      {/* SDR Selector */}
      {sdrs.length > 0 && (
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Bookmark size={16} className="text-brand-500" />
            <h3 className="font-medium text-sm">Your AI SDRs</h3>
            <span className="text-xs text-muted-foreground">({sdrs.length} active)</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {sdrs.map((s) => (
              <div key={s.id} className="flex items-center gap-1">
                <button onClick={() => selectSdr(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${currentSdr?.id === s.id ? "bg-brand-600 text-white" : "bg-muted hover:bg-muted/80"}`}>
                  <Bot size={12} />
                  {s.name || "AI SDR"}
                  {s.is_active && <span className="w-1.5 h-1.5 rounded-full bg-green-400" />}
                  {s.region && <span className="text-[10px] opacity-70">({s.region})</span>}
                </button>
                <button onClick={() => deleteSdr(s.id)} className="p-1 text-muted-foreground hover:text-red-500"><Trash2 size={12} /></button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step Navigation */}
      {currentSdr && (
        <div className="card p-5">
          {/* Progress Steps */}
          <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-2">
            {steps.map((s, i) => (
              <button key={i} onClick={() => setStep(i)} className="flex items-center gap-1 shrink-0">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${i === step ? "bg-brand-600 text-white" : i < step ? "bg-green-500 text-white" : "bg-muted text-muted-foreground"}`}>
                  {i < step ? <Check size={14} /> : i + 1}
                </div>
                <span className={`text-xs mr-2 ${i === step ? "text-foreground font-medium" : "text-muted-foreground"}`}>{s}</span>
                {i < steps.length - 1 && <ChevronRight size={12} className="text-muted-foreground shrink-0" />}
              </button>
            ))}
          </div>

          {/* SDR Identity */}
          {step === 0 && (
            <div className="space-y-4">
              <h3 className="font-semibold">SDR Identity</h3>
              <p className="text-sm text-muted-foreground">Name and region for this SDR. Create multiple SDRs for different regions or campaigns.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">SDR Name</label>
                  <input type="text" value={currentSdr.name || ""} onChange={(e) => updateField("name", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="e.g. US Sales Bot, India Outreach SDR" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Region / Territory</label>
                  <input type="text" value={currentSdr.region || ""} onChange={(e) => updateField("region", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="e.g. North America, India, Europe" />
                </div>
              </div>
            </div>
          )}

          {/* Lead Sources */}
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="font-semibold">Lead Sources</h3>
              <p className="text-sm text-muted-foreground">Select which lead sources this SDR should work on. Only leads from selected sources will be processed.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {LEAD_SOURCES.map((src) => {
                  const Icon = src.icon
                  return (
                    <label key={src.key} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${selectedSources.includes(src.key) ? "border-brand-500 bg-brand-500/5" : "hover:bg-muted"}`}>
                      <input type="checkbox" checked={selectedSources.includes(src.key)} onChange={() => toggleSource(src.key)} className="sr-only" />
                      <Icon size={20} className={src.color} />
                      <div className="flex-1">
                        <span className="text-sm font-medium">{src.label}</span>
                      </div>
                      {selectedSources.includes(src.key) && <Check size={16} className="text-brand-500" />}
                    </label>
                  )
                })}
              </div>
            </div>
          )}

          {/* Auto-Scrape */}
          {step === 2 && (
            <div className="space-y-4">
              <h3 className="font-semibold">Auto-Scrape Configuration</h3>
              <p className="text-sm text-muted-foreground">When activated, the SDR will auto-scrape leads based on these settings before starting outreach.</p>
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" checked={currentSdr.auto_scrape_enabled} onChange={(e) => updateField("auto_scrape_enabled", e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-brand-600" />
                <div>
                  <span className="font-medium text-sm">Enable Auto-Scrape on Activation</span>
                  <p className="text-xs text-muted-foreground">Automatically scrape leads when SDR is activated</p>
                </div>
              </label>

              {currentSdr.auto_scrape_enabled && (
                <div className="p-4 rounded-lg bg-muted/20 border space-y-3">
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Business Category</label>
                    <input type="text" value={currentSdr.scrape_business_category || ""} onChange={(e) => updateField("scrape_business_category", e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="e.g. IT & Technology, Home Services" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Country</label>
                    <input type="text" value={currentSdr.scrape_country || ""} onChange={(e) => updateField("scrape_country", e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="e.g. India, United States" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Directory URLs (one per line)</label>
                    <textarea value={currentSdr.scrape_directory_urls || ""} onChange={(e) => updateField("scrape_directory_urls", e.target.value)}
                      rows={3} className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm resize-none font-mono"
                      placeholder={"https://www.indiamart.com/\nhttps://www.justdial.com/"} />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Web Scrape Targets</label>
                    <textarea value={currentSdr.web_scrape_targets || ""} onChange={(e) => updateField("web_scrape_targets", e.target.value)}
                      rows={2} className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm resize-none"
                      placeholder={"company1.com\ncompany2.com"} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Campaign Sequence */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">Campaign Sequence</h3>
                  <p className="text-sm text-muted-foreground">Design the multi-step outreach sequence. Each step defines channel and delay.</p>
                </div>
                <button onClick={addSequenceStep} className="btn-secondary text-xs flex items-center gap-1"><Plus size={12} /> Add Step</button>
              </div>

              {/* Sequence Visual */}
              <div className="space-y-2">
                {sequence.length === 0 && (
                  <div className="p-8 text-center text-muted-foreground text-sm">No steps defined. Click "Add Step" to build your sequence.</div>
                )}
                {sequence.map((s: any, i: number) => {
                  const Icon = SEQUENCE_CHANNEL_ICONS[s.channel] || Mail
                  const colorClass = SEQUENCE_CHANNEL_COLORS[s.channel] || "text-gray-500 bg-gray-500/10"
                  return (
                    <div key={i} className="flex items-center gap-3 p-3 rounded-lg border bg-muted/10">
                      {/* Step number */}
                      <div className="w-7 h-7 rounded-full bg-brand-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
                        {i + 1}
                      </div>

                      {/* Channel */}
                      <div className="flex items-center gap-2 min-w-[140px]">
                        <div className={`p-1.5 rounded ${colorClass}`}>
                          <Icon size={14} />
                        </div>
                        <select value={s.channel} onChange={(e) => updateSequenceStep(i, "channel", e.target.value)}
                          className="text-xs px-2 py-1 rounded border bg-transparent">
                          <option value="email">Email</option>
                          <option value="linkedin_connect">LinkedIn Connect</option>
                          <option value="linkedin_dm">LinkedIn DM</option>
                          <option value="linkedin_like">LinkedIn Like</option>
                          <option value="linkedin_comment">LinkedIn Comment</option>
                          <option value="call">Phone Call</option>
                        </select>
                      </div>

                      {/* Label */}
                      <input type="text" value={s.label || ""} onChange={(e) => updateSequenceStep(i, "label", e.target.value)}
                        className="flex-1 px-2 py-1 rounded border bg-transparent text-xs" placeholder="Step label" />

                      {/* Delay */}
                      <div className="flex items-center gap-1 min-w-[100px]">
                        <Clock size={12} className="text-muted-foreground" />
                        <input type="number" min={0} value={s.delay_days} onChange={(e) => updateSequenceStep(i, "delay_days", parseInt(e.target.value) || 0)}
                          className="w-12 px-1 py-1 rounded border bg-transparent text-xs text-center" />
                        <span className="text-xs text-muted-foreground">days</span>
                      </div>

                      {/* Arrow connector to next step */}
                      {i < sequence.length - 1 && (
                        <div className="flex items-center gap-0.5">
                          <button onClick={() => moveStep(i, 1)} className="p-0.5 text-muted-foreground hover:text-foreground"><ChevronRight size={12} /></button>
                        </div>
                      )}
                      {i > 0 && (
                        <div className="flex items-center gap-0.5">
                          <button onClick={() => moveStep(i, -1)} className="p-0.5 text-muted-foreground hover:text-foreground"><ChevronLeft size={12} /></button>
                        </div>
                      )}

                      <button onClick={() => removeSequenceStep(i)} className="p-1 text-muted-foreground hover:text-red-500"><Trash2 size={12} /></button>
                    </div>
                  )
                })}
              </div>

              {/* Sequence Timeline Preview */}
              {sequence.length > 0 && (
                <div className="mt-4 p-4 rounded-lg bg-gradient-to-r from-brand-500/5 to-blue-500/5 border border-brand-500/20">
                  <h4 className="text-xs font-medium mb-3">Sequence Timeline Preview</h4>
                  <div className="flex items-start gap-1 overflow-x-auto pb-2">
                    {sequence.map((s: any, i: number) => {
                      const Icon = SEQUENCE_CHANNEL_ICONS[s.channel] || Mail
                      const colorClass = SEQUENCE_CHANNEL_COLORS[s.channel] || "text-gray-500"
                      const totalDays = sequence.slice(0, i + 1).reduce((sum: number, st: any) => sum + (st.delay_days || 0), 0)
                      return (
                        <div key={i} className="flex items-center shrink-0">
                          <div className="flex flex-col items-center min-w-[80px]">
                            <div className={`p-2 rounded-full ${colorClass} border-2 border-background`}>
                              <Icon size={16} />
                            </div>
                            <span className="text-[10px] mt-1 font-medium text-center">{s.label || s.channel}</span>
                            <span className="text-[9px] text-muted-foreground">Day {totalDays}</span>
                          </div>
                          {i < sequence.length - 1 && (
                            <div className="flex items-center mx-1">
                              <div className="h-0.5 w-6 bg-muted-foreground/20" />
                              <ArrowRight size={10} className="text-muted-foreground/30 -ml-1" />
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

          {/* ICP & Settings */}
          {step === 4 && (
            <div className="space-y-4">
              <h3 className="font-semibold">ICP & Outreach Settings</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Target Titles (comma-separated)</label>
                  <input type="text" value={currentSdr.target_titles || ""} onChange={(e) => updateField("target_titles", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="CTO, VP of Engineering, CEO" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Target Industries</label>
                  <input type="text" value={currentSdr.target_industries || ""} onChange={(e) => updateField("target_industries", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="Technology, Healthcare, Finance" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Target Locations</label>
                  <input type="text" value={currentSdr.target_locations || ""} onChange={(e) => updateField("target_locations", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="Bangalore, New York, London" />
                </div>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="text-xs text-muted-foreground block mb-1">Min Company Size</label>
                    <input type="number" value={currentSdr.target_company_size_min || ""} onChange={(e) => updateField("target_company_size_min", e.target.value ? parseInt(e.target.value) : null)}
                      className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="10" />
                  </div>
                  <div className="flex-1">
                    <label className="text-xs text-muted-foreground block mb-1">Max Company Size</label>
                    <input type="number" value={currentSdr.target_company_size_max || ""} onChange={(e) => updateField("target_company_size_max", e.target.value ? parseInt(e.target.value) : null)}
                      className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="500" />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">SDR Personality / Tone</label>
                  <select value={currentSdr.outreach_tone || "professional"} onChange={(e) => updateField("outreach_tone", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm">
                    <option value="professional">Professional</option>
                    <option value="friendly">Friendly</option>
                    <option value="direct">Direct</option>
                    <option value="casual">Casual</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">SDR Personality Instructions</label>
                  <input type="text" value={currentSdr.sdr_personality || ""} onChange={(e) => updateField("sdr_personality", e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" placeholder="e.g. Friendly but professional, uses humor" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Lead Target</label>
                  <input type="number" value={currentSdr.leads_target || 100} onChange={(e) => updateField("leads_target", parseInt(e.target.value) || 100)}
                    className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" />
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-3">Daily Rate Limits</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Max Emails/Day</label>
                    <input type="number" value={currentSdr.max_daily_emails || 20} onChange={(e) => updateField("max_daily_emails", parseInt(e.target.value) || 20)}
                      className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Max Calls/Day</label>
                    <input type="number" value={currentSdr.max_daily_calls || 10} onChange={(e) => updateField("max_daily_calls", parseInt(e.target.value) || 10)}
                      className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Max LinkedIn/Day</label>
                    <input type="number" value={currentSdr.max_daily_linkedin || 15} onChange={(e) => updateField("max_daily_linkedin", parseInt(e.target.value) || 15)}
                      className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Max Likes/Day</label>
                    <input type="number" value={currentSdr.max_daily_likes || 20} onChange={(e) => updateField("max_daily_likes", parseInt(e.target.value) || 20)}
                      className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" />
                  </div>
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-3">LinkedIn Engagement</h4>
                <div className="space-y-2">
                  {[
                    { key: "linkedin_connect_enabled", label: "LinkedIn Connection Requests" },
                    { key: "linkedin_dm_enabled", label: "LinkedIn Direct Messages" },
                    { key: "linkedin_like_enabled", label: "LinkedIn Likes" },
                    { key: "linkedin_comment_enabled", label: "LinkedIn Comments" },
                  ].map((item) => (
                    <label key={item.key} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={(currentSdr as any)[item.key]} onChange={(e) => updateField(item.key, e.target.checked)}
                        className="w-4 h-4 rounded border-gray-300 text-brand-600" />
                      <span className="text-sm">{item.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Navigation & Save */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t">
            <div className="flex gap-2">
              <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}
                className="btn-secondary text-sm flex items-center gap-1 disabled:opacity-50">
                <ChevronLeft size={14} /> Previous
              </button>
              <button onClick={() => setStep(Math.min(steps.length - 1, step + 1))} disabled={step === steps.length - 1}
                className="btn-secondary text-sm flex items-center gap-1 disabled:opacity-50">
                Next <ChevronRight size={14} />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={save} disabled={saving} className="btn-primary text-sm flex items-center gap-1">
                {saving ? <Loader size={14} className="animate-spin" /> : <Save size={14} />}
                Save Config
              </button>
              <button onClick={toggleActive} disabled={activating}
                className={`text-sm flex items-center gap-1 px-4 py-2 rounded-lg font-medium transition-colors ${currentSdr.is_active ? "bg-red-500/10 text-red-600 hover:bg-red-500/20" : "bg-green-500/10 text-green-600 hover:bg-green-500/20"}`}>
                {activating ? <Loader size={14} className="animate-spin" /> : currentSdr.is_active ? <Square size={14} /> : <Play size={14} />}
                {currentSdr.is_active ? "Deactivate" : "Activate & Auto-Run"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* No SDR State */}
      {!currentSdr && sdrs.length === 0 && (
        <div className="card p-12 text-center">
          <Bot size={48} className="mx-auto text-muted-foreground mb-4" />
          <h2 className="text-lg font-semibold mb-2">No AI SDRs Yet</h2>
          <p className="text-sm text-muted-foreground mb-4">Create your first AI SDR to start automating lead outreach across email, LinkedIn, and calls.</p>
          <button onClick={createSdr} className="btn-primary"><Plus size={16} /> Create Your First SDR</button>
        </div>
      )}
    </div>
  )
}
