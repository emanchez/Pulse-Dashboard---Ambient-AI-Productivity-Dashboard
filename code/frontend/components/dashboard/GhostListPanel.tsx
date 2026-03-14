"use client"

import React, { useState } from "react"
import { Ghost, ChevronRight, AlertCircle } from "lucide-react"
import type { GhostTask } from "../../lib/api"

interface GhostListPanelProps {
  ghosts: GhostTask[]
  loading?: boolean
  error?: string | null
}

const INITIAL_DISPLAY = 3

export default function GhostListPanel({ ghosts, loading, error }: GhostListPanelProps) {
  const [showAll, setShowAll] = useState(false)

  if (loading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 mb-3">
          <Ghost size={14} className="text-slate-400" />
          <span className="text-slate-400 text-xs font-bold tracking-widest uppercase">
            GHOST LIST
          </span>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse bg-slate-700 rounded h-10" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 mb-3">
          <Ghost size={14} className="text-slate-400" />
          <span className="text-slate-400 text-xs font-bold tracking-widest uppercase">
            GHOST LIST
          </span>
        </div>
        <div className="flex items-center gap-2 text-rose-400 text-xs">
          <AlertCircle size={14} />
          <span>Failed to load ghost list</span>
        </div>
      </div>
    )
  }

  const displayedGhosts = showAll ? ghosts : ghosts.slice(0, INITIAL_DISPLAY)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Ghost size={14} className="text-slate-400" />
          <span className="text-slate-400 text-xs font-bold tracking-widest uppercase">
            GHOST LIST
          </span>
          {ghosts.length > 0 && (
            <span className="bg-rose-500/20 text-rose-400 text-xs font-medium px-1.5 py-0.5 rounded border border-rose-500/30">
              {ghosts.length}
            </span>
          )}
        </div>
      </div>

      {ghosts.length === 0 ? (
        <p className="text-slate-500 text-xs">No wheel-spinning tasks detected.</p>
      ) : (
        <div className="space-y-1.5">
          {displayedGhosts.map((ghost) => (
            <div
              key={ghost.id}
              className="bg-slate-800 rounded-lg px-3 py-2 flex items-center justify-between gap-2"
            >
              <div className="min-w-0 flex-1">
                <p className="text-slate-200 text-xs font-medium truncate">
                  {ghost.name}
                </p>
                <p className="text-slate-500 text-xs mt-0.5">
                  {ghost.daysOpen}d open · {ghost.ghostReason}
                </p>
              </div>
              <ChevronRight size={12} className="text-slate-600 shrink-0" />
            </div>
          ))}

          {!showAll && ghosts.length > INITIAL_DISPLAY && (
            <button
              onClick={() => setShowAll(true)}
              className="text-slate-500 hover:text-slate-300 text-xs transition-colors w-full text-center py-1"
            >
              Show all ({ghosts.length - INITIAL_DISPLAY} more)
            </button>
          )}
          {showAll && ghosts.length > INITIAL_DISPLAY && (
            <button
              onClick={() => setShowAll(false)}
              className="text-slate-500 hover:text-slate-300 text-xs transition-colors w-full text-center py-1"
            >
              Show less
            </button>
          )}
        </div>
      )}
    </div>
  )
}
