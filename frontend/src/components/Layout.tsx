import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { ChatDrawer } from '@/features/assistant'

export function Layout() {
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-gray-50 p-6">
        <Outlet />
      </main>

      {/* Chat toggle button — bottom right */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-30 flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition-transform hover:scale-105 hover:bg-blue-700"
          data-testid="chat-toggle"
        >
          <MessageSquare className="h-5 w-5" />
        </button>
      )}

      <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
