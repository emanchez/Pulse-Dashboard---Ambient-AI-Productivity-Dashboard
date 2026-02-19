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
      setToken(data.access_token)
      router.push("/")
    } catch (err: any) {
      setError(err?.message ?? "Login failed")
    } finally {
      setLoading(false)
    }
  }

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-indigo-600" />
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-white rounded-lg shadow p-6 space-y-4"
      >
        <h1 className="text-xl font-semibold text-center">Sign In</h1>

        {error && (
          <div className="bg-red-50 text-red-700 text-sm rounded p-2">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
            Username
          </label>
          <input
            id="username"
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-indigo-600 px-4 py-2 text-white font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {loading ? "Signing in…" : "Sign In"}
        </button>
      </form>
    </div>
  )
}
