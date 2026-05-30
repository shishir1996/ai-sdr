"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X, AlertTriangle, AlertCircle, Info, CheckCircle } from "lucide-react"

export interface Notification {
  id: string
  type: "error" | "warning" | "info" | "success"
  title: string
  message: string
  sdrName?: string
  action?: { label: string; href: string }
}

interface Props {
  notifications: Notification[]
  onDismiss: (id: string) => void
}

const ICONS = {
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
  success: CheckCircle,
}

const COLORS = {
  error: { border: "border-red-500/30", bg: "bg-red-500/10", icon: "text-red-400", text: "text-red-300" },
  warning: { border: "border-amber-500/30", bg: "bg-amber-500/10", icon: "text-amber-400", text: "text-amber-300" },
  info: { border: "border-blue-500/30", bg: "bg-blue-500/10", icon: "text-blue-400", text: "text-blue-300" },
  success: { border: "border-emerald-500/30", bg: "bg-emerald-500/10", icon: "text-emerald-400", text: "text-emerald-300" },
}

export default function SDRNotificationPanel({ notifications, onDismiss }: Props) {
  if (notifications.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      <AnimatePresence>
        {notifications.map((n) => {
          const Icon = ICONS[n.type]
          const c = COLORS[n.type]
          return (
            <motion.div
              key={n.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 100, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className={`pointer-events-auto rounded-xl border ${c.border} ${c.bg} backdrop-blur-xl p-4 shadow-2xl`}
            >
              <div className="flex items-start gap-3">
                <Icon size={18} className={`shrink-0 mt-0.5 ${c.icon}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className={`text-sm font-medium ${c.text}`}>{n.title}</p>
                    <button
                      onClick={() => onDismiss(n.id)}
                      className="text-gray-500 hover:text-gray-300 shrink-0"
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">{n.message}</p>
                  {n.action && (
                    <a
                      href={n.action.href}
                      className="inline-block mt-2 text-xs font-medium text-purple-400 hover:text-purple-300 underline underline-offset-2"
                    >
                      {n.action.label} →
                    </a>
                  )}
                </div>
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

/* ─── Hook to generate SDR notifications from status ─── */
export function useSDRNotifications(sdrs: any[], statusInfo: Record<string, any>) {
  const [notifications, setNotifications] = useState<Notification[]>([])

  useEffect(() => {
    const list: Notification[] = []
    for (const sdr of sdrs) {
      const st = statusInfo[sdr.id]
      if (!st) continue

      const sdrName = sdr.name || "AI SDR"

      // Error state
      if (st.current_status === "error") {
        list.push({
          id: `error-${sdr.id}`,
          type: "error",
          title: `${sdrName} encountered an error`,
          message: st.current_action || "Unknown error occurred",
          sdrName,
          action: { label: "View SDR", href: `/sdr/${sdr.id}` },
        })
      }

      // Misconfiguration warnings
      if (st.current_status === "inactive" && sdr.is_active) {
        list.push({
          id: `inactive-${sdr.id}`,
          type: "warning",
          title: `${sdrName} is inactive`,
          message: "SDR is active but no cycle is running. Check configuration.",
          sdrName,
          action: { label: "Fix settings", href: `/sdr/${sdr.id}` },
        })
      }

      if (!sdr.has_email && !sdr.has_linkedin) {
        list.push({
          id: `noconnect-${sdr.id}`,
          type: "warning",
          title: `${sdrName} not connected`,
          message: "No email or LinkedIn channels configured. Outreach cannot proceed.",
          sdrName,
          action: { label: "Configure channels", href: `/sdr/${sdr.id}?tab=settings` },
        })
      }

      // No leads
      if ((st.leads_processed || 0) === 0 && sdr.is_active) {
        list.push({
          id: `noleads-${sdr.id}`,
          type: "info",
          title: `${sdrName} has no leads`,
          message: "Import leads via CSV or configure lead sources to begin outreach.",
          sdrName,
          action: { label: "Add leads", href: `/sdr/setup` },
        })
      }
    }
    setNotifications(list.slice(0, 5))
  }, [sdrs, statusInfo])

  return notifications
}
