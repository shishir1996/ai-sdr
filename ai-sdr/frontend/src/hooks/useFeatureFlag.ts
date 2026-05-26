import { useState, useEffect } from "react"
import { api } from "@/lib/api-client"

interface FeatureFlag {
  key: string
  enabled: boolean
}

export function useFeatureFlag(flagKey: string) {
  const [enabled, setEnabled] = useState(true)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<FeatureFlag[]>(`/admin/feature-flags`)
      .then((flags) => {
        const flag = flags.find((f: FeatureFlag) => f.key === flagKey)
        setEnabled(flag ? flag.enabled : true)
      })
      .catch(() => setEnabled(true))
      .finally(() => setLoading(false))
  }, [flagKey])

  return { enabled, loading }
}
