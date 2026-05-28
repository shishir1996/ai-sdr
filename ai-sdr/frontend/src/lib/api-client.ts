export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://ai-sdr-production-7589.up.railway.app/api/v1"

interface ApiError {
  detail: string
  request_id?: string
}

class ApiClient {
  private token: string | null = null
  private refreshPromise: Promise<void> | null = null

  constructor() {
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("access_token")
    }
  }

  setToken(token: string) {
    this.token = token
    localStorage.setItem("access_token", token)
  }

  clearToken() {
    this.token = null
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const isFormData = options.body instanceof FormData
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers as Record<string, string>),
    }
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`
      headers["X-Organization-ID"] = localStorage.getItem("org_id") || ""
    }

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
    if (res.status === 401 && this.token) {
      const refreshed = await this.tryRefresh()
      if (refreshed) {
        headers["Authorization"] = `Bearer ${this.token}`
        const retryRes = await fetch(`${API_BASE}${path}`, { ...options, headers })
        if (retryRes.ok) return retryRes.json()
        const retryErr: ApiError = await retryRes.json().catch(() => ({ detail: retryRes.statusText }))
        throw new Error(retryErr.detail || "Request failed")
      }
      this.clearToken()
      if (typeof window !== "undefined") {
        window.location.href = "/login"
      }
      throw new Error("Session expired")
    }
    if (!res.ok) {
      const err: ApiError = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || "API request failed")
    }
    return res.json()
  }

  private async tryRefresh(): Promise<boolean> {
    if (this.refreshPromise) return this.refreshPromise.then(() => true).catch(() => false)
    const refreshToken = localStorage.getItem("refresh_token")
    if (!refreshToken) return false

    this.refreshPromise = (async () => {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (res.ok) {
        const data = await res.json()
        this.setToken(data.access_token)
        localStorage.setItem("refresh_token", data.refresh_token)
      } else {
        throw new Error("Refresh failed")
      }
    })()

    try {
      await this.refreshPromise
      return true
    } catch {
      return false
    } finally {
      this.refreshPromise = null
    }
  }

  get<T>(path: string) {
    return this.request<T>(path)
  }

  post<T>(path: string, body?: unknown, isFormData?: boolean) {
    return this.request<T>(path, {
      method: "POST",
      body: isFormData ? body as FormData : body ? JSON.stringify(body) : undefined,
    })
  }

  put<T>(path: string, body?: unknown) {
    return this.request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined })
  }

  delete<T>(path: string) {
    return this.request<T>(path, { method: "DELETE" })
  }
}

export const api = new ApiClient()
