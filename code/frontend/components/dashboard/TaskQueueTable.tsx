"use client"

import React, { useCallback, useEffect, useState } from "react"
import { listTasks } from "../../lib/api"
import { TaskSchema } from "../../lib/generated/types.gen"

interface TaskQueueTableProps {
  token: string
  activeSessionTaskId?: string | null
  onAuthError?: () => void
}

export default function TaskQueueTable({
  token,
  activeSessionTaskId,
  onAuthError,
}: TaskQueueTableProps) {
  const [tasks, setTasks] = useState<TaskSchema[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    try {
      const data = await listTasks(token)
      setTasks(data)
      setError(null)
    } catch (err: any) {
      if (err?.message?.includes("401")) {
        onAuthError?.()
        return
      }
      setError(err?.message ?? "Failed to fetch tasks")
    }
  }, [token, onAuthError])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  if (error) {
    return (
      <div className="bg-slate-800 rounded-xl p-5">
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    )
  }

  if (!tasks) {
    return (
      <div className="bg-slate-800 rounded-xl p-5">
        <div className="h-10 animate-pulse bg-slate-700 rounded mb-2" />
        <div className="h-10 animate-pulse bg-slate-700 rounded mb-2" />
        <div className="h-10 animate-pulse bg-slate-700 rounded" />
      </div>
    )
  }

  return (
    <div className="bg-slate-800 rounded-xl p-5">
      <div className="flex justify-between items-center">
        <h3 className="text-base font-semibold text-white">Task Queue</h3>
        <span className="text-slate-400 text-xs">
          <span className="text-emerald-400">● Done</span>{" "}
          <span className="text-blue-400">● Working</span>
        </span>
      </div>
      <table className="w-full mt-4 text-sm">
        <thead>
          <tr>
            <th className="text-slate-500 text-xs uppercase tracking-wider text-left">
              Task
            </th>
            <th className="text-slate-500 text-xs uppercase tracking-wider text-center">
              Deadline
            </th>
            <th className="text-slate-500 text-xs uppercase tracking-wider text-right">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => {
            let statusLabel = "Pending"
            let statusColor = "text-slate-400"
            if (task.isCompleted) {
              statusLabel = "Completed"
              statusColor = "text-emerald-400"
            } else if (activeSessionTaskId && task.id === activeSessionTaskId) {
              statusLabel = "In Progress"
              statusColor = "text-blue-400"
            }

            return (
              <tr
                key={task.id ?? task.name}
                className="border-t border-slate-700/50"
              >
                <td className="py-3 text-white">{task.name}</td>
                <td className="py-3 text-center text-slate-300">
                  {task.deadline
                    ? new Date(task.deadline).toLocaleDateString()
                    : "—"}
                </td>
                <td className="py-3 text-right">
                  <span className={statusColor}>{statusLabel}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
