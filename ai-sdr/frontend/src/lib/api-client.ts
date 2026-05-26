const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

class ApiClient {
  private token: string | null = null

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
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    }
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`
    }

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || "API request failed")
    }
    return res.json()
  }

  get<T>(path: string) {
    return this.request<T>(path)
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined })
  }

  put<T>(path: string, body?: unknown) {
    return this.request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined })
  }

  delete<T>(path: string) {
    return this.request<T>(path, { method: "DELETE" })
  }
}

export const api = new ApiClient()
