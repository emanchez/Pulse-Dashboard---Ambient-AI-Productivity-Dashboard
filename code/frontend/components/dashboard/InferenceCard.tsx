"use client"

import React from "react"
import { Lightbulb, HelpCircle, AlertTriangle, X } from "lucide-react"

export type InferenceCardType = "insight" | "question" | "warning"

interface InferenceCardProps {
  type: InferenceCardType
  title: string
  body: string
  detail?: string | null
  onDismiss?: () => void
}

const TYPE_CONFIG: Record<InferenceCardType, {
  icon: React.ElementType
  borderClass: string
  iconClass: string
  bgClass: string
  labelClass: string
  label: string
}> = {
  insight: {
    icon: Lightbulb,
    borderClass: "border-l-emerald-500",
    iconClass: "text-emerald-400",
    bgClass: "bg-emerald-500/10",
    labelClass: "text-emerald-400",
    label: "INSIGHT",
  },
  question: {
    icon: HelpCircle,
    borderClass: "border-l-amber-500",
    iconClass: "text-amber-400",
    bgClass: "bg-amber-500/10",
    labelClass: "text-amber-400",
    label: "QUESTION",
  },
  warning: {
    icon: AlertTriangle,
    borderClass: "border-l-rose-500",
    iconClass: "text-rose-400",
    bgClass: "bg-rose-500/10",
    labelClass: "text-rose-400",
    label: "WARNING",
  },
}

export default function InferenceCard({
  type,
  title,
  body,
  detail,
  onDismiss,
}: InferenceCardProps) {
  const config = TYPE_CONFIG[type]
  const Icon = config.icon

  return (
    <div
      className={`${config.bgClass} border border-slate-700 border-l-4 ${config.borderClass} rounded-lg p-4 relative`}
    >
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="absolute top-2 right-2 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Dismiss"
        >
          <X size={14} />
        </button>
      )}
      <div className="flex items-start gap-3">
        <Icon size={16} className={`${config.iconClass} mt-0.5 shrink-0`} />
        <div className="min-w-0 flex-1">
          <span className={`${config.labelClass} text-xs font-bold tracking-widest uppercase`}>
            {config.label}
          </span>
          <p className="text-slate-200 text-sm font-medium mt-1">{title}</p>
          <p className="text-slate-400 text-xs mt-1 leading-relaxed">{body}</p>
          {detail && (
            <p className="text-slate-500 text-xs mt-2 italic">{detail}</p>
          )}
        </div>
      </div>
    </div>
  )
}
