"use client"

import { motion } from "framer-motion"
import { AlertCircle, Activity } from "lucide-react"

export type SDRRunState = "running" | "idle" | "error" | "paused"

interface Props {
  state: SDRRunState
  label?: string
  pulsate?: boolean
}

const CONFIG: Record<SDRRunState, { color: string; bg: string; border: string }> = {
  running: { color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/30" },
  idle:    { color: "text-blue-400",    bg: "bg-blue-500/10",    border: "border-blue-500/30" },
  error:   { color: "text-red-400",     bg: "bg-red-500/10",     border: "border-red-500/30" },
  paused:  { color: "text-amber-400",   bg: "bg-amber-500/10",   border: "border-amber-500/30" },
}

export default function SDRStatusBadge({ state, label, pulsate = true }: Props) {
  const cfg = CONFIG[state]
  const isRunning = state === "running"

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.border} ${cfg.color}`}
    >
      {/* Gear icon - spins when running */}
      <motion.svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-3.5 h-3.5 shrink-0"
        animate={isRunning ? { rotate: 360 } : { rotate: 0 }}
        transition={isRunning ? { repeat: Infinity, duration: 2, ease: "linear" } : {}}
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </motion.svg>

      {/* Pulsing dot when running */}
      {isRunning && pulsate && (
        <span className="relative flex h-2 w-2">
          <motion.span
            className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"
            animate={{ scale: [1, 1.8, 1], opacity: [0.75, 0, 0.75] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
        </span>
      )}

      {/* Alert icon on error */}
      {state === "error" && <AlertCircle size={12} />}

      {/* Idle icon */}
      {state === "idle" && <Activity size={12} />}

      {label || state}
    </span>
  )
}
