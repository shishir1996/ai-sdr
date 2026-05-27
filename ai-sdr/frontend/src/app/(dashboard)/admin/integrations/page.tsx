"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"
import { Save, Key, Check, AlertCircle, ExternalLink, ChevronDown, ChevronRight, Cpu, ChevronsUpDown, Loader, LogOut } from "lucide-react"

interface ProviderMeta {
  provider: string
  label: string
  description: string
  fields: { key: string; label: string; type: string; placeholder: string }[]
  warning?: string
}

interface Integration {
  provider: string
  label: string
  is_active: boolean
  has_api_key: boolean
  has_api_secret: boolean
  has_refresh_token: boolean
  extra_config?: Record<string, string> | null
}

interface AiModel {
  model_id: string
  display_name: string
  provider: string
  max_tokens: number
  cost_per_1k_input: number
  cost_per_1k_output: number
}

const AI_PROVIDERS = ["together_ai", "openai", "anthropic", "google_ai", "openrouter"]

const AI_PROVIDER_LABELS: Record<string, string> = {
  together_ai: "Together AI",
  openai: "OpenAI",
  anthropic: "Anthropic (Claude)",
  google_ai: "Google AI (Gemini)",
  openrouter: "OpenRouter",
}

const AI_PROVIDER_DESCRIPTIONS: Record<string, string> = {
  together_ai: "Llama 3.1, Mixtral, and other open models via Together AI",
  openai: "GPT-4o, GPT-4o Mini, GPT-3.5 Turbo",
  anthropic: "Claude 3.5 Sonnet, Claude 3 Haiku",
  google_ai: "Gemini 1.5 Pro, Gemini 1.5 Flash",
  openrouter: "200+ models including DeepSeek, Claude, GPT, Gemini via one API",
}

const AI_PROVIDER_LOGOS: Record<string, string> = {
  together_ai: "🧠",
  openai: "⚡",
  anthropic: "🌿",
  google_ai: "🔮",
  openrouter: "🌐",
}

