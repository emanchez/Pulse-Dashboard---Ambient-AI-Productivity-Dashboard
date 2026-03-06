"use client"

import { useState } from "react"
import { X, Loader2 } from "lucide-react"
import type { SystemStateSchema, SystemStateCreate, SystemStateUpdate } from "../../lib/api"
import { createSystemState, updateSystemState } from "../../lib/api"

interface SystemStateFormProps {
  mode: "create" | "edit"
  state?: SystemStateSchema
  token: string
  onClose: () => void
  onSave: () => void
}

function toLocalDatetime(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function SystemStateForm({ mode, state, token, onClose, onSave }: SystemStateFormProps) {
  const [modeType, setModeType] = useState(state?.modeType || "vacation")
  const [startDate, setStartDate] = useState(state?.startDate ? toLocalDatetime(state.startDate) : "")
  const [endDate, setEndDate] = useState(state?.endDate ? toLocalDatetime(state.endDate) : "")
  const [description, setDescription] = useState(state?.description || "")
  const [requiresRecovery, setRequiresRecovery] = useState(state?.requiresRecovery ?? true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit() {
    setError(null)
    if (!startDate) {
      setError("Start date is required.")
      return
    }

    if (endDate && new Date(endDate) <= new Date(startDate)) {
      setError("End date must be after start date.")
      return
    }

    const payload: SystemStateCreate = {
      modeType,
      startDate: new Date(startDate).toISOString(),
      endDate: endDate ? new Date(endDate).toISOString() : undefined,
      description: description || undefined,
      requiresRecovery,
    }

    setSaving(true)
    try {
      if (mode === "edit" && state) {
        await updateSystemState(token, state.id, payload as SystemStateUpdate)
      } else {
        await createSystemState(token, payload)
      }
      onSave()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      if (message.includes("409")) {
        setError("This schedule overlaps with an existing pause. Please adjust the dates.")
      } else {
        setError(message || "Failed to save. Please try again.")
      }
    } finally {
      setSaving(false)
    }
  }

  const modeOptions = [
    { value: "vacation", label: "Vacation", selectedClass: "bg-sky-500/20 text-sky-400 border-sky-500" },
    { value: "leave", label: "Leave", selectedClass: "bg-violet-500/20 text-violet-400 border-violet-500" },
  ] as const

  const inputClass =
    "bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white w-full focus:border-blue-500 focus:outline-none [color-scheme:dark]"

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-lg relative">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold text-white">
            {mode === "edit" ? "Edit Pause" : "Schedule a Pause"}
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="space-y-4">
          {/* Mode Type */}
          <div>
            <label className="block text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">
              Mode
            </label>
            <div className="flex gap-2">
              {modeOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setModeType(opt.value)}
                  className={`border rounded-lg px-4 py-2 text-sm font-medium cursor-pointer transition-colors ${
                    modeType === opt.value
                      ? opt.selectedClass
                      : "bg-slate-900 text-slate-400 border-slate-600"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Start Date */}
          <div>
            <label className="block text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">
              Start Date
            </label>
            <input
              type="datetime-local"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={inputClass}
            />
          </div>

          {/* End Date */}
          <div>
            <label className="block text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">
              End Date (optional)
            </label>
            <input
              type="datetime-local"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className={inputClass}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g., Spring break vacation"
              className={`${inputClass} min-h-[80px] resize-y`}
            />
          </div>

          {/* Requires Recovery Toggle */}
          <div className="flex items-center justify-between">
            <label className="text-sm text-slate-300">Requires Re-entry Period</label>
            <button
              type="button"
              onClick={() => setRequiresRecovery(!requiresRecovery)}
              className={`relative w-10 h-5 rounded-full transition-colors cursor-pointer ${
                requiresRecovery ? "bg-blue-600" : "bg-slate-600"
              }`}
              aria-label="Toggle requires recovery"
            >
              <span
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  requiresRecovery ? "translate-x-5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm px-3 py-2 rounded-lg">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={saving}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              {mode === "edit" ? "Update Pause" : "Schedule Pause"}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
