"use client"

import { useState, useEffect, useCallback } from "react"
import { api, API_BASE } from "@/lib/api-client"
import {
  Users, Search, RefreshCw, Mail, ExternalLink, CheckCircle, Calendar,
  MessageCircle, Target, Globe, Download, Loader, MapPin, Building2,
  Phone, Clock, X, Filter, ChevronDown, ArrowUpDown, FileText, Star,
} from "lucide-react"

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
  company_size: string
  revenue: string
  products_services: string
  source: string
  status: string
  score: number
  website: string
  notes: string
  created_at: string
}

const SOURCE_BADGES: Record<string, { label: string; color: string }> = {
  web_scrape: { label: "Web Scrape", color: "bg-green-500/10 text-green-400 border-green-500/20" },
  manual: { label: "Manual", color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  csv: { label: "CSV Upload", color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  apollo: { label: "Apollo.io", color: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
  google_business: { label: "Google Business", color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  directory_india: { label: "India Directory", color: "bg-orange-500/10 text-orange-400 border-orange-500/20" },
  directory_unknown: { label: "Directory", color: "bg-teal-500/10 text-teal-400 border-teal-500/20" },
  lusha: { label: "Lusha", color: "bg-pink-500/10 text-pink-400 border-pink-500/20" },
  rocketreach: { label: "RocketReach", color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" },
  enriched: { label: "Enriched", color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20" },
}

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  new: { label: "New", color: "bg-blue-500/10 text-blue-400" },
  contacted: { label: "Contacted", color: "bg-amber-500/10 text-amber-400" },
  replied: { label: "Replied", color: "bg-emerald-500/10 text-emerald-400" },
  qualified: { label: "Qualified", color: "bg-purple-500/10 text-purple-400" },
  meeting: { label: "Meeting", color: "bg-pink-500/10 text-pink-400" },
  converted: { label: "Converted", color: "bg-emerald-500/10 text-emerald-400" },
  unqualified: { label: "Unqualified", color: "bg-gray-500/10 text-gray-400" },
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [searchInput, setSearchInput] = useState("")
  const [sourceFilter, setSourceFilter] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [minScore, setMinScore] = useState<number | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState<{
    total: number; by_source: Record<string, number>; by_status: Record<string, number>; scored: number
  } | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const perPage = 25

  useEffect(() => { load(); loadStats() }, [])

  useEffect(() => { load() }, [page, sourceFilter, statusFilter, minScore])

  const loadStats = async () => {
    try { setStats(await api.get("/leads/stats")) } catch { }
  }

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(perPage) })
      if (search) params.set("search", search)
      if (sourceFilter) params.set("source", sourceFilter)
      if (statusFilter) params.set("status", statusFilter)
      if (minScore !== null) params.set("min_score", String(minScore))
      const r = await api.get<any>(`/leads?${params}`)
      setLeads(r.items || [])
      setTotal(r.total || 0)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const handleSearch = useCallback(() => {
    setSearch(searchInput)
    setPage(1)
  }, [searchInput])

  const clearFilters = () => {
    setSearch("")
    setSearchInput("")
    setSourceFilter("")
    setStatusFilter("")
    setMinScore(null)
    setPage(1)
  }

  const totalPages = Math.ceil(total / perPage)
  const hasFilters = search || sourceFilter || statusFilter || minScore !== null
  const sources = stats?.by_source ? Object.keys(stats.by_source).sort() : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20">
            <Users size={22} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Leads</h1>
            <p className="text-sm text-gray-400">{total} total leads</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`${API_BASE}/leads/sample-csv`}
            target="_blank" rel="noopener noreferrer"
            className="btn-ghost text-xs flex items-center gap-1"
          >
            <Download size={14} /> Sample CSV
          </a>
          <button onClick={() => { load(); loadStats() }} className="btn-secondary text-sm flex items-center gap-2">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700/50">
            <div className="text-2xl font-bold text-white">{stats.total}</div>
            <div className="text-xs text-gray-400">Total Leads</div>
          </div>
          <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700/50">
            <div className="text-2xl font-bold text-purple-400">{stats.scored}</div>
            <div className="text-xs text-gray-400">AI Scored</div>
          </div>
          <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700/50">
            <div className="text-2xl font-bold text-emerald-400">{Object.keys(stats.by_source).length}</div>
            <div className="text-xs text-gray-400">Sources</div>
          </div>
          <div className="bg-gray-800/50 rounded-xl p-3 border border-gray-700/50">
            <div className="text-2xl font-bold text-amber-400">{Object.keys(stats.by_status).length}</div>
            <div className="text-xs text-gray-400">Statuses</div>
          </div>
        </div>
      )}

      {/* Search + Filters */}
      <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 flex-1 min-w-[200px]">
            <Search size={16} className="text-gray-500 shrink-0" />
            <input
              type="text"
              placeholder="Search by name, email, company, title, phone..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 bg-transparent text-sm text-white placeholder-gray-500 outline-none"
            />
            {searchInput && (
              <button onClick={() => { setSearchInput(""); setSearch(""); setPage(1) }} className="text-gray-500 hover:text-white">
                <X size={14} />
              </button>
            )}
          </div>
          <button onClick={handleSearch} className="btn-primary text-xs px-3 py-1.5">Search</button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-ghost text-xs flex items-center gap-1 ${hasFilters ? "text-purple-400" : ""}`}
          >
            <Filter size={14} /> Filters {hasFilters && `(${[sourceFilter, statusFilter, minScore !== null].filter(Boolean).length})`}
          </button>
          {hasFilters && (
            <button onClick={clearFilters} className="text-xs text-gray-500 hover:text-white flex items-center gap-1">
              <X size={12} /> Clear
            </button>
          )}
        </div>

        {showFilters && (
          <div className="flex items-center gap-3 flex-wrap mt-3 pt-3 border-t border-gray-700/50">
            <div>
              <label className="text-[10px] text-gray-500 block mb-0.5">Source</label>
              <select value={sourceFilter} onChange={(e) => { setSourceFilter(e.target.value); setPage(1) }}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-white">
                <option value="">All Sources</option>
                {sources.map((s) => (
                  <option key={s} value={s}>{SOURCE_BADGES[s]?.label || s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 block mb-0.5">Status</label>
              <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-white">
                <option value="">All Statuses</option>
                {Object.entries(STATUS_BADGES).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 block mb-0.5">Min AI Score</label>
              <select value={minScore ?? ""} onChange={(e) => { setMinScore(e.target.value ? parseInt(e.target.value) : null); setPage(1) }}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-white">
                <option value="">Any Score</option>
                {[20, 40, 60, 80].map((s) => (
                  <option key={s} value={s}>{s}+</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Leads Table */}
      <div className="bg-gray-800/30 rounded-xl border border-gray-700/50 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <Loader size={24} className="animate-spin mx-auto text-gray-500 mb-2" />
            <p className="text-sm text-gray-500">Loading leads...</p>
          </div>
        ) : leads.length === 0 ? (
          <div className="p-12 text-center">
            <Users size={40} className="mx-auto text-gray-600 mb-3" />
            <p className="text-sm text-gray-400 mb-1">No leads found</p>
            <p className="text-xs text-gray-500">
              {hasFilters ? "Try adjusting your filters" : "Import leads via CSV, web scraping, or Apollo.io in the SDR wizard"}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50 bg-gray-800/50">
                  <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Contact</th>
                  <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Company</th>
                  <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Email</th>
                  <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Phone</th>
                  <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Industry</th>
                  <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Location</th>
                  <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Source</th>
                  <th className="text-center p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Score</th>
                  <th className="text-right p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Created</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((l) => {
                  const srcBadge = SOURCE_BADGES[l.source] || { label: l.source || "Unknown", color: "bg-gray-500/10 text-gray-400 border-gray-500/20" }
                  const stBadge = STATUS_BADGES[l.status] || { label: l.status || "New", color: "bg-gray-500/10 text-gray-400" }
                  const name = [l.first_name, l.last_name].filter(Boolean).join(" ") || l.email || "Unknown"
                  const locParts = [l.city, l.state, l.country].filter(Boolean)
                  const location = locParts.length > 0 ? locParts.join(", ") : l.location || "-"
                  return (
                    <tr key={l.id} className="border-b border-gray-700/30 hover:bg-white/[0.02] transition-colors">
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-xs font-medium text-purple-400 shrink-0">
                            {(l.first_name?.[0] || l.last_name?.[0] || l.email?.[0] || "?").toUpperCase()}
                          </div>
                          <div>
                            <div className="text-sm font-medium text-white">{name}</div>
                            {l.title && <div className="text-[11px] text-gray-500">{l.title}</div>}
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                        <div className="text-sm text-gray-300">{l.company || "-"}</div>
                        {l.company_size && <div className="text-[11px] text-gray-500">Size: {l.company_size}</div>}
                      </td>
                      <td className="p-3">
                        {l.email ? (
                          <a href={`mailto:${l.email}`} className="text-sm text-blue-400 hover:underline flex items-center gap-1">
                            <Mail size={12} /> {l.email}
                          </a>
                        ) : <span className="text-sm text-gray-600">-</span>}
                      </td>
                      <td className="p-3">
                        {l.phone ? (
                          <span className="text-sm text-gray-300 flex items-center gap-1">
                            <Phone size={12} className="text-gray-500" /> {l.phone}
                          </span>
                        ) : <span className="text-sm text-gray-600">-</span>}
                      </td>
                      <td className="p-3">
                        <span className="text-sm text-gray-300">{l.industry || "-"}</span>
                      </td>
                      <td className="p-3">
                        <span className="text-sm text-gray-300 flex items-center gap-1">
                          <MapPin size={12} className="text-gray-500 shrink-0" /> {location}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${srcBadge.color}`}>
                          {srcBadge.label}
                        </span>
                        <div className="mt-1">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${stBadge.color}`}>
                            {stBadge.label}
                          </span>
                        </div>
                      </td>
                      <td className="p-3 text-center">
                        {l.score ? (
                          <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 text-xs font-medium">
                            <Star size={10} /> {l.score}
                          </div>
                        ) : (
                          <span className="text-xs text-gray-600">-</span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {l.created_at ? new Date(l.created_at).toLocaleDateString("en-IN", {
                            day: "2-digit", month: "short", year: "numeric",
                          }) : "-"}
                        </span>
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
          <div className="flex items-center justify-between p-3 border-t border-gray-700/50 bg-gray-800/50">
            <span className="text-xs text-gray-500">
              Page {page} of {totalPages} ({total} leads)
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-xs rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                const start = Math.max(1, Math.min(page - 2, totalPages - 4))
                const p = start + i
                if (p > totalPages) return null
                return (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-7 h-7 rounded-lg text-xs font-medium ${
                      p === page ? "bg-purple-600 text-white" : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                    }`}
                  >
                    {p}
                  </button>
                )
              })}
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 text-xs rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