export default function IntegrationsPage() {
  const [providers, setProviders] = useState<ProviderMeta[]>([])
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [formData, setFormData] = useState<Record<string, Record<string, string>>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [saved, setSaved] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)

  // AI provider config state
  const [selectedProvider, setSelectedProvider] = useState<string>("openrouter")
  const [availableModels, setAvailableModels] = useState<AiModel[]>([])
  const [selectedModel, setSelectedModel] = useState<string>("deepseek-v4-flash-free")
  const [aiApiKey, setAiApiKey] = useState("")
  const [loadingModels, setLoadingModels] = useState(false)
  const [savingAi, setSavingAi] = useState(false)
  const [aiSaved, setAiSaved] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (integrations.length > 0) {
      const savedAi = integrations.find(i => AI_PROVIDERS.includes(i.provider) && i.has_api_key)
      if (savedAi) {
        setSelectedProvider(savedAi.provider)
        setAiApiKey("")
        if (savedAi.extra_config?.model) {
          setSelectedModel(savedAi.extra_config.model)
        }
      }
    }
  }, [integrations])

  useEffect(() => {
    fetchModels(selectedProvider)
  }, [selectedProvider])

  const fetchModels = async (provider: string) => {
    setLoadingModels(true)
    setAvailableModels([])
    try {
      const models = await api.get<AiModel[]>(`/admin/integrations/ai/models?provider=${provider}`)
      setAvailableModels(models)
      const savedAi = integrations.find(i => i.provider === provider && i.extra_config?.model)
      if (savedAi?.extra_config?.model) {
        setSelectedModel(savedAi.extra_config.model)
      } else if (models.length > 0) {
        setSelectedModel(models[0].model_id)
      }
    } catch {
      setAvailableModels([])
    } finally {
      setLoadingModels(false)
    }
  }

  const handleSaveAi = async () => {
    setSavingAi(true)
    setAiSaved(false)
    setError(null)
    try {
      await api.put(`/admin/integrations/${selectedProvider}`, {
        api_key: aiApiKey || null,
        model: selectedModel,
        is_active: true,
      })
      setAiSaved(true)
      setAiApiKey("")
      setTimeout(() => setAiSaved(false), 2000)
      await loadData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSavingAi(false)
    }
  }

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

  const otherProviders = providers.filter((p) => !AI_PROVIDERS.includes(p.provider))

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold">Integrations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure API keys for external services. Keys are encrypted at rest and never exposed.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 text-red-600 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="space-y-4">
        {/* AI Providers Section */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Cpu size={18} className="text-purple-500" />
            <h2 className="text-lg font-semibold">AI Configuration</h2>
            <span className="text-xs text-muted-foreground">Choose provider, model, and enter API key</span>
          </div>

          <div className="card p-5 border-purple-500/20 space-y-5">
            {/* Provider Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">AI Provider</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                {AI_PROVIDERS.map((p) => {
                  const saved = integrations.find(i => i.provider === p)
                  const isActive = selectedProvider === p
                  return (
                    <button
                      key={p}
                      onClick={() => { setSelectedProvider(p); setAiApiKey("") }}
                      className={`relative flex flex-col items-center gap-1.5 p-3 rounded-xl border text-sm transition-all ${
                        isActive
                          ? "border-purple-500 bg-purple-500/10 text-white"
                          : "border-white/10 bg-white/5 text-gray-400 hover:border-white/20 hover:text-gray-300"
                      }`}
                    >
                      <span className="text-lg">{AI_PROVIDER_LOGOS[p]}</span>
                      <span className="font-medium text-xs text-center">{AI_PROVIDER_LABELS[p]}</span>
                      {saved?.has_api_key && (
                        <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                          <Check size={10} className="text-white" />
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Model Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">
                AI Model
                {loadingModels && <Loader size={12} className="inline ml-2 animate-spin text-purple-400" />}
              </label>
              {availableModels.length > 0 ? (
                <div className="relative">
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-white/10 bg-white/5 text-sm appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-white"
                  >
                    {availableModels.map((m) => {
                      const saved = integrations.find(i => i.provider === selectedProvider)
                      const isModelSaved = saved?.extra_config?.model === m.model_id
                      return (
                        <option key={m.model_id} value={m.model_id} className="bg-gray-900 text-white">
                          {m.display_name} {isModelSaved ? "✓" : ""}
                          {m.cost_per_1k_input > 0 ? ` ($${m.cost_per_1k_input}/1K input)` : " (Free)"}
                        </option>
                      )
                    })}
                  </select>
                  <ChevronsUpDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              ) : (
                !loadingModels && (
                  <div className="px-3 py-2.5 rounded-xl border border-dashed border-white/10 text-sm text-gray-500">
                    {selectedProvider === "openrouter"
                      ? "OpenRouter supports 200+ models. Select after entering API key or use the default."
                      : "No models available for this provider"}
                  </div>
                )
              )}
            </div>

            {/* API Key */}
            <div>
              <label className="block text-sm font-medium mb-2">API Key</label>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Key size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="password"
                    placeholder={integrations.find(i => i.provider === selectedProvider)?.has_api_key ? "•••••••• (leave blank to keep existing)" : `Enter ${AI_PROVIDER_LABELS[selectedProvider]} API key`}
                    value={aiApiKey}
                    onChange={(e) => setAiApiKey(e.target.value)}
                    className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-white/10 bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                </div>
              </div>
              {integrations.find(i => i.provider === selectedProvider)?.has_api_key && (
                <p className="text-xs text-emerald-500 mt-1.5 flex items-center gap-1">
                  <Check size={12} /> API key already saved for this provider
                </p>
              )}
            </div>

            {/* Save Button */}
            <div className="flex items-center justify-end gap-3 pt-1">
              {aiSaved && (
                <span className="text-xs text-green-500 flex items-center gap-1"><Check size={14} /> AI configuration saved</span>
              )}
              <button
                onClick={handleSaveAi}
                disabled={savingAi}
                className="btn-primary text-sm px-6"
              >
                {savingAi ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                    Saving...
                  </span>
                ) : (
                  <span className="flex items-center gap-2"><Save size={16} /> Save AI Configuration</span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Other Providers Section */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Other Services</h2>
          <div className="space-y-3">
            {otherProviders.map((provider) => {
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
                            <Check size={12} /> Configured
                          </span>
                        )}
                        {provider.warning && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-600">
                            <AlertCircle size={12} /> Warning
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{provider.description}</p>
                    </div>
                    <Key size={20} className="text-muted-foreground shrink-0" />
                  </div>

                  {provider.warning && (
                    <div className="mb-3 p-2 rounded bg-amber-500/5 border border-amber-500/20 text-xs text-amber-600">
                      {provider.warning}
                    </div>
                  )}

                  <div className="space-y-3">
                    {provider.fields.map((field) => (
                      <div key={field.key}>
                        <label className="block text-sm font-medium mb-1">{field.label}</label>
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
                          className="w-full px-3 py-2 rounded-lg border bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                        />
                      </div>
                    ))}
                  </div>

                  {provider.provider === "gmail" && <GmailSetupGuide />}
                  {provider.provider === "outlook" && <OutlookSetupGuide />}

                  <div className="flex items-center justify-end mt-4 gap-2">
                    {isSavedNotif && (
                      <span className="text-xs text-green-600 flex items-center gap-1"><Check size={14} /> Saved</span>
                    )}
                    {provider.provider === "gmail" && isSaved && (
                      <GmailConnectButton hasRefreshToken={integration?.has_refresh_token || false} />
                    )}
                    {provider.provider === "outlook" && isSaved && (
                      <OutlookConnectButton />
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
                        <span className="flex items-center gap-1"><Save size={16} /> {isSaved ? "Update" : "Save"}</span>
                      )}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
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
            <li>Add redirect URI: <code className="bg-muted px-1 py-0.5 rounded text-xs">https://api.offdx.in/api/v1/email/oauth-callback</code></li>
            <li>Copy the <strong>Client ID</strong> and <strong>Client Secret</strong> into the fields above</li>
            <li>Click <strong>Save</strong>, then click <strong>Connect Gmail</strong> to authorize</li>
          </ol>
          <p className="text-xs mt-2">
            For development, use http://localhost:8000/api/v1/email/oauth-callback.
            For production, use https://api.offdx.in/api/v1/email/oauth-callback.
          </p>
        </div>
      )}
    </div>
  )
}

