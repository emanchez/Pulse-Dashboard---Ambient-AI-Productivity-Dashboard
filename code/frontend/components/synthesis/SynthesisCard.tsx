"use client"

import React from "react"

function scoreToState(score: number): "engaged" | "stagnant" | "paused" {
  if (score >= 7) return "engaged"
  if (score >= 4) return "stagnant"
  return "paused"
}

function stateLabel(state: "engaged" | "stagnant" | "paused"): string {
  if (state === "engaged") return "ENGAGED"
  if (state === "stagnant") return "STAGNANT"
  return "PAUSED"
}

interface SynthesisCardProps {
  summary: string
  theme: string
  commitmentScore: number
  periodStart: string
  periodEnd: string
  createdAt: string
}

export default function SynthesisCard({
  summary,
  theme,
  commitmentScore,
  periodStart,
  periodEnd,
  createdAt,
}: SynthesisCardProps) {
  const state = scoreToState(commitmentScore)

  return (
    <div
      data-state={state}
      className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 border-l-4 border-l-[var(--accent-primary)] accent-transition"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-accent-light text-xs font-bold tracking-widest uppercase accent-transition">
            WEEKLY SYNTHESIS
          </span>
          <span className="bg-[var(--accent-bg)] text-accent-light text-xs font-medium px-2 py-0.5 rounded accent-transition">
            LATEST
          </span>
        </div>
        <span className="text-slate-500 text-xs">
          {new Date(createdAt).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </span>
      </div>

      {/* Body — grid layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Narrative — 2/3 */}
        <div className="md:col-span-2">
          <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
            {summary}
          </p>
          <div className="mt-4 text-xs text-slate-500">
            Period: {new Date(periodStart).toLocaleDateString()} –{" "}
            {new Date(periodEnd).toLocaleDateString()}
          </div>
        </div>

        {/* Sidebar — theme + gauge */}
        <div className="flex flex-col gap-4">
          <div>
            <span className="text-accent-light text-xs font-bold tracking-widest uppercase mb-2 block accent-transition">
              THEME
            </span>
            <span className="bg-slate-700 text-slate-300 text-sm px-3 py-1 rounded inline-block">
              {theme}
            </span>
          </div>
          <div>
            <span className="text-accent-light text-xs font-bold tracking-widest uppercase mb-2 block accent-transition">
              COMMITMENT
            </span>
            <div className="flex items-center gap-2">
              <span className="text-accent-light text-2xl font-bold accent-transition">
                {commitmentScore}
              </span>
              <span className="text-slate-500 text-sm">/10</span>
            </div>
            <CommitmentGaugeInline score={commitmentScore} />
          </div>
          <div>
            <span className="bg-[var(--accent-bg)] text-accent-light text-xs font-medium px-2 py-0.5 rounded accent-transition">
              {stateLabel(state)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

/** Inline gauge for use within SynthesisCard */
function CommitmentGaugeInline({ score }: { score: number }) {
  return (
    <div
      className="flex gap-1 mt-1"
      role="meter"
      aria-label="Commitment score"
      aria-valuenow={score}
      aria-valuemin={0}
      aria-valuemax={10}
    >
      {Array.from({ length: 10 }, (_, i) => (
        <div
          key={i}
          className={`h-2 flex-1 rounded-sm transition-colors duration-300 ${
            i < score
              ? "bg-[var(--accent-primary)]"
              : "bg-slate-700"
          }`}
        />
      ))}
    </div>
  )
}
