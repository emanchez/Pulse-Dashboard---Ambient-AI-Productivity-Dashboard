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
import TaskQueueTable from "../../components/dashboard/TaskQueueTable"
import { useSilenceState } from "../../components/SilenceStateProvider"
import { getFlowState, getActiveSession, listTasks } from "../../lib/api"
import type { FlowStateSchema, SessionLogSchema, Task } from "../../lib/api"

export default function TasksPage() {
  const { token, ready, logout } = useAuth()
  const { silenceState, gapMinutes, pausedUntil } = useSilenceState()

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
        const [flow, session, taskList] = await Promise.all([
          getFlowState(token),
          getActiveSession(token),
          listTasks(token),
        ])
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
        silenceState={silenceState}
        gapMinutes={gapMinutes}
        onLogout={logout}
      />
      <main className="px-6 py-6">
        <BentoGrid
          variant="tasks-dashboard"
          row1Left={
            <FocusHeader
              silenceState={silenceState ?? "engaged"}
              pausedUntil={pausedUntil}
            />
          }
          row1Right={<ProductivityPulseCard flowState={flowState} />}
          row2A={
            <CurrentSessionCard
              session={activeSession}
              token={token}
              tasks={tasks}
              onStartSession={(s) => setActiveSession(s)}
              onStopSession={() => setActiveSession(null)}
            />
          }
          row2B={<DailyGoalsCard tasks={tasks} />}
          row2C={
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-slate-500 text-sm flex items-center justify-center h-full">
              Quick actions — coming soon
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
