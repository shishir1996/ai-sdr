"use client"

import { useState, useEffect, useCallback } from "react"
import { api, API_BASE } from "@/lib/api-client"
import {
  Users, Search, RefreshCw, Mail, Phone, MapPin, Star, X, Filter,
  Download, Loader, Trash2, ChevronDown, CheckSquare, Square, AlertTriangle,
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
  source: string
  status: string
  score: number
  website: string
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
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState("")
  const [pageLeadsIds, setPageLeadsIds] = useState<string[]>([])
  const perPage = 25

  useEffect(() => { load(); loadStats() }, [])

  useEffect(() => { load() }, [page, sourceFilter, statusFilter, minScore])

  const loadStats = async () => {
    try { setStats(await api.get("/leads/stats")) } catch {}
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
      const items = r.items || []
      setLeads(items)
      setPageLeadsIds(items.map((l: LeadRecord) => l.id))
      setTotal(r.total || 0)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const handleSearch = useCallback(() => {
    setSearch(searchInput)
    setPage(1)
    setSelected(new Set())
  }, [searchInput])

  const clearFilters = () => {
    setSearch(""); setSearchInput(""); setSourceFilter(""); setStatusFilter(""); setMinScore(null)
    setPage(1); setSelected(new Set())
  }

  const totalPages = Math.ceil(total / perPage)
  const hasFilters = search || sourceFilter || statusFilter || minScore !== null
  const sources = stats?.by_source ? Object.keys(stats.by_source).sort() : []

  const allSelectedOnPage = pageLeadsIds.length > 0 && pageLeadsIds.every(id => selected.has(id))

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (allSelectedOnPage) {
      setSelected(prev => {
        const next = new Set(prev)
        pageLeadsIds.forEach(id => next.delete(id))
        return next
      })
    } else {
      setSelected(prev => {
        const next = new Set(prev)
        pageLeadsIds.forEach(id => next.add(id))
        return next
      })
    }
  }

  const deleteSelected = async () => {
    if (selected.size === 0) return
    if (!confirm(`Delete ${selected.size} selected lead(s)?`)) return
    setDeleting(true)
    setActionError("")
    try {
      await api.post("/leads/bulk-delete", { ids: Array.from(selected) })
      setSelected(new Set())
      load()
      loadStats()
    } catch (e: any) { setActionError(e.message || "Delete failed") }
    finally { setDeleting(false) }
  }

  const deleteSingle = async (id: string, name: string) => {
    if (!confirm(`Delete lead "${name}"?`)) return
    setActionError("")
    try {
      await api.delete(`/leads/${id}`)
      setSelected(prev => { const n = new Set(prev); n.delete(id); return n })
      load()
      loadStats()
    } catch (e: any) { setActionError(e.message || "Delete failed") }
  }

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20">
            <Users size={22} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Leads</h1>
            <p className="text-sm text-gray-400">{total} total leads</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a href={`${API_BASE}/leads/sample-csv`} target="_blank" rel="noopener noreferrer"
            className="btn-ghost text-xs flex items-center gap-1 px-3 py-1.5">
            <Download size={14} /> Sample CSV
          </a>
          <button onClick={() => { load(); loadStats() }} className="btn-secondary text-sm flex items-center gap-2 px-3 py-1.5">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
            <div className="text-2xl font-bold text-white">{stats.total}</div>
            <div className="text-xs text-gray-400 mt-0.5">Total Leads</div>
          </div>
          <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
            <div className="text-2xl font-bold text-purple-400">{stats.scored}</div>
            <div className="text-xs text-gray-400 mt-0.5">AI Scored</div>
          </div>
          <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
            <div className="text-2xl font-bold text-emerald-400">{Object.keys(stats.by_source).length}</div>
            <div className="text-xs text-gray-400 mt-0.5">Sources</div>
          </div>
          <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
            <div className="text-2xl font-bold text-amber-400">{Object.keys(stats.by_status).length}</div>
            <div className="text-xs text-gray-400 mt-0.5">Statuses</div>
          </div>
        </div>
      )}

      {/* Search + Filters + Bulk Actions */}
      <div className="bg-gray-800/20 rounded-xl border border-gray-700/50 p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 bg-gray-900/60 border border-gray-700 rounded-lg px-3 py-1.5 flex-1 min-w-[200px]">
            <Search size={14} className="text-gray-500 shrink-0" />
            <input type="text" placeholder="Search by name, email, company..."
              value={searchInput} onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 bg-transparent text-sm text-white placeholder-gray-500 outline-none" />
            {searchInput && (
              <button onClick={() => { setSearchInput(""); setSearch(""); setPage(1); setSelected(new Set()) }} className="text-gray-500 hover:text-white">
                <X size={14} />
              </button>
            )}
          </div>
          <button onClick={handleSearch} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition-all">Search</button>
          <button onClick={() => setShowFilters(!showFilters)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
              hasFilters ? "bg-purple-600/20 text-purple-400 border border-purple-500/30" : "bg-gray-700/50 text-gray-400 border border-gray-600/30 hover:bg-gray-700"
            }`}>
            <Filter size={12} /> Filters {hasFilters && `(${[sourceFilter, statusFilter, minScore !== null].filter(Boolean).length})`}
          </button>
          {hasFilters && (
            <button onClick={clearFilters} className="text-xs text-gray-500 hover:text-white flex items-center gap-1">
              <X size={12} /> Clear
            </button>
          )}

          {/* Bulk delete */}
          {selected.size > 0 && (
            <button onClick={deleteSelected} disabled={deleting}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ml-auto">
              <Trash2 size={12} />
              {deleting ? "Deleting..." : `Delete ${selected.size}`}
            </button>
          )}
        </div>

        {showFilters && (
          <div className="flex items-center gap-3 flex-wrap mt-3 pt-3 border-t border-gray-700/50">
            <div>
              <label className="text-[10px] text-gray-500 block mb-0.5">Source</label>
              <select value={sourceFilter} onChange={(e) => { setSourceFilter(e.target.value); setPage(1); setSelected(new Set()) }}
                className="bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5 text-xs text-white">
                <option value="">All Sources</option>
                {sources.map((s) => (
                  <option key={s} value={s}>{SOURCE_BADGES[s]?.label || s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 block mb-0.5">Status</label>
              <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); setSelected(new Set()) }}
                className="bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5 text-xs text-white">
                <option value="">All Statuses</option>
                {Object.entries(STATUS_BADGES).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 block mb-0.5">Min AI Score</label>
              <select value={minScore ?? ""} onChange={(e) => { setMinScore(e.target.value ? parseInt(e.target.value) : null); setPage(1); setSelected(new Set()) }}
                className="bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5 text-xs text-white">
                <option value="">Any Score</option>
                {[20, 40, 60, 80].map((s) => (
                  <option key={s} value={s}>{s}+</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {actionError && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
          <AlertTriangle size={14} className="shrink-0" />
          <span className="flex-1">{actionError}</span>
          <button onClick={() => setActionError("")} className="text-red-400 hover:text-red-300"><X size={14} /></button>
        </div>
      )}

      {/* Leads Table */}
      <div className="bg-gray-800/20 rounded-xl border border-gray-700/50 overflow-hidden">
        {loading ? (
          <div className="p-16 text-center">
            <Loader size={24} className="animate-spin mx-auto text-gray-500 mb-3" />
            <p className="text-sm text-gray-500">Loading leads...</p>
          </div>
        ) : leads.length === 0 ? (
          <div className="p-16 text-center">
            <Users size={48} className="mx-auto text-gray-600 mb-3" />
            <p className="text-sm text-gray-400 mb-1">No leads found</p>
            <p className="text-xs text-gray-500">
              {hasFilters ? "Try adjusting your filters" : "Use the AI Sales Team to research and find leads"}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700/50 bg-gray-800/40">
                    <th className="p-3 w-10">
                      <button onClick={toggleSelectAll} className="text-gray-500 hover:text-white transition-colors">
                        {allSelectedOnPage ? <CheckSquare size={16} className="text-blue-400" /> : <Square size={16} />}
                      </button>
                    </th>
                    <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Contact</th>
                    <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Company</th>
                    <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Email</th>
                    <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider">Phone</th>
                    <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider hidden md:table-cell">Industry</th>
                    <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider hidden lg:table-cell">Location</th>
                    <th className="text-left p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider hidden sm:table-cell">Source</th>
                    <th className="text-center p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider hidden sm:table-cell">Score</th>
                    <th className="text-right p-3 font-medium text-[11px] text-gray-400 uppercase tracking-wider hidden xl:table-cell">Created</th>
                    <th className="p-3 w-10"></th>
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
                      <tr key={l.id} className={`border-b border-gray-700/30 hover:bg-white/[0.02] transition-colors ${selected.has(l.id) ? "bg-blue-500/5" : ""}`}>
                        <td className="p-3">
                          <button onClick={() => toggleSelect(l.id)} className="text-gray-500 hover:text-white transition-colors">
                            {selected.has(l.id)
                              ? <CheckSquare size={16} className="text-blue-400" />
                              : <Square size={16} />}
                          </button>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500/10 to-blue-500/10 border border-purple-500/20 flex items-center justify-center text-xs font-medium text-purple-400 shrink-0">
                              {(l.first_name?.[0] || l.last_name?.[0] || l.email?.[0] || "?").toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <div className="text-sm font-medium text-white truncate">{name}</div>
                              {l.title && <div className="text-[11px] text-gray-500 truncate">{l.title}</div>}
                            </div>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="text-sm text-gray-300 truncate max-w-[150px]">{l.company || "-"}</div>
                          {l.company_size && <div className="text-[11px] text-gray-500">Size: {l.company_size}</div>}
                        </td>
                        <td className="p-3">
                          {l.email ? (
                            <a href={`mailto:${l.email}`} className="text-sm text-blue-400 hover:underline flex items-center gap-1.5 truncate max-w-[180px]">
                              <Mail size={11} className="shrink-0" /> {l.email}
                            </a>
                          ) : <span className="text-sm text-gray-600">-</span>}
                        </td>
                        <td className="p-3">
                          {l.phone ? (
                            <span className="text-sm text-gray-300 flex items-center gap-1.5">
                              <Phone size={11} className="text-gray-500 shrink-0" /> {l.phone}
                            </span>
                          ) : <span className="text-sm text-gray-600">-</span>}
                        </td>
                        <td className="p-3 hidden md:table-cell">
                          <span className="text-sm text-gray-300">{l.industry || "-"}</span>
                        </td>
                        <td className="p-3 hidden lg:table-cell">
                          <span className="text-sm text-gray-300 flex items-center gap-1.5">
                            <MapPin size={11} className="text-gray-500 shrink-0" /> {location}
                          </span>
                        </td>
                        <td className="p-3 hidden sm:table-cell">
                          <div className="flex flex-col gap-1">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full border w-fit ${srcBadge.color}`}>{srcBadge.label}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded w-fit ${stBadge.color}`}>{stBadge.label}</span>
                          </div>
                        </td>
                        <td className="p-3 text-center hidden sm:table-cell">
                          {l.score ? (
                            <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 text-xs font-medium">
                              <Star size={10} /> {l.score}
                            </div>
                          ) : (
                            <span className="text-xs text-gray-600">-</span>
                          )}
                        </td>
                        <td className="p-3 text-right hidden xl:table-cell">
                          <span className="text-xs text-gray-500 whitespace-nowrap">
                            {l.created_at ? new Date(l.created_at).toLocaleDateString("en-IN", {
                              day: "2-digit", month: "short", year: "numeric",
                            }) : "-"}
                          </span>
                        </td>
                        <td className="p-3">
                          <button onClick={() => deleteSingle(l.id, name)}
                            className="text-gray-600 hover:text-red-400 transition-colors p-1">
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Selection bar */}
            {selected.size > 0 && (
              <div className="flex items-center justify-between px-4 py-2.5 bg-blue-600/10 border-t border-blue-600/30">
                <span className="text-xs text-blue-300">
                  <strong className="text-white">{selected.size}</strong> lead{selected.size !== 1 ? "s" : ""} selected
                  {selected.size === total && pageLeadsIds.length < total ? ` (all ${total} leads)` : ""}
                </span>
                <div className="flex gap-2">
                  <button onClick={() => setSelected(new Set())}
                    className="text-xs text-blue-300 hover:text-white transition-colors">Deselect All</button>
                  <button onClick={deleteSelected} disabled={deleting}
                    className="text-xs text-red-400 hover:text-red-300 transition-colors flex items-center gap-1">
                    <Trash2 size={11} />
                    {deleting ? "Deleting..." : `Delete ${selected.size}`}
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-4 border-t border-gray-700/50 bg-gray-800/40">
            <span className="text-xs text-gray-500">
              Page {page} of {totalPages} ({total} leads)
            </span>
            <div className="flex items-center gap-1">
              <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}
                className="px-3 py-1.5 text-xs rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all">
                Previous
              </button>
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                const start = Math.max(1, Math.min(page - 2, totalPages - 4))
                const p = start + i
                if (p > totalPages) return null
                return (
                  <button key={p} onClick={() => setPage(p)}
                    className={`w-8 h-8 rounded-lg text-xs font-medium transition-all ${
                      p === page ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                    }`}>{p}</button>
                )
              })}
              <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page === totalPages}
                className="px-3 py-1.5 text-xs rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all">
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
