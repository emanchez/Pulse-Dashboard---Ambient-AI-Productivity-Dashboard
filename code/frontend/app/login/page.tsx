"use client"

import React, { useState, FormEvent } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "../../lib/hooks/useAuth"
import { login } from "../../lib/api"

export default function LoginPage() {
  const { token, ready, setToken } = useAuth()
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // If already authenticated, redirect to dashboard
  React.useEffect(() => {
    if (ready && token) {
      router.replace("/")
    }
  }, [ready, token, router])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const data = await login(username, password)
      // In production, /login sets an httpOnly cookie and returns {"message": "ok"}.
      // In dev, it returns {"access_token": "...", "token_type": "bearer"}.
      // setToken() handles both: stores the JWT in localStorage for dev, or uses
      // the "cookie" sentinel for production (real auth is handled by the cookie).
      setToken(data.access_token || "cookie")
      router.push("/")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed")
    } finally {
      setLoading(false)
    }
  }

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-600 border-t-blue-500" />
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-slate-800 border border-slate-700 rounded-xl shadow-xl p-6 space-y-4"
      >
        <h1 className="text-xl font-semibold text-center text-white">Sign In</h1>

        {error && (
          <div className="bg-red-500/20 text-red-400 border border-red-500/30 text-sm rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="username" className="block text-sm font-medium text-slate-300 mb-1">
            Username
          </label>
          <input
            id="username"
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-lg bg-slate-900 border border-slate-600 text-white px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors sm:text-sm"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg bg-slate-900 border border-slate-600 text-white px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors sm:text-sm"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 px-4 py-2 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {loading ? "Signing in…" : "Sign In"}
        </button>
      </form>
    </div>
  )
}
