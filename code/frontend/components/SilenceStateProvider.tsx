"use client"

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from "react"
import { useAuth } from "../lib/hooks/useAuth"
import { getPulse } from "../lib/api"
import type { PulseStats } from "../lib/api"

interface SilenceStateContextValue {
  silenceState: PulseStats["silenceState"] | null
  gapMinutes: number
  pausedUntil: string | null
  refreshPulse: () => Promise<void>
}

const SilenceStateContext = createContext<SilenceStateContextValue>({
  silenceState: null,
  gapMinutes: 0,
  pausedUntil: null,
  refreshPulse: async () => {},
})

export function useSilenceState() {
  return useContext(SilenceStateContext)
}

export default function SilenceStateProvider({ children }: { children: React.ReactNode }) {
  const { token, ready, logout } = useAuth()
  const [pulse, setPulse] = useState<PulseStats | null>(null)

  const tokenRef = useRef(token)
  useEffect(() => {
    tokenRef.current = token
  }, [token])

  const fetchPulse = useCallback(async () => {
    const t = tokenRef.current
    if (!t) return
    try {
      setPulse(await getPulse(t))
    } catch (e) {
      // If the token was rejected by the server, log the user out so they
      // are redirected to /login rather than stuck in a silent 401 loop.
      if (e instanceof Error && e.message.includes("401")) {
        logout()
      }
      // Other errors (network down, 5xx) are ignored — page-level guards handle them.
    }
  }, [logout])

  // Initial fetch + 30s polling
  useEffect(() => {
    if (!ready || !token) return

    fetchPulse()

    const timer = setInterval(fetchPulse, 30_000)
    return () => clearInterval(timer)
  }, [ready, token, fetchPulse])

  // Propagate data-state to <html> for CSS custom property switching
  useEffect(() => {
    const state = pulse?.silenceState ?? "engaged"
    document.documentElement.dataset.state = state
  }, [pulse?.silenceState])

  const value: SilenceStateContextValue = {
    silenceState: pulse?.silenceState ?? null,
    gapMinutes: pulse?.gapMinutes ?? 0,
    pausedUntil: pulse?.pausedUntil ?? null,
    refreshPulse: fetchPulse,
  }

  return (
    <SilenceStateContext.Provider value={value}>
      {children}
    </SilenceStateContext.Provider>
  )
}
