"use client"

import React, { useState } from "react"
import { CheckCircle2, ChevronRight } from "lucide-react"
import type { SuggestedTask } from "../../lib/api"

const PRIORITY_COLORS: Record<string, { text: string; bg: string }> = {
  High: { text: "text-red-400", bg: "bg-red-500/20 border border-red-500/30" },
  Medium: { text: "text-amber-400", bg: "bg-amber-500/20 border border-amber-500/30" },
  Low: { text: "text-emerald-400", bg: "bg-emerald-500/20 border border-emerald-500/30" },
}

interface TaskSuggestionListProps {
  suggestions: SuggestedTask[]
  onAccept: (task: SuggestedTask) => Promise<void>
  onDismiss: (index: number) => void
  isReEntryMode: boolean
}

export default function TaskSuggestionList({
  suggestions,
  onAccept,
  onDismiss,
  isReEntryMode,
}: TaskSuggestionListProps) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)
  const [acceptedIdxs, setAcceptedIdxs] = useState<Set<number>>(new Set())
  const [loadingIdx, setLoadingIdx] = useState<number | null>(null)

  if (suggestions.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl p-8 text-center">
        <p className="text-slate-400 text-sm">
          Trigger a synthesis to generate task recommendations.
        </p>
      </div>
    )
  }

  const handleAccept = async (task: SuggestedTask, idx: number) => {
    setLoadingIdx(idx)
    try {
      await onAccept(task)
      setAcceptedIdxs((prev) => new Set(prev).add(idx))
    } catch {
      // Error handled by parent
    } finally {
      setLoadingIdx(null)
    }
  }

  return (
    <div className="space-y-2">
      <span className="text-accent-light text-xs font-bold tracking-widest uppercase mb-3 block accent-transition">
        SUGGESTED TASKS
      </span>

      {isReEntryMode && (
        <div className="bg-sky-500/10 border border-sky-500/30 rounded-lg px-4 py-3 text-sky-300 text-sm mb-3">
          Re-entry mode active — showing low-friction tasks to ease you back in.
        </div>
      )}

      {suggestions.map((task, idx) => {
        if (acceptedIdxs.has(idx)) {
          return (
            <div
              key={idx}
              className="bg-slate-800 rounded-lg px-4 py-3 flex items-center gap-2 text-emerald-400 text-sm"
            >
              <CheckCircle2 size={16} />
              <span>Added to queue — {task.name}</span>
            </div>
          )
        }

        const colors = PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.Medium
        const isExpanded = expandedIdx === idx

        return (
          <div key={idx} className="bg-slate-800 rounded-lg px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                  {task.priority}
                </span>
                <span className="text-slate-200 text-sm truncate">{task.name}</span>
                {task.isLowFriction && (
                  <span className="text-sky-400 text-xs">⚡ Low friction</span>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                  className="text-slate-500 hover:text-slate-300 transition-colors"
                  aria-label="Toggle rationale"
                >
                  <ChevronRight
                    size={16}
                    className={`transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`}
                  />
                </button>
                <button
                  onClick={() => handleAccept(task, idx)}
                  disabled={loadingIdx === idx}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors disabled:opacity-50"
                >
                  Accept
                </button>
                <button
                  onClick={() => onDismiss(idx)}
                  className="bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-1.5 rounded-md transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
            {isExpanded && (
              <p className="text-slate-400 text-xs mt-2 pl-2 border-l-2 border-slate-700">
                {task.rationale}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
