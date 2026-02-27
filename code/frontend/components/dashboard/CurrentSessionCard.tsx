"use client"

import React from "react"
import { FileText } from "lucide-react"
import { SessionLogSchema } from "../../lib/generated/types.gen"

interface CurrentSessionCardProps {
  session: SessionLogSchema | null
}

export default function CurrentSessionCard({ session }: CurrentSessionCardProps) {
  const elapsed = session?.elapsedMinutes ?? 0
  const goal = session?.goalMinutes ?? 0
  const percent = goal > 0 ? Math.min((elapsed / goal) * 100, 100) : 0

  return (
    <div className="bg-slate-800 rounded-xl p-5 relative overflow-hidden">
      <FileText className="absolute right-4 bottom-4 text-slate-700/40" size={64} />
      <span className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
        Current Session
      </span>
      {session ? (
        <>
          <h3 className="text-lg font-semibold text-white mt-1">
            {session.taskName}
          </h3>
          <p className="text-blue-400 text-sm">{elapsed}m elapsed</p>
          <div className="w-full bg-slate-700 rounded-full h-1.5 mt-3">
            <div
              className="bg-blue-500 h-1.5 rounded-full transition-all"
              style={{ width: `${percent}%` }}
            />
          </div>
          <span className="text-slate-500 text-xs">
            Goal: {session.goalMinutes ?? 0} mins
          </span>
        </>
      ) : (
        <p className="text-slate-500 text-sm mt-2">No active session</p>
      )}
    </div>
  )
}
