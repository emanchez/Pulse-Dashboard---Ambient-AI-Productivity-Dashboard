"use client"

import { useState, useEffect, useCallback } from "react"
import { Plus, CalendarOff, ChevronDown, ChevronRight, Loader2 } from "lucide-react"
import type { SystemStateSchema } from "../../lib/api"
import { listSystemStates, deleteSystemState } from "../../lib/api"
import SystemStateCard from "./SystemStateCard"
import SystemStateForm from "./SystemStateForm"

interface SystemStateManagerProps {
  token: string
  onStateChange?: () => void
}

export default function SystemStateManager({ token, onStateChange }: SystemStateManagerProps) {
  const [states, setStates] = useState<SystemStateSchema[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingState, setEditingState] = useState<SystemStateSchema | null>(null)
  const [showPast, setShowPast] = useState(false)

  const fetchStates = useCallback(async () => {
    try {
      const data = await listSystemStates(token)
      setStates(data)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchStates()
  }, [fetchStates])

  // Categorize states
  const now = new Date()

  const active = states
    .filter((s) => {
      const start = new Date(s.startDate)
      const end = s.endDate ? new Date(s.endDate) : null
      return start <= now && (!end || end >= now)
    })
    .sort((a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime())

  const upcoming = states
    .filter((s) => new Date(s.startDate) > now)
    .sort((a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime())

  const past = states
    .filter((s) => s.endDate && new Date(s.endDate) < now)
    .sort((a, b) => new Date(b.startDate).getTime() - new Date(a.startDate).getTime())

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this pause?")) return
    try {
      await deleteSystemState(token, id)
      await fetchStates()
      onStateChange?.()
    } catch {
      /* ignore */
    }
  }

  const handleEdit = (state: SystemStateSchema) => {
    setEditingState(state)
    setShowForm(true)
  }

  const handleFormSave = () => {
    setShowForm(false)
    setEditingState(null)
    fetchStates()
    onStateChange?.()
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">System Pauses</h2>
        <button
          onClick={() => {
            setEditingState(null)
            setShowForm(true)
          }}
          className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors cursor-pointer"
        >
          <Plus size={14} />
          Schedule Pause
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-4">
          <Loader2 size={20} className="animate-spin text-slate-400" />
        </div>
      )}

      {/* Empty state */}
      {!loading && states.length === 0 && (
        <div className="text-center py-8">
          <CalendarOff size={40} className="mx-auto text-slate-600 mb-3" />
          <p className="text-slate-400 text-sm">
            No scheduled pauses. Use &quot;Schedule Pause&quot; to schedule vacation or leave periods.
          </p>
        </div>
      )}

      {/* Active states */}
      {active.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold tracking-widest text-emerald-400 uppercase">
            Currently Active
          </p>
          {active.map((s) => (
            <SystemStateCard key={s.id} state={s} onEdit={handleEdit} onDelete={handleDelete} />
          ))}
        </div>
      )}

      {/* Upcoming states */}
      {upcoming.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold tracking-widest text-blue-400 uppercase">Upcoming</p>
          {upcoming.map((s) => (
            <SystemStateCard key={s.id} state={s} onEdit={handleEdit} onDelete={handleDelete} />
          ))}
        </div>
      )}

      {/* Past states (collapsible) */}
      {past.length > 0 && (
        <div>
          <button
            onClick={() => setShowPast(!showPast)}
            className="flex items-center gap-1.5 text-slate-400 hover:text-slate-300 text-sm transition-colors cursor-pointer"
          >
            {showPast ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            {showPast ? "Hide" : "Show"} past pauses ({past.length})
          </button>
          {showPast && (
            <div className="space-y-2 mt-2">
              {past.map((s) => (
                <SystemStateCard key={s.id} state={s} onEdit={handleEdit} onDelete={handleDelete} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <SystemStateForm
          mode={editingState ? "edit" : "create"}
          state={editingState ?? undefined}
          token={token}
          onClose={() => {
            setShowForm(false)
            setEditingState(null)
          }}
          onSave={handleFormSave}
        />
      )}
    </div>
  )
}