function OutlookSetupGuide() {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-4 border rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-4 py-2 text-left text-sm font-medium hover:bg-muted/50 transition-colors"
      >
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        How to get Outlook / Microsoft 365 API credentials
      </button>
      {open && (
        <div className="px-4 pb-4 text-sm text-muted-foreground space-y-2 border-t pt-3">
          <ol className="list-decimal list-inside space-y-1.5">
            <li>Go to <a href="https://portal.azure.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">Azure Portal</a> → <strong>App Registrations</strong></li>
            <li>Click <strong>New Registration</strong>, name it "AI SDR"</li>
            <li>Supported account types: <strong>Accounts in any organizational directory and personal Microsoft accounts</strong></li>
            <li>Redirect URI (dev): Web → <code className="bg-muted px-1 py-0.5 rounded text-xs">http://localhost:8000/api/v1/email/sdr-outlook-oauth-callback/{'{'}sdr_profile_id{'}'}</code></li>
            <li>Redirect URI (prod): Web → <code className="bg-muted px-1 py-0.5 rounded text-xs">https://api.offdx.in/api/v1/email/sdr-outlook-oauth-callback/{'{'}sdr_profile_id{'}'}</code></li>
            <li>After creation, copy the <strong>Application (Client) ID</strong> → this is your <strong>Client ID</strong></li>
            <li>Go to <strong>Certificates & Secrets</strong> → <strong>New Client Secret</strong> → copy the value → this is your <strong>Client Secret</strong></li>
            <li>Go to <strong>API Permissions</strong> → Add permission → <strong>Microsoft Graph</strong> → <strong>Delegated Permissions</strong></li>
            <li>Add: <code className="bg-muted px-1 py-0.5 rounded text-xs">Mail.Send</code>, <code className="bg-muted px-1 py-0.5 rounded text-xs">Mail.Read</code>, <code className="bg-muted px-1 py-0.5 rounded text-xs">User.Read</code>, <code className="bg-muted px-1 py-0.5 rounded text-xs">offline_access</code></li>
            <li>Click <strong>Grant Admin Consent</strong> (requires admin privileges)</li>
            <li>Enter the <strong>Client ID</strong> and <strong>Client Secret</strong> above, then each SDR connects their own Outlook via the SDR wizard</li>
          </ol>
          <p className="text-xs mt-2">
            Each SDR profile uses its own redirect URI. Add as many redirect URIs as SDRs you need, or use a single generic URI pattern.
          </p>
        </div>
      )}
    </div>
  )
}

function OutlookConnectButton() {
  const [connecting, setConnecting] = useState(false)

  const startOAuth = async () => {
    setConnecting(true)
    try {
      alert("Outlook OAuth for the global account is configured via the SDR wizard. Each SDR connects their own Outlook mailbox individually.")
    } catch (e: any) {
      alert(e.message)
    } finally {
      setConnecting(false)
    }
  }

  return (
    <button onClick={startOAuth} className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
      <ExternalLink size={14} /> Per-SDR via SDR Wizard
    </button>
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
