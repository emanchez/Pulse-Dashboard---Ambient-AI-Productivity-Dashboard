"use client"

import React, { useState, useEffect, useRef } from "react"
import { X, Check, Tag, Plus } from "lucide-react"
import { createReport, updateReport } from "../../lib/api"
import type {
  ManualReportSchema,
  ManualReportCreate,
  ManualReportUpdate,
  Task,
} from "../../lib/api"

interface ReportFormProps {
  mode: "create" | "edit"
  report?: ManualReportSchema
  token: string
  tasks: Task[]
  onClose: () => void
  onSave: () => void
}

export default function ReportForm({
  mode,
  report,
  token,
  tasks,
  onClose,
  onSave,
}: ReportFormProps) {
  const [title, setTitle] = useState(report?.title ?? "")
  const [body, setBody] = useState(report?.body ?? "")
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>(
    report?.associatedTaskIds ?? []
  )
  const [tags, setTags] = useState<string[]>(report?.tags ?? [])
  const [tagInput, setTagInput] = useState("")
  const [status, setStatus] = useState<string>(report?.status ?? "published")
  const [showTaskDropdown, setShowTaskDropdown] = useState(false)
  const [saving, setSaving] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [errors, setErrors] = useState<{ title?: string; body?: string }>({})

  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setShowTaskDropdown(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const toggleTask = (taskId: string) => {
    setSelectedTaskIds((prev) =>
      prev.includes(taskId)
        ? prev.filter((id) => id !== taskId)
        : [...prev, taskId]
    )
  }

  const addTag = (value: string) => {
    const trimmed = value.trim()
    if (trimmed && !tags.includes(trimmed)) {
      setTags((prev) => [...prev, trimmed])
    }
  }

  const removeTag = (tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag))
  }

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      const parts = tagInput.split(",").map((s) => s.trim()).filter(Boolean)
      parts.forEach(addTag)
      setTagInput("")
    }
  }

  const validate = (): boolean => {
    const errs: { title?: string; body?: string } = {}
    if (!title.trim()) errs.title = "Title is required"
    if (!body.trim()) errs.body = "Body is required"
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setSaving(true)
    setApiError(null)
    try {
      if (mode === "create") {
        const data: ManualReportCreate = {
          title: title.trim(),
          body: body.trim(),
          associatedTaskIds: selectedTaskIds,
          tags,
          status,
        }
        await createReport(token, data)
      } else if (report) {
        const data: ManualReportUpdate = {
          title: title.trim(),
          body: body.trim(),
          associatedTaskIds: selectedTaskIds,
          tags,
          status,
        }
        await updateReport(token, report.id ?? "", data)
      }
      onSave()
    } catch (err) {
      console.error("Failed to save report:", err)
      setApiError(err instanceof Error ? err.message : "Failed to save report. Please try again.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">
            {mode === "create" ? "Create New Report" : "Edit Report"}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Title field */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-300 mb-1.5">
            Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Report title..."
            className="bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white w-full focus:outline-none focus:border-blue-500 transition-colors"
          />
          {errors.title && (
            <p className="text-red-400 text-xs mt-1">{errors.title}</p>
          )}
        </div>

        {/* Body field */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-300 mb-1.5">
            Body
          </label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your strategic narrative..."
            className="bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white w-full min-h-[200px] resize-y focus:outline-none focus:border-blue-500 transition-colors"
          />
          {errors.body && (
            <p className="text-red-400 text-xs mt-1">{errors.body}</p>
          )}
        </div>

        {/* Task linking */}
        <div className="mb-4" ref={dropdownRef}>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">
            Linked Tasks
          </label>
          {/* Selected task pills */}
          {selectedTaskIds.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {selectedTaskIds.map((taskId) => {
                const task = tasks.find((t) => t.id === taskId)
                return (
                  <span
                    key={taskId}
                    className="flex items-center gap-1 bg-blue-600/20 text-blue-400 text-xs px-2.5 py-1 rounded"
                  >
                    {task?.name ?? taskId}
                    <button
                      onClick={() => toggleTask(taskId)}
                      className="hover:text-blue-200"
                    >
                      <X size={12} />
                    </button>
                  </span>
                )
              })}
            </div>
          )}
          <button
            type="button"
            onClick={() => setShowTaskDropdown((prev) => !prev)}
            className="flex items-center gap-1.5 bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-slate-400 text-sm w-full text-left hover:border-slate-500 transition-colors"
          >
            <Plus size={14} />
            Select tasks to link...
          </button>
          {showTaskDropdown && (
            <div className="mt-1 bg-slate-900 border border-slate-600 rounded-lg max-h-48 overflow-y-auto">
              {tasks.filter((t) => t.id != null).length === 0 ? (
                <p className="px-4 py-3 text-slate-500 text-sm">
                  No tasks available
                </p>
              ) : (
                tasks
                  .filter((t): t is typeof t & { id: string } => t.id != null)
                  .map((task) => (
                  <label
                    key={task.id}
                    className="flex items-center gap-3 px-4 py-2 hover:bg-slate-800 cursor-pointer text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={selectedTaskIds.includes(task.id)}
                      onChange={() => toggleTask(task.id)}
                      className="rounded border-slate-600"
                    />
                    <span className="text-slate-300">{task.name}</span>
                  </label>
                ))
              )}
            </div>
          )}
        </div>

        {/* Tags */}
        <div className="mb-4">
          <label className="flex items-center gap-1.5 text-sm font-medium text-slate-300 mb-1.5">
            <Tag size={14} />
            Tags
          </label>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="flex items-center gap-1 bg-slate-700 text-slate-300 text-xs px-2.5 py-1 rounded"
                >
                  {tag}
                  <button
                    onClick={() => removeTag(tag)}
                    className="hover:text-white"
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
            </div>
          )}
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleTagKeyDown}
            placeholder="Type a tag and press Enter..."
            className="bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white w-full focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>

        {/* Status toggle */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-1.5">
            Status
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setStatus("published")}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                status === "published"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-400 hover:text-white"
              }`}
            >
              <Check size={14} />
              Published
            </button>
            <button
              type="button"
              onClick={() => setStatus("draft")}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                status === "draft"
                  ? "bg-amber-600 text-white"
                  : "bg-slate-700 text-slate-400 hover:text-white"
              }`}
            >
              Draft
            </button>
          </div>
        </div>

        {/* API Error */}
        {apiError && (
          <div className="mb-4 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg px-4 py-3 text-sm">
            {apiError}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            {saving
              ? "Saving..."
              : mode === "create"
              ? "Save Report"
              : "Update Report"}
          </button>
        </div>
      </div>
    </div>
  )
}
