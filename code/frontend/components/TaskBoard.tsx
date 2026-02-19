"use client"

import React, { useState, useEffect, useCallback } from "react"
import { Save, Loader2 } from "lucide-react"
import type { Task } from "../lib/api"
import { listTasks, updateTask } from "../lib/api"

// ── Priority colors (PDD palette) ──────────────────────────────────
const PRIORITY_STYLES: Record<string, { border: string; bg: string; text: string }> = {
  High:   { border: "border-l-rose-500",  bg: "bg-rose-50",  text: "text-rose-600" },
  Medium: { border: "border-l-amber-500", bg: "bg-amber-50", text: "text-amber-700" },
  Low:    { border: "border-l-sky-500",   bg: "bg-sky-50",   text: "text-sky-700" },
}

function priorityStyle(p?: string | null) {
  return PRIORITY_STYLES[p ?? ""] ?? { border: "border-l-gray-300", bg: "bg-white", text: "text-gray-600" }
}

// ── Props ───────────────────────────────────────────────────────────
interface TaskBoardProps {
  token: string
  onAuthError?: () => void
}

export default function TaskBoard({ token, onAuthError }: TaskBoardProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [unsaved, setUnsaved] = useState<Map<string, Partial<Task>>>(new Map())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // ── Fetch tasks ─────────────────────────────────────────────────
  const fetchTasks = useCallback(async () => {
    try {
      const data = await listTasks(token)
      setTasks(data ?? [])
      setError(null)
    } catch (err: any) {
      if (err?.message?.includes("401")) {
        onAuthError?.()
        return
      }
      setError(err?.message ?? "Failed to load tasks")
    } finally {
      setLoading(false)
    }
  }, [token, onAuthError])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // ── Track field changes ────────────────────────────────────────
  function handleFieldChange(taskId: string, field: keyof Task, value: string | boolean) {
    setUnsaved((prev) => {
      const next = new Map(prev)
      const existing: Record<string, unknown> = { ...(next.get(taskId) ?? {}) }
      existing[field] = value
      next.set(taskId, existing as Partial<Task>)
      return next
    })
  }

  // ── Display value: unsaved override → original ────────────────
  function displayValue(task: Task, field: keyof Task) {
    const id = task.id ?? ""
    const override = unsaved.get(id)
    if (override && field in override) return override[field]
    return task[field]
  }

  // ── Save all pending changes ──────────────────────────────────
  async function handleSave() {
    setSaving(true)
    setError(null)
    const failed = new Map<string, Partial<Task>>()

    for (const [id, diff] of Array.from(unsaved.entries())) {
      try {
        await updateTask(token, id, diff as Task)
      } catch (err: any) {
        if (err?.message?.includes("401")) {
          onAuthError?.()
          return
        }
        failed.set(id, diff)
        setError(`Failed to save task ${id}`)
      }
    }

    setUnsaved(failed)
    setSaving(false)

    // Re-fetch to sync with server state
    if (failed.size === 0) {
      await fetchTasks()
    }
  }

  // ── Render ────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Tasks</h2>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 animate-pulse bg-gray-100 rounded" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Tasks</h2>

        <button
          onClick={handleSave}
          disabled={unsaved.size === 0 || saving}
          className="inline-flex items-center gap-1.5 rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white
                     hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Saving…
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save changes
            </>
          )}
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 rounded p-2">{error}</p>
      )}

      {/* Empty state */}
      {tasks.length === 0 && (
        <p className="text-sm text-gray-500 py-6 text-center">
          No tasks yet. Tasks created via the API will appear here.
        </p>
      )}

      {/* Task rows */}
      <div className="space-y-2">
        {tasks.map((task) => {
          const id = task.id ?? ""
          const isDirty = unsaved.has(id)
          const pStyle = priorityStyle(displayValue(task, "priority") as string)

          return (
            <div
              key={id}
              className={`border-l-4 ${pStyle.border} ${pStyle.bg} rounded-md p-3 space-y-2 transition-colors`}
            >
              {/* Row 1: Name + priority + dirty badge */}
              <div className="flex items-center gap-2 flex-wrap">
                <input
                  type="text"
                  value={(displayValue(task, "name") as string) ?? ""}
                  onChange={(e) => handleFieldChange(id, "name", e.target.value)}
                  className="flex-1 min-w-0 rounded border-gray-300 text-sm shadow-sm
                             focus:border-indigo-500 focus:ring-indigo-500"
                  placeholder="Task name"
                />

                <select
                  value={(displayValue(task, "priority") as string) ?? ""}
                  onChange={(e) => handleFieldChange(id, "priority", e.target.value)}
                  className={`rounded border-gray-300 text-sm shadow-sm ${pStyle.text}
                              focus:border-indigo-500 focus:ring-indigo-500`}
                >
                  <option value="">None</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>

                <label className="flex items-center gap-1 text-xs text-gray-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!displayValue(task, "isCompleted")}
                    onChange={(e) => handleFieldChange(id, "isCompleted", e.target.checked)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Done
                </label>

                {isDirty && (
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                    Unsaved
                  </span>
                )}
              </div>

              {/* Row 2: Deadline */}
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500 w-16">Deadline</label>
                <input
                  type="date"
                  value={
                    (displayValue(task, "deadline") as string)
                      ? new Date(displayValue(task, "deadline") as string).toISOString().split("T")[0]
                      : ""
                  }
                  onChange={(e) => handleFieldChange(id, "deadline", e.target.value || "")}
                  className="rounded border-gray-300 text-sm shadow-sm
                             focus:border-indigo-500 focus:ring-indigo-500"
                />
              </div>

              {/* Row 3: Notes */}
              <textarea
                value={(displayValue(task, "notes") as string) ?? ""}
                onChange={(e) => handleFieldChange(id, "notes", e.target.value)}
                rows={2}
                className="w-full rounded border-gray-300 text-sm shadow-sm
                           focus:border-indigo-500 focus:ring-indigo-500"
                placeholder="Notes…"
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
