"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Users, Search, RefreshCw, Mail, ExternalLink, CheckCircle, Calendar, MessageCircle, Target, Globe, Download, Loader, MapPin, Building2, Phone, Clock } from "lucide-react"

interface LeadRecord {
  id: string
  first_name: string
  last_name: string
  title: string
  company: string
  email: string
  phone: string
  industry: string
  location: string
  city: string
  state: string
  country: string
  postal_code: string
  company_size: string
  products_services: string
  source: string
  status: string
  website: string
  notes: string
  created_at: string
}

const SOURCE_BADGES: Record<string, { label: string; color: string }> = {
  web_scrape: { label: "Web Scrape", color: "bg-green-500/10 text-green-700" },
  manual: { label: "Manual Upload", color: "bg-blue-500/10 text-blue-700" },
  apollo: { label: "Apollo.io", color: "bg-purple-500/10 text-purple-700" },
  csv: { label: "CSV Upload", color: "bg-blue-500/10 text-blue-700" },
  google_business: { label: "Google Business", color: "bg-amber-500/10 text-amber-700" },
  directory_india: { label: "India Directory", color: "bg-orange-500/10 text-orange-700" },
  directory_unknown: { label: "Directory", color: "bg-teal-500/10 text-teal-700" },
  lusha: { label: "Lusha", color: "bg-pink-500/10 text-pink-700" },
  rocketreach: { label: "RocketReach", color: "bg-indigo-500/10 text-indigo-700" },
}

const ALL_SOURCES = Object.keys(SOURCE_BADGES)

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [sourceFilter, setSourceFilter] = useState<string>("all")
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const perPage = 25

  useEffect(() => { load() }, [page, sourceFilter])

  const load = async () => {
    setLoading(true)
    try {
      const r = await api.get<any>(`/leads?page=${page}&per_page=${perPage}${search ? `&search=${encodeURIComponent(search)}` : ""}`)
      setLeads(r.items || [])
      setTotal(r.total || 0)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const handleSearch = () => {
    setPage(1)
    load()
  }

  const getSources = (): string[] => {
    const sources = new Set(leads.map((l) => l.source))
    return ["all", ...ALL_SOURCES.filter((s) => sources.has(s)), ...Array.from(sources).filter((s) => !ALL_SOURCES.includes(s))]
  }

  const filtered = sourceFilter === "all" ? leads : leads.filter((l) => l.source === sourceFilter)

  const totalPages = Math.ceil(total / perPage)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users size={28} className="text-blue-500" />
          <h1 className="text-2xl font-semibold">Leads</h1>
          <span className="text-sm text-muted-foreground">({total} total)</span>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2"><RefreshCw size={14} /> Refresh</button>
      </div>

      {/* Search + Source Filter */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 max-w-md flex-1">
          <Search size={18} className="text-muted-foreground shrink-0" />
          <input type="text" placeholder="Search by name, email, company..." value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="flex-1 px-3 py-2 rounded-lg border bg-transparent text-sm outline-none" />
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          <button onClick={() => { setSourceFilter("all"); setPage(1) }}
            className={`text-xs px-2.5 py-1.5 rounded-lg font-medium transition-colors ${sourceFilter === "all" ? "bg-brand-600 text-white" : "bg-muted hover:bg-muted/80"}`}>
            All Sources
          </button>
          {getSources().filter((s) => s !== "all").map((s) => {
            const badge = SOURCE_BADGES[s] || { label: s, color: "bg-muted text-muted-foreground" }
            return (
              <button key={s} onClick={() => { setSourceFilter(s); setPage(1) }}
                className={`text-xs px-2.5 py-1.5 rounded-lg font-medium transition-colors ${sourceFilter === s ? "bg-brand-600 text-white" : "bg-muted hover:bg-muted/80"}`}>
                {badge.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Leads Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">No leads found. Import leads via scraping, CSV, or Apollo.io.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left p-2.5 font-medium text-xs">Name</th>
                  <th className="text-left p-2.5 font-medium text-xs">Email</th>
                  <th className="text-left p-2.5 font-medium text-xs">Phone</th>
                  <th className="text-left p-2.5 font-medium text-xs">Company</th>
                  <th className="text-left p-2.5 font-medium text-xs">Industry</th>
                  <th className="text-left p-2.5 font-medium text-xs">Location</th>
                  <th className="text-left p-2.5 font-medium text-xs">Source</th>
                  <th className="text-left p-2.5 font-medium text-xs">Products/Services</th>
                  <th className="text-right p-2.5 font-medium text-xs">Created</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => {
                  const badge = SOURCE_BADGES[l.source] || { label: l.source, color: "bg-muted text-muted-foreground" }
                  const name = [l.first_name, l.last_name].filter(Boolean).join(" ") || l.email || "Unknown"
                  const locParts = [l.city, l.state, l.country].filter(Boolean)
                  const location = locParts.length > 0 ? locParts.join(", ") : l.location || "-"
                  return (
                    <tr key={l.id} className="border-b border-border hover:bg-muted/30 transition-colors">
                      <td className="p-2.5">
                        <div className="font-medium text-xs">{name}</div>
                        {l.title && <div className="text-[10px] text-muted-foreground">{l.title}</div>}
                      </td>
                      <td className="p-2.5 text-xs">
                        {l.email ? (
                          <a href={`mailto:${l.email}`} className="text-blue-500 hover:underline">{l.email}</a>
                        ) : "-"}
                      </td>
                      <td className="p-2.5 text-xs">{l.phone || "-"}</td>
                      <td className="p-2.5">
                        <div className="text-xs">{l.company || "-"}</div>
                        {l.company_size && <div className="text-[10px] text-muted-foreground">Size: {l.company_size}</div>}
                      </td>
                      <td className="p-2.5 text-xs">{l.industry || "-"}</td>
                      <td className="p-2.5 text-xs">{location}</td>
                      <td className="p-2.5">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${badge.color}`}>{badge.label}</span>
                      </td>
                      <td className="p-2.5 text-xs max-w-[150px] truncate" title={l.products_services || ""}>
                        {l.products_services || "-"}
                      </td>
                      <td className="p-2.5 text-right text-[10px] text-muted-foreground whitespace-nowrap">
                        {l.created_at ? new Date(l.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "-"}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-3 border-t border-border">
            <span className="text-xs text-muted-foreground">Page {page} of {totalPages} ({total} leads)</span>
            <div className="flex gap-1">
              <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}
                className="px-3 py-1 text-xs rounded bg-muted hover:bg-muted/80 disabled:opacity-50">Previous</button>
              <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page === totalPages}
                className="px-3 py-1 text-xs rounded bg-muted hover:bg-muted/80 disabled:opacity-50">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
