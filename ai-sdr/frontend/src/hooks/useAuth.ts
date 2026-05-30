import { useState, useEffect, useCallback } from "react"
import { api } from "@/lib/api-client"

interface User {
  id: string
  email: string
  name: string
  role: string
  org_id: string
  phone?: string | null
  country_code?: string | null
  email_verified?: boolean
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem("access_token")
    if (!token) {
      setLoading(false)
      return
    }
    api.get<User>("/auth/me")
      .then((me) => {
        setUser(me)
        localStorage.setItem("org_id", me.org_id)
      })
      .catch(() => {
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<{ access_token: string; refresh_token: string }>("/auth/login", { email, password })
    api.setToken(data.access_token)
    localStorage.setItem("access_token", data.access_token)
    localStorage.setItem("refresh_token", data.refresh_token)
    const me = await api.get<User>("/auth/me")
    localStorage.setItem("org_id", me.org_id)
    setUser(me)
  }, [])

  const signup = useCallback(async (
    name: string,
    email: string,
    password: string,
    orgName: string,
    phone?: string,
    countryCode?: string,
  ) => {
    const data = await api.post<{ access_token: string; refresh_token: string }>("/auth/signup", {
      name, email, password, org_name: orgName, phone, country_code: countryCode,
    })
    api.setToken(data.access_token)
    localStorage.setItem("access_token", data.access_token)
    localStorage.setItem("refresh_token", data.refresh_token)
    const me = await api.get<User>("/auth/me")
    localStorage.setItem("org_id", me.org_id)
    setUser(me)
  }, [])

  const logout = useCallback(() => {
    api.clearToken()
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    localStorage.removeItem("org_id")
    setUser(null)
  }, [])

  const forgotPassword = useCallback(async (email: string) => {
    return api.post<{ message: string }>("/auth/forgot-password", { email })
  }, [])

  const resetPassword = useCallback(async (accessToken: string, newPassword: string) => {
    return api.post<{ message: string }>("/auth/reset-password", {
      access_token: accessToken,
      new_password: newPassword,
    })
  }, [])

  const updateProfile = useCallback(async (data: { name?: string; phone?: string; country_code?: string }) => {
    const updated = await api.put<User>("/auth/profile", data)
    setUser((prev) => prev ? { ...prev, ...updated } : null)
    return updated
  }, [])

  return { user, loading, login, signup, logout, forgotPassword, resetPassword, updateProfile }
}
