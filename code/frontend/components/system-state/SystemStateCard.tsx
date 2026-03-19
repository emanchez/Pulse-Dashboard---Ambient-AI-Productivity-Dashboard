"use client"

import { Pencil, Trash2, RefreshCw } from "lucide-react"
import type { SystemStateSchema } from "../../lib/api"

interface SystemStateCardProps {
  state: SystemStateSchema
  onEdit: (state: SystemStateSchema) => void
  onDelete: (id: string) => void
}

function getStateStatus(state: SystemStateSchema): "active" | "upcoming" | "expired" {
  const now = new Date()
  const start = new Date(state.startDate ?? "")
  const end = state.endDate ? new Date(state.endDate) : null
  if (start > now) return "upcoming"
  if (end && end < now) return "expired"
  return "active"
}

function formatShortDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

const statusConfig = {
  active: {
    dotClass: "w-2 h-2 rounded-full bg-emerald-400 animate-pulse",
    textClass: "text-emerald-400 text-xs",
    label: "Active",
  },
  upcoming: {
    dotClass: "w-2 h-2 rounded-full bg-blue-400",
    textClass: "text-blue-400 text-xs",
    label: "Upcoming",
  },
  expired: {
    dotClass: "w-2 h-2 rounded-full bg-slate-500",
    textClass: "text-slate-500 text-xs",
    label: "Expired",
  },
} as const

const modeBadgeConfig = {
  vacation: "bg-sky-500/20 text-sky-400 text-xs font-medium px-2 py-0.5 rounded uppercase",
  leave: "bg-violet-500/20 text-violet-400 text-xs font-medium px-2 py-0.5 rounded uppercase",
} as const

export default function SystemStateCard({ state, onEdit, onDelete }: SystemStateCardProps) {
  const status = getStateStatus(state)
  const { dotClass, textClass, label } = statusConfig[status]
  const badgeClass =
    modeBadgeConfig[state.modeType as keyof typeof modeBadgeConfig] ?? modeBadgeConfig.leave

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-3">
      {/* Top row */}
      <div className="flex items-center justify-between gap-3">
        {/* Left side */}
        <div className="flex items-center gap-3 flex-wrap min-w-0">
          <span className={badgeClass}>{state.modeType}</span>

          <span className="flex items-center gap-1.5">
            <span className={dotClass} />
            <span className={textClass}>{label}</span>
          </span>

          <span className="text-slate-300 text-sm">
            {formatShortDate(state.startDate ?? "")} →{" "}
            {state.endDate ? formatShortDate(state.endDate) : "Ongoing"}
          </span>

          {state.requiresRecovery && (
            <span className="flex items-center gap-1 text-amber-400 text-xs">
              <RefreshCw size={12} />
              Recovery
            </span>
          )}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => onEdit(state)}
            className="text-slate-400 hover:text-white cursor-pointer transition-colors"
            aria-label="Edit"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => onDelete(state.id ?? "")}
            className="text-slate-400 hover:text-rose-400 cursor-pointer transition-colors"
            aria-label="Delete"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Description */}
      {state.description && (
        <p className="text-slate-400 text-sm mt-2">{state.description}</p>
      )}
    </div>
  )
}
