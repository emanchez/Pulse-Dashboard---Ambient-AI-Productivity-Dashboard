"use client"

import React, { useEffect, useRef, useState } from "react"
import { Calendar } from "lucide-react"
import { useAuth } from "../../lib/hooks/useAuth"
import LoadingSpinner from "../LoadingSpinner"
import AppNavBar from "../../components/nav/AppNavBar"
import ReportList from "../../components/reports/ReportList"
import ReportForm from "../../components/reports/ReportForm"
import SystemStateManager from "../../components/system-state/SystemStateManager"
import { useSilenceState } from "../../components/SilenceStateProvider"
import { listReports, listTasks, deleteReport, archiveReport, getAIUsage, ApiError } from "../../lib/api"
import type {
  ManualReportSchema,
  Task,
  AIUsageSummary,
} from "../../lib/api"

function relativeTime(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diffMs = now - then
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days === 1 ? "" : "s"} ago`
}

export default function ReportsPage() {
  const { token, ready, logout } = useAuth()
  const { silenceState, gapMinutes, refreshPulse } = useSilenceState()
  const [reports, setReports] = useState<ManualReportSchema[]>([])
  const [totalReports, setTotalReports] = useState(0)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingReport, setEditingReport] = useState<ManualReportSchema | null>(null)
  const [aiUsage, setAiUsage] = useState<AIUsageSummary | null>(null)

  const tokenRef = useRef(token)
  useEffect(() => {
    tokenRef.current = token
  }, [token])

  const handleAuthError = (err: unknown) => {
    if (err instanceof ApiError && err.isUnauthorized) { logout(); return true }
    return false
  }

  const refreshReports = async () => {
    if (!token) return
    try {
      const res = await listReports(token, 0, Math.max(reports.length, 20))
      setReports(res.items)
      setTotalReports(res.total)
    } catch (err: unknown) {
      if (!handleAuthError(err)) {
        const msg = err instanceof Error ? err.message : "Unknown error"
        setFetchError(`Could not refresh reports: ${msg}`)
      }
    }
  }

  const handleLoadMore = async () => {
    if (!token) return
    try {
      const next = await listReports(token, reports.length, 20)
      setReports((prev) => [...prev, ...next.items])
      setTotalReports(next.total)
    } catch (err: unknown) {
      handleAuthError(err)
    }
  }

  const handleDeleteReport = async (id: string) => {
    if (!token) return
    try {
      await deleteReport(token, id)
      await refreshReports()
      void refreshPulse()
    } catch (err: unknown) {
      handleAuthError(err)
    }
  }

  const handleArchiveReport = async (id: string) => {
    if (!token) return
    try {
      await archiveReport(token, id)
      await refreshReports()
      void refreshPulse()
    } catch (err: unknown) {
      handleAuthError(err)
    }
  }

  useEffect(() => {
    if (!token) return

    const fetchAll = async () => {
      setLoading(true)
      setFetchError(null)

      const [reportsResult, tasksResult] = await Promise.allSettled([
        listReports(token, 0, 20),
        listTasks(token),
      ])

      // Fetch AI usage in background (non-blocking)
      getAIUsage(token).then(setAiUsage).catch(() => {})

      const errors: string[] = []

      if (reportsResult.status === "fulfilled") {
        setReports(reportsResult.value.items)
        setTotalReports(reportsResult.value.total)
      } else {
        const err: unknown = reportsResult.reason
        if (err instanceof ApiError && err.isUnauthorized) { logout(); return }
        const msg = err instanceof Error ? err.message : "Unknown error"
        errors.push(`Could not load reports: ${msg}`)
      }

      if (tasksResult.status === "fulfilled") {
        setTasks(tasksResult.value)
      } else {
        const err: unknown = tasksResult.reason
        if (err instanceof ApiError && err.isUnauthorized) { logout(); return }
        errors.push("Could not load tasks — task linking unavailable")
      }

      if (errors.length > 0) {
        setFetchError(errors.join(" | "))
      }

      setLoading(false)
    }

    fetchAll()

    return () => {}
  }, [token, logout])

  if (!ready || !token || loading) return <LoadingSpinner />

  return (
    <>
      <AppNavBar
        silenceState={silenceState ?? undefined}
        gapMinutes={gapMinutes}
        onCreateReport={() => {
          setEditingReport(null)
          setShowForm(true)
        }}
        onLogout={logout}
      />
      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Fetch error banner */}
        {fetchError && (
          <div className="bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg px-4 py-3 text-sm mb-4">
            {fetchError}
          </div>
        )}

        {/* Page Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Strategic Reports</h1>
            <p className="text-slate-400 text-sm mt-1">
              Temporal history and narrative synthesis of your progress.
            </p>
          </div>
          {reports.length > 0 && (
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Calendar size={14} />
              <span>Last updated {relativeTime(reports[0].createdAt ?? "")}</span>
            </div>
          )}
        </div>

        {/* Report List */}
        <ReportList
          reports={reports}
          total={totalReports}
          loading={loading}
          onEdit={(report) => {
            setEditingReport(report)
            setShowForm(true)
          }}
          onLoadMore={handleLoadMore}
          onDelete={handleDeleteReport}
          onArchive={handleArchiveReport}
          token={token}
          coPlanUsage={aiUsage ? { used: aiUsage.coplan.used, limit: aiUsage.coplan.limit } : null}
        />

        {/* === SYSTEM PAUSES SECTION === */}
        <div className="border-t border-slate-700 my-8 pt-8">
          <SystemStateManager token={token} onStateChange={refreshPulse} />
        </div>

      </main>

      {/* Create/Edit Form Modal */}
      {showForm && (
        <ReportForm
          mode={editingReport ? "edit" : "create"}
          report={editingReport ?? undefined}
          token={token}
          tasks={tasks}
          onClose={() => {
            setShowForm(false)
            setEditingReport(null)
          }}
          onSave={() => {
            refreshReports()
            void refreshPulse()
            setShowForm(false)
            setEditingReport(null)
          }}
        />
      )}
    </>
  )
}
