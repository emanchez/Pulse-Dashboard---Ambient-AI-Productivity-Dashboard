"use client"

import React from "react"

interface CommitmentGaugeProps {
  score: number
}

export default function CommitmentGauge({ score }: CommitmentGaugeProps) {
  return (
    <div className="flex flex-col gap-1">
      <div
        className="flex gap-1"
        role="meter"
        aria-label="Commitment score"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={10}
      >
        {Array.from({ length: 10 }, (_, i) => (
          <div
            key={i}
            className={`h-3 flex-1 rounded-sm transition-colors duration-300 ${
              i < score
                ? "bg-[var(--accent-primary)]"
                : "bg-slate-700"
            }`}
          />
        ))}
      </div>
      <div className="flex justify-between text-xs text-slate-500">
        <span>0</span>
        <span>10</span>
      </div>
    </div>
  )
}
