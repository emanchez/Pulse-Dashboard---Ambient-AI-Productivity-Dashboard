import React from 'react'
import './globals.css'
import SilenceStateProvider from '../components/SilenceStateProvider'

export const metadata = {
  title: 'Pulse Dashboard',
  description: 'Ambient AI Productivity Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Unregister any stale service workers (e.g. from earlier next-pwa experiments).
            Runs before the page hydrates so orphaned SWs cannot intercept API fetches. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                navigator.serviceWorker.getRegistrations().then(function(registrations) {
                  registrations.forEach(function(r) { r.unregister(); });
                });
              }
            `,
          }}
        />
      </head>
      <body className="min-h-screen bg-slate-950 text-white">
        <SilenceStateProvider>
          {children}
        </SilenceStateProvider>
      </body>
    </html>
  )
}
