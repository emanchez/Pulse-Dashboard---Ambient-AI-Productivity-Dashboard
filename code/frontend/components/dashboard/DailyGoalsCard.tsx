"use client"

import React from "react"
import { CheckCircle2 } from "lucide-react"
import { TaskSchema } from "../../lib/generated/types.gen"

interface DailyGoalsCardProps {
  tasks: TaskSchema[]
}

export default function DailyGoalsCard({ tasks }: DailyGoalsCardProps) {
  const today = new Date().toISOString().slice(0, 10)
  const todays = tasks.filter(
    (t) => t.deadline?.slice(0, 10) === today
  )
  const list = todays.length > 0 ? todays : tasks.slice(0, 5)

  const doneCount = list.filter((t) => t.isCompleted).length
  const totalCount = list.length
  const firstIncompleteIdx = list.findIndex((t) => !t.isCompleted)

  return (
    <div className="bg-slate-800 rounded-xl p-5">
      <div className="flex justify-between items-center">
        <h3 className="text-base font-semibold text-white">Daily Goals</h3>
        <span className="text-slate-400 text-sm">
          {doneCount} of {totalCount} completed
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {list.map((task, idx) => {
          const completed = task.isCompleted
          const isCurrent = idx === firstIncompleteIdx
          return (
            <div key={task.id ?? task.name} className="flex items-center gap-2">
              {completed ? (
                <CheckCircle2 className="text-emerald-500 shrink-0" size={16} />
              ) : isCurrent ? (
                <div className="w-4 h-4 rounded-full border-2 border-blue-400 shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-slate-600 shrink-0" />
              )}
              <span
                className={
                  completed
                    ? "line-through text-slate-500 text-sm"
                    : isCurrent
                    ? "text-white text-sm"
                    : "text-slate-400 text-sm"
                }
              >
                {task.name}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
