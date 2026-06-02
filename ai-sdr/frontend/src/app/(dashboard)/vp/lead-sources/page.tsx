"use client"

import { useEffect, useState } from "react"
import { api } from "@/lib/api-client"

const SOURCE_LABELS: Record<string, string> = {
  google_search: "Google Search",
  bing_search: "Bing Search",
  web_research: "Web Research",
  business_directories: "Business Directories",
  company_websites: "Company Websites",
  google_maps_scraping: "Google Maps Scraping",
  apollo: "Apollo.io",
  lusha: "Lusha",
  rocketreach: "RocketReach",
  zoominfo: "ZoomInfo",
  linkedin_data: "LinkedIn Data Sources",
  news_sites: "News Sites",
  startup_directories: "Startup Directories",
  industry_listings: "Industry Listings",
}

const SOURCE_CATEGORIES: Record<string, string[]> = {
  "Web Research": ["google_search", "bing_search", "web_research", "news_sites"],
  "Directories": ["business_directories", "company_websites", "startup_directories", "industry_listings"],
  "Paid Providers": ["apollo", "lusha", "rocketreach", "zoominfo"],
  "Platform Data": ["linkedin_data", "google_maps_scraping"],
}

export default function VPLeadSourcesPage() {
  const [sources, setSources] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await api.get<{ sources: Record<string, boolean> }>("/lead-sources/")
      setSources(res.sources || {})
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const toggle = async (key: string) => {
    const updated = { ...sources, [key]: !sources[key] }
    setSources(updated)
    try {
      await api.put("/lead-sources/", { [key]: updated[key] })
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Lead Source Control Panel</h1>
        <p className="text-sm text-gray-400 mt-1">
          Toggle lead sources on or off. The VP and research agents will only use enabled sources.
          Disabled sources are enforced server-side.
        </p>
      </div>

      <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
        <p className="text-sm text-amber-400">
          Security: Source toggles are validated server-side. Disabling a source completely blocks agent access at the API and service layer.
        </p>
      </div>

      {Object.entries(SOURCE_CATEGORIES).map(([category, keys]) => (
        <div key={category} className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
          <h2 className="text-lg font-semibold text-white mb-3">{category}</h2>
          <div className="space-y-2">
            {keys.map((key) => {
              if (!(key in sources)) return null
              return (
                <div key={key} className="flex items-center justify-between py-1.5">
                  <label className="text-sm text-gray-300" htmlFor={`switch-${key}`}>
                    {SOURCE_LABELS[key] || key}
                  </label>
                  <button
                    id={`switch-${key}`}
                    onClick={() => toggle(key)}
                    className={`relative w-10 h-5 rounded-full transition-colors ${
                      sources[key] ? "bg-emerald-600" : "bg-gray-600"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                        sources[key] ? "translate-x-5" : "translate-x-0"
                      }`}
                    />
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      <div className="p-4 bg-[#1a1a2e] rounded-lg border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400 mb-2">What happens when you disable a source?</h2>
        <ul className="space-y-1 text-sm text-gray-500">
          <li>• Research agents will skip that source during discovery</li>
          <li>• The VP decision engine will not assign that source to agents</li>
          <li>• API-level checks prevent any code from accessing disabled sources</li>
          <li>• All source usage is audit-logged</li>
        </ul>
      </div>
    </div>
  )
}
