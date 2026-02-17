import React from 'react'

export default function BentoGrid({ children }: { children?: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="md:col-span-2 bg-white p-4 rounded shadow">{children}</div>
      <div className="md:col-span-1 bg-white p-4 rounded shadow">Side</div>
      <div className="md:col-span-1 bg-white p-4 rounded shadow">Side 2</div>
    </div>
  )
}
