"use client"

import React, { useState } from "react"
import { ChevronDown, FileText } from "lucide-react"
import ReportCard from "./ReportCard"
import type { ManualReportSchema } from "../../lib/api"

interface ReportListProps {
  reports: ManualReportSchema[]
  total: number
  loading: boolean
  onEdit: (report: ManualReportSchema) => void
  onLoadMore: () => void
  onDelete?: (id: string) => void
  onArchive?: (id: string) => void
}

export default function ReportList({
  reports,
  total,
  loading,
  onEdit,
  onLoadMore,
  onDelete,
  onArchive,
}: ReportListProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () => new Set(reports.length > 0 ? [reports[0].id] : [])
  )

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (reports.length === 0 && !loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <FileText size={48} className="text-slate-600 mb-4" />
        <p className="text-white font-medium mb-1">No reports yet</p>
        <p className="text-slate-400 text-sm">
          Create your first strategic report to get started.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {reports.map((report) => (
        <ReportCard
          key={report.id}
          report={report}
          expanded={expandedIds.has(report.id)}
          onEdit={onEdit}
          onToggle={() => toggleExpanded(report.id)}
          onDelete={onDelete}
          onArchive={onArchive}
        />
      ))}

      {total > reports.length && (
        <div className="flex flex-col items-center pt-4 pb-2">
          <button
            onClick={onLoadMore}
            className="flex flex-col items-center gap-1 text-slate-400 text-sm hover:text-slate-300 transition-colors"
          >
            <ChevronDown size={18} />
            <span>Load Historical Reports</span>
          </button>
        </div>
      )}
    </div>
  )
}
