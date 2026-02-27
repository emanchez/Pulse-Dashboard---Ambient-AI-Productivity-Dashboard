import React from 'react'
import './globals.css'
import AppNavBar from '../components/nav/AppNavBar'

export const metadata = {
  title: 'Pulse Dashboard',
  description: 'Ambient AI Productivity Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-white">
        <AppNavBar />
        <main className="px-6 py-6">
          {children}
        </main>
      </body>
    </html>
  )
}
