"use client"

import React from "react"
import { Sparkles, Loader2, AlertTriangle } from "lucide-react"

interface SynthesisTriggerProps {
  onTrigger: () => void
  loading: boolean
  error: string | null
  rateLimitMessage: string | null
  disabled?: boolean
  usageText?: string
}

export default function SynthesisTrigger({
  onTrigger,
  loading,
  error,
  rateLimitMessage,
  disabled,
  usageText,
}: SynthesisTriggerProps) {
  return (
    <div className="bg-slate-800 rounded-xl p-5 flex flex-col items-center gap-2">
      <button
        onClick={onTrigger}
        disabled={loading || disabled || !!rateLimitMessage}
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Analyzing your week…
          </>
        ) : (
          <>
            <Sparkles size={16} />
            Generate Weekly Synthesis
          </>
        )}
      </button>

      {usageText && (
        <p className="text-xs text-slate-500">{usageText}</p>
      )}

      {rateLimitMessage && (
        <p className="text-amber-400 text-sm mt-1">{rateLimitMessage}</p>
      )}

      {error && !rateLimitMessage && (
        <div className="flex items-center gap-2 text-red-400 text-sm mt-1">
          <AlertTriangle size={14} />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
