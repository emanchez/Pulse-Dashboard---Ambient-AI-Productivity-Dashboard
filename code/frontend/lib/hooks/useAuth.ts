"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter, usePathname } from "next/navigation"

const TOKEN_KEY = "pulse_token"

export function useAuth() {
  const [token, setTokenState] = useState<string | null>(null)
  const [ready, setReady] = useState(false)
  const router = useRouter()
  const pathname = usePathname()

  // Read token from localStorage on mount
  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null
    setTokenState(stored)
    setReady(true)
  }, [])

  // Redirect to /login when there is no token (skip if already on /login)
  useEffect(() => {
    if (ready && !token && pathname !== "/login") {
      router.replace("/login")
    }
  }, [ready, token, pathname, router])

  const setToken = useCallback((t: string) => {
    // TODO(deploy): S-2 — Migrate token storage from localStorage to httpOnly + Secure +
    //               SameSite=Strict cookies. Remove this localStorage write and the corresponding
    //               read below. Implement a /refresh endpoint for session renewal.
    localStorage.setItem(TOKEN_KEY, t)
    setTokenState(t)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setTokenState(null)
    router.replace("/login")
  }, [router])

  return { token, ready, setToken, logout }
}
