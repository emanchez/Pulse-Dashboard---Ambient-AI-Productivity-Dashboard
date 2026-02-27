import React from "react"
import AppNavBar from "../../components/nav/AppNavBar"

export default function ReportsPage() {
  return (
    <>
      <AppNavBar silenceState="engaged" />
      <main className="px-6 py-6">
        <div className="flex items-center justify-center h-64">
          <p className="text-slate-500 text-sm">Reports — coming soon.</p>
        </div>
      </main>
    </>
  )
}
