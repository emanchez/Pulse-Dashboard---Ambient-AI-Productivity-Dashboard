"use client"

import React, { useEffect, useRef, useState } from "react"
import { useAuth } from "../../lib/hooks/useAuth"
import LoadingSpinner from "../LoadingSpinner"
import AppNavBar from "../../components/nav/AppNavBar"
import BentoGrid from "../../components/BentoGrid"
import FocusHeader from "../../components/dashboard/FocusHeader"
import ProductivityPulseCard from "../../components/dashboard/ProductivityPulseCard"
import CurrentSessionCard from "../../components/dashboard/CurrentSessionCard"
import DailyGoalsCard from "../../components/dashboard/DailyGoalsCard"
import QuickAccessCard from "../../components/dashboard/QuickAccessCard"
import TaskQueueTable from "../../components/dashboard/TaskQueueTable"
import { getPulse, getFlowState, getActiveSession, listTasks } from "../../lib/api"
import type { PulseStats, FlowStateSchema, SessionLogSchema, Task } from "../../lib/api"
import { Users, FileText } from "lucide-react"

export default function TasksPage() {
  const { token, ready, logout } = useAuth()

  const [pulseStats, setPulseStats] = useState<PulseStats | null>(null)
  const [flowState, setFlowState] = useState<FlowStateSchema | null>(null)
  const [activeSession, setActiveSession] = useState<SessionLogSchema | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  // Ref so polling callbacks always read the latest token without stale closures
  const tokenRef = useRef(token)
  useEffect(() => { tokenRef.current = token }, [token])

  useEffect(() => {
    if (!token) return

    const handleAuthError = (err: any) => {
      if (err?.message?.includes("401")) logout()
    }

    const fetchAll = async () => {
      try {
        const [pulse, flow, session, taskList] = await Promise.all([
          getPulse(token),
          getFlowState(token),
          getActiveSession(token),
          listTasks(token),
        ])
        setPulseStats(pulse)
        setFlowState(flow)
        setActiveSession(session)
        setTasks(taskList)
      } catch (err: any) {
        handleAuthError(err)
      } finally {
        setLoading(false)
      }
    }

    fetchAll()

    const pulseTimer = setInterval(async () => {
      try { setPulseStats(await getPulse(tokenRef.current!)) }
      catch (err: any) { handleAuthError(err) }
    }, 30_000)

    const sessTimer = setInterval(async () => {
      try { setActiveSession(await getActiveSession(tokenRef.current!)) }
      catch (err: any) { handleAuthError(err) }
    }, 30_000)

    const flowTimer = setInterval(async () => {
      try { setFlowState(await getFlowState(tokenRef.current!)) }
      catch (err: any) { handleAuthError(err) }
    }, 60_000)

    const taskTimer = setInterval(async () => {
      try { setTasks(await listTasks(tokenRef.current!)) }
      catch (err: any) { handleAuthError(err) }
    }, 60_000)

    return () => {
      clearInterval(pulseTimer)
      clearInterval(sessTimer)
      clearInterval(flowTimer)
      clearInterval(taskTimer)
    }
  }, [token, logout])

  if (!ready || !token || loading) {
    return <LoadingSpinner />
  }

  return (
    <>
      <AppNavBar
        silenceState={pulseStats?.silenceState}
        gapMinutes={pulseStats?.gapMinutes}
      />
      <main className="px-6 py-6">
        <BentoGrid
          variant="tasks-dashboard"
          row1Left={
            <FocusHeader
              silenceState={pulseStats?.silenceState ?? "engaged"}
              pausedUntil={pulseStats?.pausedUntil}
            />
          }
          row1Right={<ProductivityPulseCard flowState={flowState} />}
          row2A={<CurrentSessionCard session={activeSession} />}
          row2B={<DailyGoalsCard tasks={tasks} />}
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
              tasks={tasks}
              activeSessionTaskId={activeSession?.taskId ?? null}
            />
          }
        />
      </main>
    </>
  )
}
