"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Zap, Bell, WifiOff, CalendarOff, Brain, Menu, X } from "lucide-react"
import { useState, useEffect } from "react"

interface AppNavBarProps {
  silenceState?: "engaged" | "stagnant" | "paused"
  gapMinutes?: number
  onCreateReport?: () => void
  onManagePauses?: () => void
  onLogout?: () => void
}

export default function AppNavBar({ silenceState, gapMinutes, onCreateReport, onManagePauses, onLogout }: AppNavBarProps) {
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [pathname])

  const tabClass = (path: string) =>
    pathname === path
      ? "text-white border-b-2 border-blue-500 pb-0.5 text-sm font-medium"
      : "text-slate-400 hover:text-slate-200 text-sm font-medium"

  const mobileLinkClass = (path: string) =>
    pathname === path
      ? "text-white text-sm font-medium py-2 border-b border-slate-700"
      : "text-slate-400 hover:text-slate-200 text-sm font-medium py-2 border-b border-slate-700"

  const badge = () => {
    if (!silenceState) {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium bg-slate-700/50 text-slate-500 border border-slate-600/30">
          Checking…
        </span>
      )
    }
    if (silenceState === "stagnant") {
      const gapHours = Math.round((gapMinutes ?? 0) / 60)
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
          <WifiOff size={12} />
          STAGNANT — {gapHours}h gap
        </span>
      )
    }
    if (silenceState === "paused") {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium bg-sky-500/20 text-sky-400 border border-sky-500/30">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400 inline-block" />
          SYSTEM PAUSED
        </span>
      )
    }
    return (
      <span className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
        FOCUS MODE ACTIVE
      </span>
    )
  }

  return (
    <>
      <nav className="flex items-center justify-between px-6 h-14 bg-slate-900 border-b border-slate-800">
        {/* Left — Logo + hamburger (mobile) */}
        <div className="flex items-center">
          <Zap className="text-yellow-400" size={18} />
          <span className="text-white font-semibold ml-2 text-sm">Pulse Dashboard</span>
          {/* Hamburger — visible on mobile only */}
          <button
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="md:hidden text-slate-400 hover:text-white ml-3 p-1"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Center — Tabs (hidden on mobile) */}
        <div className="hidden md:flex items-center gap-6">
          <Link href="/tasks" className={tabClass("/tasks")}>
            Tasks
          </Link>
          <Link href="/synthesis" className={tabClass("/synthesis")}>
            <span className="flex items-center gap-1"><Brain size={14} /> Synthesis</span>
          </Link>
          <Link href="/reports" className={tabClass("/reports")}>
            Reports
          </Link>
        </div>

        {/* Right — Actions */}
        <div className="flex items-center gap-3">
          {/* Create Report — hidden on mobile */}
          {onCreateReport && (
            <button
              onClick={onCreateReport}
              className="hidden md:flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors"
            >
              + Create New Report
            </button>
          )}
          {/* Badge — hidden on mobile */}
          <span className="hidden md:flex">{badge()}</span>
          {silenceState === "paused" && onManagePauses && (
            <button
              onClick={onManagePauses}
              className="hidden md:block text-sky-400 hover:text-sky-300 transition-colors"
              aria-label="Manage system pauses"
              title="Manage system pauses"
            >
              <CalendarOff size={18} />
            </button>
          )}
          <span title="Notifications — coming soon" className="opacity-50 pointer-events-none hidden md:block">
            <Bell size={18} className="text-slate-500" />
          </span>
          <button
            onClick={onLogout}
            title="Click to logout"
            className="w-8 h-8 rounded-full bg-slate-600 hover:bg-slate-500 flex items-center justify-center text-sm text-white font-medium transition-colors"
          >
            U
          </button>
        </div>
      </nav>

      {/* Mobile drawer — visible only when mobileMenuOpen */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-900 border-b border-slate-800 px-6 py-4 space-y-1 z-40">
          <Link href="/tasks" className={mobileLinkClass("/tasks")} onClick={() => setMobileMenuOpen(false)}>
            Tasks
          </Link>
          <Link href="/synthesis" className={mobileLinkClass("/synthesis")} onClick={() => setMobileMenuOpen(false)}>
            <span className="flex items-center gap-1"><Brain size={14} /> Synthesis</span>
          </Link>
          <Link href="/reports" className={mobileLinkClass("/reports")} onClick={() => setMobileMenuOpen(false)}>
            Reports
          </Link>

          {/* Status badge */}
          <div className="pt-2">{badge()}</div>

          {/* Create Report */}
          {onCreateReport && (
            <button
              onClick={() => { onCreateReport(); setMobileMenuOpen(false) }}
              className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-3 py-2 rounded-md transition-colors w-full justify-center"
            >
              + Create New Report
            </button>
          )}

          {/* Manage pauses */}
          {silenceState === "paused" && onManagePauses && (
            <button
              onClick={() => { onManagePauses(); setMobileMenuOpen(false) }}
              className="flex items-center gap-1.5 text-sky-400 hover:text-sky-300 text-sm transition-colors"
            >
              <CalendarOff size={16} />
              Manage Pauses
            </button>
          )}
        </div>
      )}
    </>
  )
}

