// quick-access card used on dashboard
import React from "react"

interface QuickAccessCardProps {
  icon: React.ElementType
  title: string
  subtitle: string
  iconBg?: string
}

export default function QuickAccessCard({
  icon: Icon,
  title,
  subtitle,
  iconBg = "bg-blue-900/40",
}: QuickAccessCardProps) {
  return (
    <div className="bg-slate-800 rounded-xl p-5 flex flex-col gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${iconBg}`}>
        <Icon className="text-blue-400" size={20} />
      </div>
      <h3 className="text-white font-medium text-sm">{title}</h3>
      <p className="text-slate-400 text-xs">{subtitle}</p>
    </div>
  )
}
