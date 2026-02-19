"use client"

import React from "react"
import { useAuth } from "../lib/hooks/useAuth"
import BentoGrid from "../components/BentoGrid"
import PulseCard from "../components/PulseCard"
import TaskBoard from "../components/TaskBoard"

export default function DashboardPage() {
  const { token, ready, logout } = useAuth()

  // useAuth redirects to /login when token is null
  if (!ready || !token) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-indigo-600" />
      </div>
    )
  }

  return (
    <>
      <h1 className="text-2xl font-semibold mb-4">Dashboard</h1>
      <BentoGrid
        zoneA={<PulseCard token={token} onAuthError={logout} />}
        zoneB={<TaskBoard token={token} onAuthError={logout} />}
      />
    </>
  )
}
