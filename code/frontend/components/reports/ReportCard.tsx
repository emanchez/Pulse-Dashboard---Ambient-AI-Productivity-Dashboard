"use client"

import React, { useState } from "react"
import { ChevronRight, Pencil, Tag, Archive, Trash2, GitBranch, Loader2 } from "lucide-react"
import type { ManualReportSchema, CoPlanResponse, AIUsageSummary } from "../../lib/api"
import { coPlan } from "../../lib/api"
import InferenceCard from "../dashboard/InferenceCard"

function formatDateExpanded(dateStr: string): string {
  const d = new Date(dateStr)
  const options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "long",
    day: "numeric",
  }
  const datePart = d.toLocaleDateString("en-US", options)
  const hours = d.getHours()
  const minutes = d.getMinutes().toString().padStart(2, "0")
  const ampm = hours >= 12 ? "PM" : "AM"
  const h = hours % 12 || 12
  return `${datePart} • ${h}:${minutes} ${ampm}`
}

function formatDateCollapsed(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

interface ReportCardProps {
  report: ManualReportSchema
  expanded: boolean
  onEdit: (report: ManualReportSchema) => void
  onToggle?: () => void
  onDelete?: (id: string) => void
  onArchive?: (id: string) => void
  token?: string
  coPlanUsage?: { used: number; limit: number } | null
}

export default function ReportCard({ report, expanded, onEdit, onToggle, onDelete, onArchive, token, coPlanUsage }: ReportCardProps) {
  const [coPlanResult, setCoPlanResult] = useState<CoPlanResponse | null>(null)
  const [coPlanLoading, setCoPlanLoading] = useState(false)
  const [coPlanError, setCoPlanError] = useState<string | null>(null)
  const [coPlanDismissed, setCoPlanDismissed] = useState(false)

  const coPlanAtLimit = coPlanUsage ? coPlanUsage.used >= coPlanUsage.limit : false

  const handleAnalyze = async () => {
    if (!token || coPlanAtLimit) return
    setCoPlanLoading(true)
    setCoPlanError(null)
    setCoPlanDismissed(false)
    try {
      const result = await coPlan(token, report.id ?? "")
      setCoPlanResult(result)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : ""
      if (msg.includes("429")) {
        setCoPlanError("Daily co-plan limit reached. Try again tomorrow.")
      } else if (msg.includes("503")) {
        setCoPlanError("AI features are currently disabled.")
      } else {
        setCoPlanError("Failed to analyze report.")
      }
    } finally {
      setCoPlanLoading(false)
    }
  }

  if (expanded) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 border-l-4 border-l-accent-primary accent-transition">
        {/* Top row */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3 cursor-pointer" onClick={onToggle}>
            <h2 className="text-xl font-bold text-white">{report.title}</h2>
            <span className="bg-accent-bg text-accent-light text-xs font-medium px-2 py-0.5 rounded accent-transition">
              LATEST
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleAnalyze}
              disabled={coPlanLoading || coPlanAtLimit}
              className={`flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-1.5 rounded-md transition-colors ${
                coPlanAtLimit ? "opacity-50 cursor-not-allowed" : ""
              }`}
              title={coPlanAtLimit ? "Daily co-plan limit reached" : "Analyze report for conflicts"}
            >
              {coPlanLoading ? <Loader2 size={14} className="animate-spin" /> : <GitBranch size={14} />}
              Analyze
            </button>
            <button
              onClick={() => onEdit(report)}
              className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-1.5 rounded-md transition-colors"
            >
              <Pencil size={14} />
              Edit Report
            </button>
            <button
              onClick={() => onArchive?.(report.id ?? "")}
              className="flex items-center gap-1.5 bg-amber-600 hover:bg-amber-700 text-white text-sm px-3 py-1.5 rounded-md transition-colors"
            >
              <Archive size={14} />
              Archive
            </button>
            <button
              onClick={() => {
                if (window.confirm("Delete this report? This cannot be undone.")) {
                  onDelete?.(report.id ?? "")
                }
              }}
              className="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-sm px-3 py-1.5 rounded-md transition-colors"
            >
              <Trash2 size={14} />
              Delete
            </button>
          </div>
        </div>

        {/* Date row */}
        <p className="text-slate-400 text-sm mb-4">
          {formatDateExpanded(report.createdAt ?? "")}
        </p>

        {/* Content area */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left – body */}
          <div className="col-span-2">
            <p className="text-accent-light text-xs font-bold tracking-widest uppercase mb-3 accent-transition">
              STRATEGIC NARRATIVE
            </p>
            <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
              {report.body}
            </div>
          </div>

          {/* Right – tags */}
          <div>
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
              <p className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-3">
                TAGS
              </p>
              <div className="flex flex-wrap gap-2">
                {report.tags && report.tags.length > 0 ? (
                  report.tags.map((tag) => (
                    <span
                      key={tag}
                      className="bg-slate-700 text-slate-300 text-xs px-2.5 py-1 rounded"
                    >
                      {tag}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-500 text-xs">No tags</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Co-plan result */}
        {coPlanError && !coPlanDismissed && (
          <div className="mt-4">
            <InferenceCard
              type="warning"
              title="Analysis Failed"
              body={coPlanError}
              onDismiss={() => setCoPlanDismissed(true)}
            />
          </div>
        )}
        {coPlanResult && !coPlanError && !coPlanDismissed && (
          <div className="mt-4">
            {coPlanResult.hasConflict ? (
              <InferenceCard
                type="question"
                title="Conflict Detected"
                body={coPlanResult.conflictDescription || "A potential conflict was found in this report."}
                detail={coPlanResult.resolutionQuestion}
                onDismiss={() => setCoPlanDismissed(true)}
              />
            ) : (
              <InferenceCard
                type="insight"
                title="No Conflicts Found"
                body="Report analysis complete — no ambiguity or conflicting goals detected."
                onDismiss={() => setCoPlanDismissed(true)}
              />
            )}
          </div>
        )}
      </div>
    )
  }

  // Collapsed variant
  return (
    <div
      className="bg-slate-800/50 border border-slate-700 rounded-xl px-6 py-4 cursor-pointer"
      onClick={onToggle}
    >
      <div className="flex items-center justify-between gap-4">
        {/* Left – title + date */}
        <div className="flex-shrink-0 min-w-0">
          <h3 className="text-white font-semibold text-sm truncate">{report.title}</h3>
          <p className="text-slate-500 text-xs mt-0.5">
            {formatDateCollapsed(report.createdAt ?? "")}
          </p>
        </div>

        {/* Center – body preview */}
        <p className="text-slate-400 text-sm truncate flex-1 mx-4">
          {report.body}
        </p>

        {/* Right – badges + chevron */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {report.status === "archived" && (
            <span className="border border-rose-500 text-rose-400 text-xs px-2 py-0.5 rounded">
              ARCHIVED
            </span>
          )}
          <ChevronRight
            size={16}
            className={`text-slate-500 transition-transform ${expanded ? "rotate-90" : ""}`}
          />
        </div>
      </div>
    </div>
  )
}
