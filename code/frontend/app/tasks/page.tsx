"use client"

import React, { useEffect, useRef, useState } from "react"
import { Plus } from "lucide-react"
import { useAuth } from "../../lib/hooks/useAuth"
import LoadingSpinner from "../LoadingSpinner"
import AppNavBar from "../../components/nav/AppNavBar"
import BentoGrid from "../../components/BentoGrid"
import FocusHeader from "../../components/dashboard/FocusHeader"
import ProductivityPulseCard from "../../components/dashboard/ProductivityPulseCard"
import CurrentSessionCard from "../../components/dashboard/CurrentSessionCard"
import DailyGoalsCard from "../../components/dashboard/DailyGoalsCard"
import TaskQueueTable from "../../components/dashboard/TaskQueueTable"
import TaskForm from "../../components/tasks/TaskForm"
import ReasoningSidebar from "../../components/dashboard/ReasoningSidebar"
import { useSilenceState } from "../../components/SilenceStateProvider"
import { getFlowState, getActiveSession, listTasks, updateTask, deleteTask } from "../../lib/api"
import { ApiError } from "../../lib/api"
import type { FlowStateSchema, SessionLogSchema, Task, TaskUpdate } from "../../lib/api"

export default function TasksPage() {
  const { token, ready, logout } = useAuth()
  const { silenceState, gapMinutes, pausedUntil, refreshPulse } = useSilenceState()

  const [flowState, setFlowState] = useState<FlowStateSchema | null>(null)
  const [activeSession, setActiveSession] = useState<SessionLogSchema | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  // Task form modal state
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)

  // Ref so polling callbacks always read the latest token without stale closures
  const tokenRef = useRef(token)
  useEffect(() => { tokenRef.current = token }, [token])

  const refreshTasks = async () => {
    if (!tokenRef.current) return
    try {
      setTasks(await listTasks(tokenRef.current))
    } catch (err: unknown) {
      if (err instanceof ApiError && err.isUnauthorized) logout()
    }
  }

  // After any mutation, eagerly refresh pulse + flow state so the dashboard
  // reflects the new action log entry without waiting for the next poll.
  const refreshPulseAndFlow = async () => {
    await refreshPulse()
    if (!tokenRef.current) return
    try {
      setFlowState(await getFlowState(tokenRef.current))
    } catch {
      // non-fatal
    }
  }

  useEffect(() => {
    if (!token) return

    const handleAuthError = (err: unknown) => {
      if (err instanceof ApiError && err.isUnauthorized) logout()
    }

    const fetchAll = async () => {
      // Use Promise.allSettled so a single API failure does not crash the entire load
      const [flowResult, sessionResult, tasksResult] = await Promise.allSettled([
        getFlowState(token),
        getActiveSession(token),
        listTasks(token),
      ])

      if (flowResult.status === "fulfilled") {
        setFlowState(flowResult.value)
      } else {
        handleAuthError(flowResult.reason)
        // Flow state failure is non-fatal — dashboard still usable
      }

      if (sessionResult.status === "fulfilled") {
        setActiveSession(sessionResult.value)
      } else {
        handleAuthError(sessionResult.reason)
      }

      if (tasksResult.status === "fulfilled") {
        setTasks(tasksResult.value)
      } else {
        handleAuthError(tasksResult.reason)
      }

      setLoading(false)
    }

    fetchAll()

    const sessTimer = setInterval(async () => {
      try { setActiveSession(await getActiveSession(tokenRef.current!)) }
      catch (err: unknown) { handleAuthError(err) }
    }, 30_000)

    const flowTimer = setInterval(async () => {
      try { setFlowState(await getFlowState(tokenRef.current!)) }
      catch (err: unknown) { handleAuthError(err) }
    }, 60_000)

    const taskTimer = setInterval(async () => {
      try { setTasks(await listTasks(tokenRef.current!)) }
      catch (err: unknown) { handleAuthError(err) }
    }, 60_000)

    return () => {
      clearInterval(sessTimer)
      clearInterval(flowTimer)
      clearInterval(taskTimer)
    }
  }, [token, logout])

  const handleOpenCreate = () => {
    setEditingTask(null)
    setShowTaskForm(true)
  }

  const handleEdit = (task: Task) => {
    setEditingTask(task)
    setShowTaskForm(true)
  }

  const handleDelete = async (task: Task) => {
    if (!token || !task.id) return
    try {
      await deleteTask(token, task.id)
      await refreshTasks()
      void refreshPulseAndFlow()
    } catch (err: unknown) {
      console.error("Failed to delete task:", err)
    }
  }

  const handleToggleComplete = async (task: Task) => {
    if (!token || !task.id) return
    try {
      const update: TaskUpdate = { isCompleted: !task.isCompleted }
      await updateTask(token, task.id, update)
      await refreshTasks()
      void refreshPulseAndFlow()
    } catch (err: unknown) {
      console.error("Failed to toggle task:", err)
    }
  }

  const handleFormSave = async () => {
    setShowTaskForm(false)
    setEditingTask(null)
    await refreshTasks()
    void refreshPulseAndFlow()
  }

  if (!ready || !token || loading) {
    return <LoadingSpinner />
  }

  return (
    <>
      <AppNavBar
        silenceState={silenceState ?? undefined}
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
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex flex-col items-center justify-center h-full gap-3">
              <p className="text-slate-400 text-sm">Quick Actions</p>
              <button
                onClick={handleOpenCreate}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors w-full justify-center"
              >
                <Plus size={15} />
                Create Task
              </button>
            </div>
          }
          row3={
            <TaskQueueTable
              tasks={tasks}
              activeSessionTaskId={activeSession?.taskId ?? null}
              onCreateTask={handleOpenCreate}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onToggleComplete={handleToggleComplete}
            />
          }
          zoneC={<ReasoningSidebar token={token} />}
        />
      </main>

      {showTaskForm && (
        <TaskForm
          mode={editingTask ? "edit" : "create"}
          task={editingTask ?? undefined}
          token={token}
          onClose={() => { setShowTaskForm(false); setEditingTask(null) }}
          onSave={handleFormSave}
        />
      )}
    </>
  )
}

