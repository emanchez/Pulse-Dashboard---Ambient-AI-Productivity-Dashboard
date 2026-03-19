"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter, usePathname } from "next/navigation"

const TOKEN_KEY = "pulse_token"
const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

export function useAuth() {
  const [token, setTokenState] = useState<string | null>(null)
  const [ready, setReady] = useState(false)
  const router = useRouter()
  const pathname = usePathname()

  // Read token from localStorage on mount, then validate it against /me.
  // This clears stale tokens (expired, missing iss/aud claims, deleted user, etc.)
  // so the user is redirected to /login instead of silently receiving 401s everywhere.
  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null
    if (!stored) {
      setTokenState(null)
      setReady(true)
      return
    }
    // Validate against the server — if rejected, wipe the stale token.
    fetch(`${BASE}/me`, {
      headers: { Authorization: `Bearer ${stored}` },
      credentials: "omit",
    })
      .then((res) => {
        if (res.status === 401 || res.status === 403) {
          localStorage.removeItem(TOKEN_KEY)
          setTokenState(null)
        } else {
          setTokenState(stored)
        }
      })
      .catch(() => {
        // Network error (backend down) — keep the token so the UI can show a
        // meaningful error rather than bouncing the user to /login.
        setTokenState(stored)
      })
      .finally(() => setReady(true))
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
