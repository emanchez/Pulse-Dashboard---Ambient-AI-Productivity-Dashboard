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

  // Validate session on mount.
  //
  // Strategy (works for both dev and production):
  //   1. Read any stored JWT from localStorage (dev mode artifact).
  //   2. Call GET /me with credentials: "include" so the browser sends the
  //      httpOnly cookie automatically (production) AND the Authorization
  //      header (dev).
  //   3. 200 → authenticated. Token state is set to the stored JWT (dev) or
  //      "cookie" (production sentinel — indicates auth is handled by cookie).
  //   4. 401/403 → stale/invalid. Clear localStorage, set unauthenticated.
  //   5. Network error → keep stored token so the UI can show a meaningful
  //      error rather than bouncing the user to /login.
  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null

    const headers: Record<string, string> = {}
    if (stored) headers["Authorization"] = `Bearer ${stored}`

    fetch(`${BASE}/me`, {
      headers,
      credentials: "include",
    })
      .then((res) => {
        if (res.status === 401 || res.status === 403) {
          localStorage.removeItem(TOKEN_KEY)
          setTokenState(null)
        } else if (res.ok) {
          // In production, stored is null — use "cookie" sentinel.
          setTokenState(stored || "cookie")
        }
      })
      .catch(() => {
        // Network error (backend down) — keep any stored token so the UI can
        // show a meaningful error rather than silently redirecting to /login.
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
    // Only persist real JWTs to localStorage (not the "cookie" sentinel used in prod).
    if (t && t !== "cookie") {
      localStorage.setItem(TOKEN_KEY, t)
    }
    setTokenState(t)
  }, [])

  const logout = useCallback(async () => {
    localStorage.removeItem(TOKEN_KEY)
    // Call /logout so the backend clears the httpOnly pulse_token and csrf_token cookies.
    try {
      await fetch(`${BASE}/logout`, { method: "POST", credentials: "include" })
    } catch {
      // Ignore network errors on logout — clear local state regardless.
    }
    setTokenState(null)
    router.replace("/login")
  }, [router])

  return { token, ready, setToken, logout }
}
