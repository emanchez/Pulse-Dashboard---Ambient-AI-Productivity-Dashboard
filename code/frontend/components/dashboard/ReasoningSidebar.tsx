"use client"

import React, { useEffect, useState } from "react"
import { Brain, AlertCircle } from "lucide-react"
import GhostListPanel from "./GhostListPanel"
import ReEntryBanner from "./ReEntryBanner"
import InferenceCard from "./InferenceCard"
import {
  getGhostList,
  getAIUsage,
  getLatestSynthesis,
  listSystemStates,
} from "../../lib/api"
import type {
  GhostTask,
  AIUsageSummary,
  SynthesisResponse,
  SystemStateSchema,
} from "../../lib/api"

interface ReasoningSidebarProps {
  token: string
}

function isReturningFromLeave(states: SystemStateSchema[]): boolean {
  const now = Date.now()
  const cutoff = 48 * 60 * 60 * 1000 // 48 hours
  return states.some((s) => {
    if (!s.requiresRecovery) return false
    if (!s.endDate) return false
    const end = new Date(s.endDate).getTime()
    return end <= now && now - end < cutoff
  })
}

function formatResetTime(resetsIn: string): string {
  // resetsIn is an ISO date string or a human-readable string
  try {
    const resetDate = new Date(resetsIn)
    if (isNaN(resetDate.getTime())) return resetsIn
    const now = Date.now()
    const diff = resetDate.getTime() - now
    if (diff <= 0) return "now"
    const hours = Math.floor(diff / 3_600_000)
    const days = Math.floor(hours / 24)
    if (days > 0) return `${days}d`
    if (hours > 0) return `${hours}h`
    const minutes = Math.floor(diff / 60_000)
    return `${minutes}m`
  } catch {
    return resetsIn
  }
}

export default function ReasoningSidebar({ token }: ReasoningSidebarProps) {
  // Ghost list state
  const [ghosts, setGhosts] = useState<GhostTask[]>([])
  const [ghostsLoading, setGhostsLoading] = useState(true)
  const [ghostsError, setGhostsError] = useState<string | null>(null)

  // AI usage state
  const [usage, setUsage] = useState<AIUsageSummary | null>(null)
  const [usageError, setUsageError] = useState(false)

  // Latest synthesis for inline insight
  const [latestSynthesis, setLatestSynthesis] = useState<SynthesisResponse | null>(null)

  // Re-entry mode
  const [isReEntry, setIsReEntry] = useState(false)

  useEffect(() => {
    if (!token) return

    // Fetch all sidebar data independently
    const fetchGhosts = async () => {
      try {
        const res = await getGhostList(token)
        setGhosts(res.ghosts)
      } catch (err: unknown) {
        setGhostsError(err instanceof Error ? err.message : "Failed to load")
      } finally {
        setGhostsLoading(false)
      }
    }

    const fetchUsage = async () => {
      try {
        const res = await getAIUsage(token)
        setUsage(res)
      } catch {
        setUsageError(true)
      }
    }

    const fetchSynthesis = async () => {
      try {
        const res = await getLatestSynthesis(token)
        setLatestSynthesis(res)
      } catch {
        // No synthesis yet — that's fine
      }
    }

    const fetchReEntry = async () => {
      try {
        const states = await listSystemStates(token)
        setIsReEntry(isReturningFromLeave(states))
      } catch {
        // Silent fail
      }
    }

    fetchGhosts()
    fetchUsage()
    fetchSynthesis()
    fetchReEntry()
  }, [token])

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Brain size={16} className="text-slate-400" />
        <span className="text-slate-300 text-sm font-semibold">Reasoning</span>
      </div>

      {/* Re-entry banner */}
      <ReEntryBanner visible={isReEntry} />

      {/* Latest synthesis insight */}
      {latestSynthesis && (
        <InferenceCard
          type="insight"
          title={latestSynthesis.theme}
          body={
            latestSynthesis.summary.length > 120
              ? latestSynthesis.summary.slice(0, 120) + "…"
              : latestSynthesis.summary
          }
          detail={`Score: ${latestSynthesis.commitmentScore}/10 · ${new Date(latestSynthesis.createdAt).toLocaleDateString()}`}
        />
      )}

      {/* Ghost list */}
      <GhostListPanel
        ghosts={ghosts}
        loading={ghostsLoading}
        error={ghostsError}
      />

      {/* AI Usage summary */}
      <div className="mt-auto pt-3 border-t border-slate-700">
        {usageError ? (
          <div className="flex items-center gap-1.5 text-rose-400 text-xs">
            <AlertCircle size={12} />
            <span>Usage data unavailable</span>
          </div>
        ) : usage ? (
          <p className="text-slate-500 text-xs">
            Synthesis: {usage.synthesis.used}/{usage.synthesis.limit} this week
            {" · "}
            Tasks: {usage.suggest.used}/{usage.suggest.limit} today
            {" · "}
            Co-plan: {usage.coplan.used}/{usage.coplan.limit} today
          </p>
        ) : (
          <div className="animate-pulse bg-slate-700 rounded h-3 w-3/4" />
        )}
      </div>
    </div>
  )
}
