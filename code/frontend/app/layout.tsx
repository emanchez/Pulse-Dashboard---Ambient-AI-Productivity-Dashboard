import React from 'react'
import BentoGrid from '../components/BentoGrid'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <main className="container mx-auto p-4">
          <BentoGrid>{children}</BentoGrid>
        </main>
      </body>
    </html>
  )
}
