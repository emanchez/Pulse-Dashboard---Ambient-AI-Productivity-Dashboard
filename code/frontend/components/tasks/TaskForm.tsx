"use client"

import React, { useState } from "react"
import { X } from "lucide-react"
import { createTask, updateTask } from "../../lib/api"
import type { Task, TaskCreate, TaskUpdate } from "../../lib/api"

interface TaskFormProps {
  mode: "create" | "edit"
  task?: Task
  token: string
  onClose: () => void
  onSave: () => void
}

const PRIORITIES = ["High", "Medium", "Low"] as const

export default function TaskForm({ mode, task, token, onClose, onSave }: TaskFormProps) {
  const [name, setName] = useState(task?.name ?? "")
  const [priority, setPriority] = useState<string>(task?.priority ?? "")
  const [deadline, setDeadline] = useState(
    task?.deadline ? new Date(task.deadline).toISOString().slice(0, 10) : ""
  )
  const [notes, setNotes] = useState(task?.notes ?? "")
  const [tags, setTags] = useState(task?.tags ?? "")
  const [saving, setSaving] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)

  const validate = (): boolean => {
    if (!name.trim()) {
      setNameError("Task name is required")
      return false
    }
    setNameError(null)
    return true
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setSaving(true)
    setApiError(null)
    try {
      if (mode === "create") {
        const data: TaskCreate = {
          name: name.trim(),
          priority: priority || undefined,
          deadline: deadline ? new Date(deadline).toISOString() : undefined,
          notes: notes.trim() || undefined,
          tags: tags.trim() || undefined,
        }
        await createTask(token, data)
      } else if (task?.id) {
        const data: TaskUpdate = {
          name: name.trim(),
          priority: priority || undefined,
          deadline: deadline ? new Date(deadline).toISOString() : undefined,
          notes: notes.trim() || undefined,
          tags: tags.trim() || undefined,
        }
        await updateTask(token, task.id, data)
      }
      onSave()
    } catch (err) {
      console.error("Failed to save task:", err)
      setApiError(err instanceof Error ? err.message : "Failed to save task. Please try again.")
    } finally {
      setSaving(false)
    }
  }

  const inputClass =
    "w-full bg-slate-900 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 placeholder-slate-500"
  const labelClass = "block text-sm font-medium text-slate-300 mb-1"

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">
            {mode === "create" ? "Create Task" : "Edit Task"}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* API error banner */}
        {apiError && (
          <div className="mb-4 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg px-4 py-3 text-sm">
            {apiError}
          </div>
        )}

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className={labelClass}>
              Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Task name"
              className={`${inputClass} ${nameError ? "border-red-500" : ""}`}
              autoFocus
            />
            {nameError && (
              <p className="mt-1 text-xs text-red-400">{nameError}</p>
            )}
          </div>

          {/* Priority */}
          <div>
            <label className={labelClass}>Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className={inputClass}
            >
              <option value="">None</option>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          {/* Deadline */}
          <div>
            <label className={labelClass}>Deadline</label>
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className={inputClass}
            />
          </div>

          {/* Notes */}
          <div>
            <label className={labelClass}>Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional notes…"
              rows={3}
              className={`${inputClass} resize-none`}
            />
          </div>

          {/* Tags */}
          <div>
            <label className={labelClass}>Tags</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="comma, separated, tags"
              className={inputClass}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 rounded-lg text-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving…" : mode === "create" ? "Create Task" : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  )
}
