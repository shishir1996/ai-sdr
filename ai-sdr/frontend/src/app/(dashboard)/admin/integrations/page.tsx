"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Save, Key, Check, AlertCircle, ExternalLink, LogOut, ChevronDown, ChevronRight } from "lucide-react"

interface ProviderMeta {
  provider: string
  label: string
  description: string
  fields: { key: string; label: string; type: string; placeholder: string }[]
}

interface Integration {
  provider: string
  label: string
  is_active: boolean
  has_api_key: boolean
  has_api_secret: boolean
  has_refresh_token: boolean
}

export default function IntegrationsPage() {
  const [providers, setProviders] = useState<ProviderMeta[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [formData, setFormData] = useState<Record<string, Record<string, string>>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [saved, setSaved] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [providersData, integrationsData] = await Promise.all([
        api.get<ProviderMeta[]>("/admin/integrations/providers"),
        api.get<Integration[]>("/admin/integrations"),
      ])
      setProviders(providersData)
      setIntegrations(integrationsData)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleSave = async (provider: string) => {
    setSaving((prev) => ({ ...prev, [provider]: true }))
    setSaved((prev) => ({ ...prev, [provider]: false }))
    setError(null)
    try {
      const values = formData[provider] || {}
      await api.put(`/admin/integrations/${provider}`, {
        api_key: values.api_key || null,
        api_secret: values.api_secret || null,
        is_active: true,
      })
      setSaved((prev) => ({ ...prev, [provider]: true }))
      setTimeout(() => setSaved((prev) => ({ ...prev, [provider]: false })), 2000)
      await loadData()
      setFormData((prev) => {
        const next = { ...prev }
        delete next[provider]
        return next
      })
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSaving((prev) => ({ ...prev, [provider]: false }))
    }
  }

  const getIntegration = (provider: string) => integrations.find((i) => i.provider === provider)

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold">Integrations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure API keys for external services. Keys are encrypted at rest.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 text-red-600 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="space-y-4">
        {providers.map((provider) => {
          const integration = getIntegration(provider.provider)
          const isSaved = !!integration
          const isSaving = saving[provider.provider]
          const isSavedNotif = saved[provider.provider]

          return (
            <div key={provider.provider} className="card p-5">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{provider.label}</h3>
                    {isSaved && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-600">
                        <Check size={12} />
                        Configured
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{provider.description}</p>
                </div>
                <Key size={20} className="text-muted-foreground shrink-0" />
              </div>

              <div className="space-y-3">
                {provider.fields.map((field) => (
                  <div key={field.key}>
                    <label className="block text-sm font-medium mb-1">{field.label}</label>
                    <div className="relative">
                      <input
                        type={field.type}
                        placeholder={isSaved ? "•••••••• (replace to update)" : field.placeholder}
                        value={formData[provider.provider]?.[field.key] || ""}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            [provider.provider]: {
                              ...(prev[provider.provider] || {}),
                              [field.key]: e.target.value,
                            },
                          }))
                        }
                        className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 pr-10"
                      />
                    </div>
                  </div>
                ))}
              </div>

              {provider.provider === "gmail" && (
                <GmailSetupGuide />
              )}

              <div className="flex items-center justify-end mt-4 gap-2">
                {isSavedNotif && (
                  <span className="text-xs text-green-600 flex items-center gap-1">
                    <Check size={14} /> Saved
                  </span>
                )}
                {provider.provider === "gmail" && isSaved && (
                  <GmailConnectButton
                    hasRefreshToken={integration?.has_refresh_token || false}
                  />
                )}
                <button
                  onClick={() => handleSave(provider.provider)}
                  disabled={isSaving || !formData[provider.provider]}
                  className="btn-primary text-sm disabled:opacity-50"
                >
                  {isSaving ? (
                    <span className="flex items-center gap-1">
                      <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                      Saving...
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <Save size={16} />
                      {isSaved ? "Update" : "Save"}
                    </span>
                  )}
                </button>
              </div>
            </div>
          )
          })}
      </div>
    </div>
  )
}

function GmailSetupGuide() {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-4 border rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-4 py-2 text-left text-sm font-medium hover:bg-muted/50 transition-colors"
      >
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        How to get Gmail API credentials
      </button>
      {open && (
        <div className="px-4 pb-4 text-sm text-muted-foreground space-y-2 border-t pt-3">
          <ol className="list-decimal list-inside space-y-1.5">
            <li>Go to <a href="https://console.cloud.google.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">Google Cloud Console</a></li>
            <li>Create a new project or select existing one</li>
            <li>Enable the <strong>Gmail API</strong> from the API Library</li>
            <li>Go to <strong>Credentials</strong> → <strong>Create Credentials</strong> → <strong>OAuth 2.0 Client ID</strong></li>
            <li>Application type: <strong>Web application</strong></li>
            <li>Add redirect URI: <code className="bg-muted px-1 py-0.5 rounded text-xs">http://localhost:8000/api/v1/email/oauth-callback</code></li>
            <li>Copy the <strong>Client ID</strong> and <strong>Client Secret</strong> into the fields above</li>
            <li>Click <strong>Save</strong>, then click <strong>Connect Gmail</strong> to authorize</li>
          </ol>
          <p className="text-xs mt-2">
            Make sure the redirect URI matches your backend URL exactly.
            For production, use your actual domain instead of localhost.
          </p>
        </div>
      )}
    </div>
  )
}

function GmailConnectButton({ hasRefreshToken }: { hasRefreshToken: boolean }) {
  const [connecting, setConnecting] = useState(false)

  const startOAuth = async () => {
    setConnecting(true)
    try {
      const { auth_url } = await api.get<{ auth_url: string }>("/email/auth-url")
      window.open(auth_url, "_blank", "width=600,height=700")
    } catch (e: any) {
      alert(e.message)
    } finally {
      setConnecting(false)
    }
  }

  const disconnect = async () => {
    if (!confirm("Disconnect Gmail? You will need to re-authorize to send emails.")) return
    try {
      await api.put("/admin/integrations/gmail", { api_key: null, api_secret: null, is_active: false })
      window.location.reload()
    } catch (e: any) {
      alert(e.message)
    }
  }

  if (hasRefreshToken) {
    return (
      <button onClick={disconnect} className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm border border-red-500/30 text-red-500 hover:bg-red-500/10">
        <LogOut size={14} /> Disconnect
      </button>
    )
  }

  return (
    <button onClick={startOAuth} disabled={connecting} className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
      <ExternalLink size={14} /> {connecting ? "Opening..." : "Connect Gmail"}
    </button>
  )
}
