"use client"

import React, { useState, useEffect, useCallback } from "react"
import { Activity, Pause, Clock } from "lucide-react"
import type { PulseStats } from "../lib/generated/pulseClient"
import { getPulse } from "../lib/generated/pulseClient"

const POLL_INTERVAL_MS = 30_000

interface PulseCardProps {
  token: string
  onAuthError?: () => void
}

function formatGap(minutes: number): string {
  if (minutes < 1) return "< 1m"
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m}m`
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

const BADGE_STYLES: Record<PulseStats["silenceState"], { bg: string; text: string; label: string }> = {
  engaged: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Engaged" },
  stagnant: { bg: "bg-amber-50", text: "text-amber-700", label: "Stagnant" },
  paused: { bg: "bg-sky-50", text: "text-sky-700", label: "Paused" },
}

const BADGE_ICONS: Record<PulseStats["silenceState"], React.ReactNode> = {
  engaged: <Activity className="h-4 w-4" />,
  stagnant: <Clock className="h-4 w-4" />,
  paused: <Pause className="h-4 w-4" />,
}

export default function PulseCard({ token, onAuthError }: PulseCardProps) {
  const [pulse, setPulse] = useState<PulseStats | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchPulse = useCallback(async () => {
    try {
      const data = await getPulse(token)
      setPulse(data)
      setError(null)
    } catch (err: any) {
      if (err?.message?.includes("401")) {
        onAuthError?.()
        return
      }
      setError(err?.message ?? "Failed to fetch pulse")
    }
  }, [token, onAuthError])

  useEffect(() => {
    fetchPulse()
    const id = setInterval(fetchPulse, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [fetchPulse])

  if (error) {
    return (
      <div className="space-y-2">
        <h2 className="text-lg font-semibold">Silence Indicator</h2>
        <p className="text-sm text-red-600">{error}</p>
      </div>
    )
  }

  if (!pulse) {
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Silence Indicator</h2>
        <div className="h-6 w-24 animate-pulse bg-gray-100 rounded" />
        <div className="h-4 w-32 animate-pulse bg-gray-100 rounded" />
      </div>
    )
  }

  const badge = BADGE_STYLES[pulse.silenceState]

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Silence Indicator</h2>

      {/* State badge */}
      <span
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${badge.bg} ${badge.text}`}
      >
        {BADGE_ICONS[pulse.silenceState]}
        {badge.label}
      </span>

      {/* Gap display */}
      <p className="text-sm text-gray-600">
        Gap: <span className="font-medium">{formatGap(pulse.gapMinutes)}</span>
      </p>

      {/* Last action */}
      {pulse.lastActionAt && (
        <p className="text-xs text-gray-500">
          Last action: {new Date(pulse.lastActionAt).toLocaleString()}
        </p>
      )}

      {/* Paused until */}
      {pulse.silenceState === "paused" && pulse.pausedUntil && (
        <p className="text-xs text-sky-600">
          Paused until: {new Date(pulse.pausedUntil).toLocaleString()}
        </p>
      )}
    </div>
  )
}
