"use client"

import React, { useEffect, useRef, useState } from "react"
import { Calendar } from "lucide-react"
import { useAuth } from "../../lib/hooks/useAuth"
import LoadingSpinner from "../LoadingSpinner"
import AppNavBar from "../../components/nav/AppNavBar"
import ReportList from "../../components/reports/ReportList"
import ReportForm from "../../components/reports/ReportForm"
import SystemStateManager from "../../components/system-state/SystemStateManager"
import { getPulse, listReports, listTasks } from "../../lib/api"
import type {
  PulseStats,
  ManualReportSchema,
  Task,
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
  const [pulseStats, setPulseStats] = useState<PulseStats | null>(null)
  const [reports, setReports] = useState<ManualReportSchema[]>([])
  const [totalReports, setTotalReports] = useState(0)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingReport, setEditingReport] = useState<ManualReportSchema | null>(null)

  const tokenRef = useRef(token)
  useEffect(() => {
    tokenRef.current = token
  }, [token])

  const handleAuthError = (err: any) => {
    if (err?.message?.includes("401")) logout()
  }

  const refreshPulse = async () => {
    if (!tokenRef.current) return
    try {
      setPulseStats(await getPulse(tokenRef.current))
    } catch {
      /* ignore */
    }
  }

  const refreshReports = async () => {
    if (!token) return
    try {
      const res = await listReports(token, 0, Math.max(reports.length, 20))
      setReports(res.items)
      setTotalReports(res.total)
    } catch (err: any) {
      handleAuthError(err)
    }
  }

  const handleLoadMore = async () => {
    if (!token) return
    try {
      const next = await listReports(token, reports.length, 20)
      setReports((prev) => [...prev, ...next.items])
      setTotalReports(next.total)
    } catch (err: any) {
      handleAuthError(err)
    }
  }

  useEffect(() => {
    if (!token) return

    const fetchAll = async () => {
      try {
        const [pulse, reportsRes, taskList] = await Promise.all([
          getPulse(token),
          listReports(token, 0, 20),
          listTasks(token),
        ])
        setPulseStats(pulse)
        setReports(reportsRes.items)
        setTotalReports(reportsRes.total)
        setTasks(taskList)
      } catch (err: any) {
        handleAuthError(err)
      } finally {
        setLoading(false)
      }
    }

    fetchAll()

    const pulseTimer = setInterval(async () => {
      try {
        setPulseStats(await getPulse(tokenRef.current!))
      } catch (err: any) {
        handleAuthError(err)
      }
    }, 30_000)

    return () => {
      clearInterval(pulseTimer)
    }
  }, [token, logout])

  if (!ready || !token || loading) return <LoadingSpinner />

  return (
    <>
      <AppNavBar
        silenceState={pulseStats?.silenceState}
        gapMinutes={pulseStats?.gapMinutes}
        onCreateReport={() => {
          setEditingReport(null)
          setShowForm(true)
        }}
      />
      <main className="max-w-5xl mx-auto px-6 py-8">
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
              <span>Last updated {relativeTime(reports[0].createdAt)}</span>
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
            setShowForm(false)
            setEditingReport(null)
          }}
        />
      )}
    </>
  )
}
