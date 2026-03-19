"use client"

import React from "react"
import { Pencil, Trash2, Plus } from "lucide-react"
import { TaskSchema } from "../../lib/generated/types.gen"

interface TaskQueueTableProps {
  tasks: TaskSchema[]
  activeSessionTaskId?: string | null
  onCreateTask?: () => void
  onEdit?: (task: TaskSchema) => void
  onDelete?: (task: TaskSchema) => void
  onToggleComplete?: (task: TaskSchema) => void
}

const PRIORITY_COLORS: Record<string, string> = {
  High: "text-red-400",
  Medium: "text-amber-400",
  Low: "text-emerald-400",
}

export default function TaskQueueTable({
  tasks,
  activeSessionTaskId,
  onCreateTask,
  onEdit,
  onDelete,
  onToggleComplete,
}: TaskQueueTableProps) {
  if (!tasks.length) {
    return (
      <div className="bg-slate-800 rounded-xl p-8 text-center">
        <p className="text-slate-400 mb-4">No tasks yet</p>
        {onCreateTask && (
          <button
            onClick={onCreateTask}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
          >
            Create Your First Task
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="bg-slate-800 rounded-xl p-5">
      <div className="flex justify-between items-center">
        <h3 className="text-base font-semibold text-white">Task Queue</h3>
        <div className="flex items-center gap-3">
          <span className="text-slate-400 text-xs">
            <span className="text-emerald-400">● Done</span>{" "}
            <span className="text-blue-400">● Working</span>
          </span>
          {onCreateTask && (
            <button
              onClick={onCreateTask}
              title="Create task"
              className="flex items-center gap-1 text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              <Plus size={13} />
              New Task
            </button>
          )}
        </div>
      </div>
      <div className="overflow-x-auto -mx-1">
        <table className="w-full mt-4 text-sm min-w-[560px]">
        <thead>
          <tr>
            <th className="text-slate-500 text-xs uppercase tracking-wider text-left w-6" />
            <th className="text-slate-500 text-xs uppercase tracking-wider text-left">
              Task
            </th>
            <th className="text-slate-500 text-xs uppercase tracking-wider text-center">
              Priority
            </th>
            <th className="text-slate-500 text-xs uppercase tracking-wider text-center">
              Deadline
            </th>
            <th className="text-slate-500 text-xs uppercase tracking-wider text-right">
              Status
            </th>
            <th className="text-slate-500 text-xs uppercase tracking-wider text-right">
              Actions
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
                {/* Completed toggle */}
                <td className="py-3 pr-2">
                  <input
                    type="checkbox"
                    checked={task.isCompleted ?? false}
                    onChange={() => onToggleComplete?.(task)}
                    className="accent-emerald-500 cursor-pointer"
                    title="Toggle completed"
                  />
                </td>
                <td className={`py-3 text-white ${task.isCompleted ? "line-through text-slate-400" : ""}`}>
                  {task.name}
                </td>
                <td className="py-3 text-center">
                  {task.priority ? (
                    <span className={`text-xs font-medium ${PRIORITY_COLORS[task.priority] ?? "text-slate-400"}`}>
                      {task.priority}
                    </span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
                <td className="py-3 text-center text-slate-300">
                  {task.deadline
                    ? new Date(task.deadline).toLocaleDateString()
                    : "—"}
                </td>
                <td className="py-3 text-right">
                  <span className={statusColor}>{statusLabel}</span>
                </td>
                {/* Action buttons */}
                <td className="py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => onEdit?.(task)}
                      title="Edit task"
                      className="text-slate-400 hover:text-blue-400 transition-colors"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => {
                        if (window.confirm(`Delete "${task.name}"?`)) {
                          onDelete?.(task)
                        }
                      }}
                      title="Delete task"
                      className="text-slate-400 hover:text-red-400 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      </div>
    </div>
  )
}
