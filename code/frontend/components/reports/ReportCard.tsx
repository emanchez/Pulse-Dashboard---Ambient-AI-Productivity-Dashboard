"use client"

import React from "react"
import { ChevronRight, Pencil, Tag } from "lucide-react"
import type { ManualReportSchema } from "../../lib/api"

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
}

export default function ReportCard({ report, expanded, onEdit }: ReportCardProps) {
  if (expanded) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 border-l-4 border-l-cyan-500">
        {/* Top row */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white">{report.title}</h2>
            <span className="bg-cyan-500/20 text-cyan-400 text-xs font-medium px-2 py-0.5 rounded">
              LATEST
            </span>
          </div>
          <button
            onClick={() => onEdit(report)}
            className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-1.5 rounded-md transition-colors"
          >
            <Pencil size={14} />
            Edit Report
          </button>
        </div>

        {/* Date row */}
        <p className="text-slate-400 text-sm mb-4">
          {formatDateExpanded(report.createdAt)}
        </p>

        {/* Content area */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left – body */}
          <div className="col-span-2">
            <p className="text-cyan-400 text-xs font-bold tracking-widest uppercase mb-3">
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
      </div>
    )
  }

  // Collapsed variant
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl px-6 py-4">
      <div className="flex items-center justify-between gap-4">
        {/* Left – title + date */}
        <div className="flex-shrink-0 min-w-0">
          <h3 className="text-white font-semibold text-sm truncate">{report.title}</h3>
          <p className="text-slate-500 text-xs mt-0.5">
            {formatDateCollapsed(report.createdAt)}
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
          <ChevronRight size={16} className="text-slate-500" />
        </div>
      </div>
    </div>
  )
}
