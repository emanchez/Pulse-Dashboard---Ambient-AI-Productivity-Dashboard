import React from 'react'

interface BentoGridProps {
  zoneA?: React.ReactNode
  zoneB?: React.ReactNode
  className?: string
}

export default function BentoGrid({ zoneA, zoneB, className }: BentoGridProps) {
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
