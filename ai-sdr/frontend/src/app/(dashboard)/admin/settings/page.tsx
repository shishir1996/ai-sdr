"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Settings, Save, Package, Calendar, BookOpen, Globe, Shield, X } from "lucide-react"

const ALL_COUNTRIES = [
  "India", "United States", "United Kingdom", "Canada", "Australia",
  "Germany", "France", "Singapore", "UAE", "Brazil", "Japan", "China", "Other",
]

const PRESET_CATEGORIES = [
  "Automotive", "Beauty & Personal Care", "Business Services", "Construction & Contractors",
  "Education", "Entertainment & Recreation", "Finance & Insurance", "Food & Dining",
  "Health & Medical", "Home Services", "IT & Technology", "Legal Services",
  "Manufacturing", "Marketing & Advertising", "Media & Communications", "Real Estate",
  "Retail", "Shopping", "Sports & Fitness", "Transportation & Logistics",
  "Travel & Hospitality",
]

export default function SettingsPage() {
  const [form, setForm] = useState({
    sell_type: "product",
    product_name: "",
    product_description: "",
    payment_link: "",
    service_description: "",
    calendar_link: "",
    knowledge_base: "",
    scraping_enabled: false,
    approved_countries: "",
    approved_categories: "",
  })
  const [approvedCountriesList, setApprovedCountriesList] = useState<string[]>([])
  const [approvedCategoriesList, setApprovedCategoriesList] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => { load() }, [])

  const load = async () => {
    try {
      const s = await api.get<any>("/settings/org")
      if (s) {
        setForm({ ...form, ...s })
        if (s.approved_countries) {
          try { setApprovedCountriesList(JSON.parse(s.approved_countries)) }
          catch { setApprovedCountriesList(s.approved_countries.split(",").map((c: string) => c.trim()).filter(Boolean)) }
        }
        if (s.approved_categories) {
          try { setApprovedCategoriesList(JSON.parse(s.approved_categories)) }
          catch { setApprovedCategoriesList(s.approved_categories.split(",").map((c: string) => c.trim()).filter(Boolean)) }
        }
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const toggleCountry = (country: string) => {
    setApprovedCountriesList((prev) =>
      prev.includes(country) ? prev.filter((c) => c !== country) : [...prev, country]
    )
  }

  const toggleCategory = (cat: string) => {
    setApprovedCategoriesList((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    )
  }

  const save = async () => {
    setSaving(true)
    try {
      await api.put("/settings/org", {
        ...form,
        approved_countries: JSON.stringify(approvedCountriesList),
        approved_categories: JSON.stringify(approvedCategoriesList),
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e: any) { alert(e.message) }
    finally { setSaving(false) }
  }

  if (loading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Settings size={28} className="text-muted-foreground" />
        <h1 className="text-2xl font-semibold">Organization Settings</h1>
      </div>

      {/* Scrape Permissions - Admin Only */}
      <div className="card p-5 space-y-4 border-brand-500/30">
        <div className="flex items-center gap-2">
          <Shield size={20} className="text-brand-500" />
          <h3 className="font-semibold">Web Scrape Permissions (Admin)</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Configure which countries and business categories the team is allowed to scrape.
          When disabled, all scraping is blocked.
        </p>

        {/* Enable/Disable Scraping */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" checked={form.scraping_enabled} onChange={(e) => setForm({ ...form, scraping_enabled: e.target.checked })} className="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
          <div>
            <span className="font-medium text-sm">Enable Web Scraping</span>
            <p className="text-xs text-muted-foreground">Allow team members to scrape websites and Google Business Profiles</p>
          </div>
        </label>

        {/* Approved Countries */}
        <div>
          <label className="text-sm font-medium block mb-2">Approved Countries</label>
          <p className="text-xs text-muted-foreground mb-2">Select countries the team is allowed to scrape leads from.</p>
          <div className="flex flex-wrap gap-1.5">
            {ALL_COUNTRIES.map((c) => (
              <button key={c} onClick={() => toggleCountry(c)}
                className={`text-xs px-2.5 py-1 rounded-lg transition-colors ${approvedCountriesList.includes(c) ? "bg-brand-600 text-white" : "bg-muted hover:bg-muted/80"}`}>
                {c}
              </button>
            ))}
          </div>
          {approvedCountriesList.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {approvedCountriesList.map((c) => (
                <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-700 flex items-center gap-1">
                  {c} <X size={10} className="cursor-pointer" onClick={() => toggleCountry(c)} />
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Approved Business Categories */}
        <div>
          <label className="text-sm font-medium block mb-2">Approved Business Categories</label>
          <p className="text-xs text-muted-foreground mb-2">Select business categories allowed for Google Business Profile scraping.</p>
          <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
            {PRESET_CATEGORIES.map((cat) => (
              <button key={cat} onClick={() => toggleCategory(cat)}
                className={`text-xs px-2.5 py-1 rounded-lg transition-colors ${approvedCategoriesList.includes(cat) ? "bg-brand-600 text-white" : "bg-muted hover:bg-muted/80"}`}>
                {cat}
              </button>
            ))}
          </div>
          {approvedCategoriesList.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {approvedCategoriesList.map((cat) => (
                <span key={cat} className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-700 flex items-center gap-1">
                  {cat} <X size={10} className="cursor-pointer" onClick={() => toggleCategory(cat)} />
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Sell Type Toggle */}
      <div className="card p-5 space-y-4">
        <h3 className="font-semibold">What are you selling?</h3>
        <p className="text-sm text-muted-foreground">
          This setting controls how the AI SDR operates. Product mode sends payment links. Service mode books meetings.
        </p>
        <div className="flex gap-3">
          <label className={`flex-1 p-4 rounded-lg border cursor-pointer text-center transition-colors ${form.sell_type === "product" ? "border-brand-500 bg-brand-500/10" : "hover:bg-muted"}`}>
            <input type="radio" name="sell_type" value="product" checked={form.sell_type === "product"} onChange={(e) => setForm({ ...form, sell_type: e.target.value })} className="sr-only" />
            <Package size={24} className="mx-auto mb-2 text-brand-500" />
            <span className="font-medium">Product Sales</span>
            <p className="text-xs text-muted-foreground mt-1">Send payment links, track purchases</p>
          </label>
          <label className={`flex-1 p-4 rounded-lg border cursor-pointer text-center transition-colors ${form.sell_type === "service" ? "border-brand-500 bg-brand-500/10" : "hover:bg-muted"}`}>
            <input type="radio" name="sell_type" value="service" checked={form.sell_type === "service"} onChange={(e) => setForm({ ...form, sell_type: e.target.value })} className="sr-only" />
            <Calendar size={24} className="mx-auto mb-2 text-brand-500" />
            <span className="font-medium">Service Sales</span>
            <p className="text-xs text-muted-foreground mt-1">Book meetings, schedule demos</p>
          </label>
        </div>
      </div>

      {/* Product Details */}
      {form.sell_type === "product" && (
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold">Product Details</h3>
          <input placeholder="Product name" value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" />
          <textarea placeholder="Product description — what it does, key features, pricing" value={form.product_description} onChange={(e) => setForm({ ...form, product_description: e.target.value })} rows={3} className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm resize-none" />
          <input placeholder="Payment link (e.g. Stripe, Gumroad, Paddle)" value={form.payment_link} onChange={(e) => setForm({ ...form, payment_link: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" />
        </div>
      )}

      {/* Service Details */}
      {form.sell_type === "service" && (
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold">Service Details</h3>
          <textarea placeholder="Describe your service — what you offer, deliverables, pricing" value={form.service_description} onChange={(e) => setForm({ ...form, service_description: e.target.value })} rows={3} className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm resize-none" />
          <input placeholder="Calendar link (e.g. Calendly, Cal.com, youcanbook.me)" value={form.calendar_link} onChange={(e) => setForm({ ...form, calendar_link: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm" />
        </div>
      )}

      {/* Knowledge Base */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <BookOpen size={20} className="text-muted-foreground" />
          <h3 className="font-semibold">Knowledge Base</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Add information the AI SDR should know about your business, product, service, competitors, pricing, FAQs, etc.
        </p>
        <textarea
          placeholder={`Paste or type knowledge base content here. Include:\n- Key features and benefits\n- Pricing tiers\n- Competitor comparisons\n- Common objections and responses\n- Case studies or testimonials\n- FAQ answers\n- Your unique value proposition`}
          value={form.knowledge_base}
          onChange={(e) => setForm({ ...form, knowledge_base: e.target.value })}
          rows={8}
          className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm resize-none font-mono"
        />
      </div>

      <div className="flex items-center gap-3">
        <button onClick={save} disabled={saving} className="btn-primary flex items-center gap-2">
          {saving ? "Saving..." : <><Save size={16} /> Save Settings</>}
        </button>
        {saved && <span className="text-sm text-green-600">Settings saved!</span>}
      </div>
    </div>
  )
}
