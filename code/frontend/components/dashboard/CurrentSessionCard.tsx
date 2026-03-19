"use client"

import React, { useState } from "react"
import { FileText, Play, Square } from "lucide-react"
import { SessionLogSchema } from "../../lib/generated/types.gen"
import { startSession, stopSession } from "../../lib/api"
import type { Task } from "../../lib/api"

interface CurrentSessionCardProps {
  session: SessionLogSchema | null
  token?: string
  tasks?: Task[]
  onStartSession?: (session: SessionLogSchema) => void
  onStopSession?: () => void
}

export default function CurrentSessionCard({
  session,
  token,
  tasks = [],
  onStartSession,
  onStopSession,
}: CurrentSessionCardProps) {
  const [showForm, setShowForm] = useState(false)
  const [selectedTaskId, setSelectedTaskId] = useState("")
  const [goalMinutes, setGoalMinutes] = useState("")
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const elapsed = session?.elapsedMinutes ?? 0
  const goal = session?.goalMinutes ?? 0
  const percent = goal > 0 ? Math.min((elapsed / goal) * 100, 100) : 0

  const handleStart = async () => {
    if (!token || !selectedTaskId) return
    const selectedTask = tasks.find((t) => t.id === selectedTaskId)
    if (!selectedTask) return
    setStarting(true)
    setError(null)
    try {
      const result = await startSession(token, {
        taskName: selectedTask.name,
        taskId: selectedTaskId,
        goalMinutes: goalMinutes ? parseInt(goalMinutes, 10) : undefined,
      })
      setShowForm(false)
      setSelectedTaskId("")
      setGoalMinutes("")
      onStartSession?.(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start session.")
    } finally {
      setStarting(false)
    }
  }

  const handleStop = async () => {
    if (!token) return
    setStopping(true)
    setError(null)
    try {
      await stopSession(token)
      onStopSession?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop session.")
    } finally {
      setStopping(false)
    }
  }

  return (
    <div className="bg-slate-800 rounded-xl p-5 relative overflow-hidden">
      <FileText className="absolute right-4 bottom-4 text-slate-700/40" size={64} />
      <span className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
        Current Session
      </span>

      {error && (
        <div className="mt-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg px-3 py-2 text-xs">
          {error}
        </div>
      )}

      {session ? (
        <>
          <h3 className="text-lg font-semibold text-white mt-1">
            {session.taskName}
          </h3>
          <p className="text-blue-400 text-sm">{elapsed}m elapsed</p>
          <div className="w-full bg-slate-700 rounded-full h-1.5 mt-3">
            <div
              className="bg-blue-500 h-1.5 rounded-full transition-all"
              style={{ width: `${percent}%` }}
            />
          </div>
          <span className="text-slate-500 text-xs">
            Goal: {session.goalMinutes ?? 0} mins
          </span>
          <div className="mt-4">
            <button
              onClick={handleStop}
              disabled={stopping}
              className="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Square size={14} />
              {stopping ? "Stopping…" : "Stop Session"}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-slate-500 text-sm mt-2">No active session</p>
          {!showForm ? (
            <button
              onClick={() => setShowForm(true)}
              className="mt-3 flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors"
            >
              <Play size={14} />
              Start Focus Session
            </button>
          ) : (
            <div className="mt-3 space-y-2">
              <select
                value={selectedTaskId}
                onChange={(e) => setSelectedTaskId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
              >
                <option value="">Select a task…</option>
                {tasks.map((t) => (
                  <option key={t.id} value={t.id ?? ""}>
                    {t.name}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min="1"
                value={goalMinutes}
                onChange={(e) => setGoalMinutes(e.target.value)}
                placeholder="Goal (minutes, optional)"
                className="w-full bg-slate-900 border border-slate-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 transition-colors"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleStart}
                  disabled={starting || !selectedTaskId}
                  className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play size={14} />
                  {starting ? "Starting…" : "Start"}
                </button>
                <button
                  onClick={() => {
                    setShowForm(false)
                    setSelectedTaskId("")
                    setGoalMinutes("")
                    setError(null)
                  }}
                  className="bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

