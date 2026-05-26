"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"

interface FeatureFlag {
  key: string
  enabled: boolean
  description: string | null
}

const flagLabels: Record<string, string> = {
  email_outreach_enabled: "Email Outreach",
  calls_enabled: "Phone Calls (VAPI.ai)",
  lead_extraction_apollo_enabled: "Apollo.io Lead Extraction",
  lead_extraction_web_enabled: "Web Scraping",
  lead_extraction_csv_enabled: "CSV Import",
  ai_lead_scoring_enabled: "AI Lead Scoring",
  ai_email_drafting_enabled: "AI Email Drafting",
  ai_call_script_enabled: "AI Call Script Generation",
}

export default function FeatureFlagsPage() {
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFlags()
  }, [])

  const fetchFlags = async () => {
    try {
      const data = await api.get<FeatureFlag[]>("/admin/feature-flags")
      setFlags(data)
    } catch (err) {
      console.error("Failed to fetch flags", err)
    } finally {
      setLoading(false)
    }
  }

  const toggleFlag = async (key: string, enabled: boolean) => {
    try {
      await api.put(`/admin/feature-flags/${key}`, { enabled })
      setFlags((prev) => prev.map((f) => (f.key === key ? { ...f, enabled } : f)))
    } catch (err) {
      console.error("Failed to update flag", err)
    }
  }

  if (loading) {
    return <div className="animate-pulse text-muted-foreground">Loading feature flags...</div>
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold">Admin - Feature Flags</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Enable or disable features across the platform. Disabled features are hidden from the UI and blocked at the API level.
        </p>
      </div>

      <div className="card divide-y">
        {flags.map((flag) => (
          <div key={flag.key} className="flex items-center justify-between px-5 py-4">
            <div>
              <p className="font-medium text-sm">{flagLabels[flag.key] || flag.key}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{flag.key}</p>
            </div>
            <button
              onClick={() => toggleFlag(flag.key, !flag.enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                flag.enabled ? "bg-brand-600" : "bg-border"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  flag.enabled ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
