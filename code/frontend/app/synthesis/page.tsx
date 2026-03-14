"use client"

import React, { useEffect, useRef, useState, useCallback } from "react"
import { Brain } from "lucide-react"
import { useAuth } from "../../lib/hooks/useAuth"
import LoadingSpinner from "../LoadingSpinner"
import AppNavBar from "../../components/nav/AppNavBar"
import SynthesisCard from "../../components/synthesis/SynthesisCard"
import SynthesisTrigger from "../../components/synthesis/SynthesisTrigger"
import TaskSuggestionList from "../../components/synthesis/TaskSuggestionList"
import { useSilenceState } from "../../components/SilenceStateProvider"
import {
  triggerSynthesis,
  getLatestSynthesis,
  getSynthesis,
  acceptTasks,
  getAIUsage,
} from "../../lib/api"
import type {
  SynthesisResponse,
  SuggestedTask,
  AIUsageSummary,
} from "../../lib/api"

export default function SynthesisPage() {
  const { token, ready, logout } = useAuth()
  const { silenceState, gapMinutes } = useSilenceState()

  const [synthesis, setSynthesis] = useState<SynthesisResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [pollingId, setPollingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [rateLimitMsg, setRateLimitMsg] = useState<string | null>(null)
  const [aiDisabled, setAiDisabled] = useState(false)
  const [usage, setUsage] = useState<AIUsageSummary | null>(null)
  const [suggestions, setSuggestions] = useState<SuggestedTask[]>([])
  const [isReEntryMode, setIsReEntryMode] = useState(false)

  const tokenRef = useRef(token)
  useEffect(() => { tokenRef.current = token }, [token])

  const handleAuthError = useCallback((err: any) => {
    if (err?.message?.includes("401")) { logout(); return true }
    return false
  }, [logout])

  // Fetch latest synthesis + usage on mount
  useEffect(() => {
    if (!token) return

    const fetchInitial = async () => {
      try {
        const [latestSynthesis, usageData] = await Promise.allSettled([
          getLatestSynthesis(token),
          getAIUsage(token),
        ])

        if (latestSynthesis.status === "fulfilled") {
          setSynthesis(latestSynthesis.value)
          setSuggestions(latestSynthesis.value.suggestedTasks || [])
        }
        if (usageData.status === "fulfilled") {
          setUsage(usageData.value)
        }
      } catch (err: any) {
        if (err?.message?.includes("503")) {
          setAiDisabled(true)
        } else if (!handleAuthError(err)) {
          // 404 is fine — no synthesis yet
        }
      } finally {
        setLoading(false)
      }
    }

    fetchInitial()
  }, [token, handleAuthError])

  // Polling for synthesis completion
  useEffect(() => {
    if (!pollingId || !tokenRef.current) return

    let cancelled = false
    const poll = async () => {
      try {
        const result = await getSynthesis(tokenRef.current!, pollingId)
        if (cancelled) return

        if (result.status === "completed") {
          setSynthesis(result)
          setSuggestions(result.suggestedTasks || [])
          setTriggering(false)
          setPollingId(null)
          // Refresh usage
          try {
            const u = await getAIUsage(tokenRef.current!)
            setUsage(u)
          } catch { /* best effort */ }
        } else if (result.status === "failed") {
          setError("Synthesis failed. Please try again.")
          setTriggering(false)
          setPollingId(null)
        } else {
          // still pending — poll again
          setTimeout(poll, 5000)
        }
      } catch (err: any) {
        if (cancelled) return
        if (!handleAuthError(err)) {
          setError("Failed to check synthesis status.")
          setTriggering(false)
          setPollingId(null)
        }
      }
    }

    // Start polling after a brief delay
    const timeout = setTimeout(poll, 3000)
    return () => { cancelled = true; clearTimeout(timeout) }
  }, [pollingId, handleAuthError])

  const handleTrigger = async () => {
    if (!token) return
    setError(null)
    setRateLimitMsg(null)
    setTriggering(true)

    try {
      const result = await triggerSynthesis(token)
      setPollingId(result.id)
    } catch (err: any) {
      setTriggering(false)
      if (err?.message?.includes("429")) {
        // Extract the message from the error
        const match = err.message.match(/:\s*(.+)/)
        setRateLimitMsg(match ? match[1] : "Synthesis limit reached. Please try again later.")
      } else if (err?.message?.includes("503")) {
        setAiDisabled(true)
      } else if (!handleAuthError(err)) {
        setError(err?.message || "Failed to trigger synthesis.")
      }
    }
  }

  const handleAcceptTask = async (task: SuggestedTask) => {
    if (!token) return
    await acceptTasks(token, [{ name: task.name, priority: task.priority, notes: task.rationale }])
  }

  const handleDismissTask = (idx: number) => {
    setSuggestions((prev) => prev.filter((_, i) => i !== idx))
  }

  if (!ready || !token) return <LoadingSpinner />

  const usageText = usage
    ? `${usage.synthesis.used}/${usage.synthesis.limit} synthesis runs used this week`
    : undefined

  return (
    <div className="bg-slate-900 min-h-screen">
      <AppNavBar
        silenceState={silenceState}
        gapMinutes={gapMinutes}
        onLogout={logout}
      />

      <main className="max-w-3xl mx-auto px-4 py-8 md:px-6">
        {/* Page header */}
        <div className="flex items-center gap-3 mb-6">
          <Brain className="text-blue-400" size={24} />
          <h1 className="text-white text-xl font-semibold">Sunday Synthesis</h1>
        </div>

        {/* AI disabled state */}
        {aiDisabled ? (
          <div className="bg-slate-800 rounded-xl p-6 text-center">
            <p className="text-slate-400">AI features are currently disabled.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Trigger */}
            <SynthesisTrigger
              onTrigger={handleTrigger}
              loading={triggering}
              error={error}
              rateLimitMessage={rateLimitMsg}
              usageText={usageText}
            />

            {/* Loading skeleton */}
            {loading && (
              <div className="bg-slate-800 rounded-xl p-6 space-y-3">
                <div className="h-4 w-1/4 animate-pulse bg-slate-700 rounded" />
                <div className="h-4 w-3/4 animate-pulse bg-slate-700 rounded" />
                <div className="h-4 w-1/2 animate-pulse bg-slate-700 rounded" />
                <div className="h-20 w-full animate-pulse bg-slate-700 rounded mt-4" />
              </div>
            )}

            {/* Synthesis result */}
            {!loading && synthesis && (
              <SynthesisCard
                summary={synthesis.summary}
                theme={synthesis.theme}
                commitmentScore={synthesis.commitmentScore}
                periodStart={synthesis.periodStart}
                periodEnd={synthesis.periodEnd}
                createdAt={synthesis.createdAt}
              />
            )}

            {/* Empty state */}
            {!loading && !synthesis && !triggering && (
              <div className="bg-slate-800 rounded-xl p-8 text-center">
                <p className="text-slate-400 text-sm">
                  No synthesis reports yet. Click &ldquo;Generate Weekly Synthesis&rdquo; to get started.
                </p>
              </div>
            )}

            {/* Task suggestions */}
            {!loading && suggestions.length > 0 && (
              <TaskSuggestionList
                suggestions={suggestions}
                onAccept={handleAcceptTask}
                onDismiss={handleDismissTask}
                isReEntryMode={isReEntryMode}
              />
            )}
          </div>
        )}
      </main>
    </div>
  )
}
