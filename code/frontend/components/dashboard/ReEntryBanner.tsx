"use client"

import React, { useState } from "react"
import { RefreshCw, X } from "lucide-react"

interface ReEntryBannerProps {
  /** Set to true when the user is returning from leave/vacation (requiresRecovery) */
  visible: boolean
}

export default function ReEntryBanner({ visible }: ReEntryBannerProps) {
  const [dismissed, setDismissed] = useState(false)

  if (!visible || dismissed) return null

  return (
    <div className="bg-sky-500/10 border border-sky-500/30 rounded-lg px-4 py-3 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <RefreshCw size={14} className="text-sky-400 shrink-0" />
        <div>
          <p className="text-sky-300 text-sm font-medium">Welcome back!</p>
          <p className="text-sky-400/80 text-xs mt-0.5">
            Re-entry mode active — AI suggestions will prioritize low-friction tasks to help you ease back in.
          </p>
        </div>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="text-sky-500 hover:text-sky-300 transition-colors shrink-0"
        aria-label="Dismiss re-entry banner"
      >
        <X size={14} />
      </button>
    </div>
  )
}
