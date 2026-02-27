"use client"

import React, { useCallback, useEffect, useState } from "react"
import {
  AreaChart,
  Area,
  XAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { getFlowState } from "../../lib/api"
import { FlowStateSchema } from "../../lib/generated/types.gen"

interface ProductivityPulseCardProps {
  token: string
  onAuthError?: () => void
}

export default function ProductivityPulseCard({ token, onAuthError }: ProductivityPulseCardProps) {
  const [flow, setFlow] = useState<FlowStateSchema | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchFlow = useCallback(async () => {
    try {
      const data = await getFlowState(token)
      setFlow(data)
      setError(null)
    } catch (err: any) {
      if (err?.message?.includes("401")) {
        onAuthError?.()
        return
      }
      setError(err?.message ?? "Failed to fetch flow state")
    }
  }, [token, onAuthError])

  useEffect(() => {
    fetchFlow()
    const id = setInterval(fetchFlow, 60000)
    return () => clearInterval(id)
  }, [fetchFlow])

  if (error) {
    return (
      <div className="bg-slate-800 rounded-xl p-5 h-full">
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    )
  }

  if (!flow) {
    return (
      <div className="bg-slate-800 rounded-xl p-5 h-full">
        <div className="h-6 w-1/3 animate-pulse bg-slate-700 rounded" />
        <div className="h-6 w-1/4 mt-2 animate-pulse bg-slate-700 rounded" />
      </div>
    )
  }

  const { flowPercent, changePercent, series } = flow

  return (
    <div className="bg-slate-800 rounded-xl p-5 h-full">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
          Productivity Pulse
        </span>
        <div className="flex items-center gap-2">
          <span className="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded">
            Last 6 hours
          </span>
          <span className={changePercent >= 0 ? "text-emerald-400" : "text-rose-400"}>
            {changePercent >= 0 ? `+${changePercent}%` : `${changePercent}%`}
          </span>
        </div>
      </div>
      <h2 className="text-2xl font-bold text-white mt-1">
        Flow State <span className="text-blue-400">{flowPercent}%</span>
      </h2>
      <div className="h-40 mt-4">
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={series}>
            <defs>
              <linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="activityScore"
              stroke="#3b82f6"
              fill="url(#flowGrad)"
              strokeWidth={2}
              dot={false}
            />
            <XAxis
              dataKey="time"
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#1e293b",
                border: "none",
                borderRadius: "8px",
                color: "#fff",
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
