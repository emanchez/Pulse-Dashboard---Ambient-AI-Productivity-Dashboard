"use client"

import React from "react"
import { BarChart2 } from "lucide-react"

interface FocusHeaderProps {
  silenceState: "engaged" | "stagnant" | "paused"
  pausedUntil?: string | null
}

export default function FocusHeader({ silenceState, pausedUntil }: FocusHeaderProps) {
  let subtitle = ""
  switch (silenceState) {
    case "engaged":
      subtitle = "Deep work session active. Distractions minimized."
      break
    case "stagnant":
      subtitle = "Momentum gap detected. Re-engage to restore flow."
      break
    case "paused":
      subtitle = `System paused${pausedUntil ? ` until ${new Date(pausedUntil).toLocaleDateString()}` : ""}.`
      break
  }

  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Focused Engagement</h1>
        <p className="text-slate-400 text-sm mt-1">{subtitle}</p>
      </div>
      <button className="flex items-center gap-2 border border-accent-border text-accent-light text-xs font-semibold px-4 py-2 rounded-lg hover:bg-accent-bg accent-transition">
        <BarChart2 size={14} /> SYSTEM MONITORING ACTIVE
      </button>
    </div>
  )
}
