import React from 'react'
import './globals.css'

export const metadata = {
  title: 'Pulse Dashboard',
  description: 'Ambient AI Productivity Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <main className="container mx-auto p-4">
          {children}
        </main>
      </body>
    </html>
  )
}
