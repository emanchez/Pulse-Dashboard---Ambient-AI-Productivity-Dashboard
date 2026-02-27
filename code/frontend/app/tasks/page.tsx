"use client"

import React from "react"
import { useAuth } from "../../lib/hooks/useAuth"
import LoadingSpinner from "../LoadingSpinner"
import BentoGrid from "../../components/BentoGrid"
import FocusHeader from "../../components/dashboard/FocusHeader"
import ProductivityPulseCard from "../../components/dashboard/ProductivityPulseCard"
import CurrentSessionCard from "../../components/dashboard/CurrentSessionCard"
import DailyGoalsCard from "../../components/dashboard/DailyGoalsCard"
import QuickAccessCard from "../../components/dashboard/QuickAccessCard"
import TaskQueueTable from "../../components/dashboard/TaskQueueTable"
import { Users, FileText } from "lucide-react"

export default function TasksPage() {
  const { token, ready, logout } = useAuth()

  if (!ready || !token) {
    return <LoadingSpinner />
  }

  return (
    <BentoGrid
      variant="tasks-dashboard"
      row1Left={<FocusHeader silenceState="engaged" />}
      row1Right={
        <ProductivityPulseCard token={token} onAuthError={logout} />
      }
      row2A={<CurrentSessionCard token={token} onAuthError={logout} />}
      row2B={<DailyGoalsCard token={token} onAuthError={logout} />}
      row2C={
        <div className="flex flex-col gap-4">
          <QuickAccessCard
            icon={Users}
            title="Team Sync"
            subtitle="Starts in 14 mins"
          />
          <QuickAccessCard
            icon={FileText}
            title="Docs & Assets"
            subtitle="Internal wiki access"
          />
        </div>
      }
      row3={
        <TaskQueueTable
          token={token}
          activeSessionTaskId={undefined}
          onAuthError={logout}
        />
      }
    />
  )
}
