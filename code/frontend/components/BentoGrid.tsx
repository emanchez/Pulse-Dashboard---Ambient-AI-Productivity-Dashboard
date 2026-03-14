import React from 'react'

interface BentoGridProps {
  // default variant props
  zoneA?: React.ReactNode
  zoneB?: React.ReactNode
  className?: string
  // tasks-dashboard variant
  variant?: "default" | "tasks-dashboard"
  row1Left?: React.ReactNode
  row1Right?: React.ReactNode
  row2A?: React.ReactNode
  row2B?: React.ReactNode
  row2C?: React.ReactNode
  row3?: React.ReactNode
  // Zone C — Reasoning Sidebar (desktop: right column, mobile: bottom section)
  zoneC?: React.ReactNode
}

export default function BentoGrid({
  zoneA,
  zoneB,
  className,
  variant = "default",
  row1Left,
  row1Right,
  row2A,
  row2B,
  row2C,
  row3,
  zoneC,
}: BentoGridProps) {
  if (variant === "tasks-dashboard") {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Main content — Zones A & B */}
        <div className={`${zoneC ? "lg:col-span-9" : "lg:col-span-12"} space-y-4`}>
          {/* Row 1 — 12-column split */}
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-12 md:col-span-8">{row1Left}</div>
            <div className="col-span-12 md:col-span-4">{row1Right}</div>
          </div>

          {/* Row 2 — 3-column */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>{row2A}</div>
            <div>{row2B}</div>
            <div>{row2C}</div>
          </div>

          {/* Row 3 — full width */}
          <div className="w-full">{row3}</div>
        </div>

        {/* Zone C — Reasoning Sidebar (desktop: right column, mobile: bottom) */}
        {zoneC && (
          <div className="lg:col-span-3">
            {zoneC}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={`grid grid-cols-1 md:grid-cols-4 gap-4 ${className ?? ''}`}>
      {/* Zone A — Silence Indicator (spans 2 cols) */}
      <div className="md:col-span-2 bg-white p-4 rounded-lg shadow">
        {zoneA ?? <div className="h-32 animate-pulse bg-gray-100 rounded" />}
      </div>

      {/* Zone B — Task Board (spans 2 cols) */}
      <div className="md:col-span-2 bg-white p-4 rounded-lg shadow">
        {zoneB ?? <div className="h-32 animate-pulse bg-gray-100 rounded" />}
      </div>
    </div>
  )
}
