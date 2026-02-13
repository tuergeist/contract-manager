import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { HelpVideoButton } from './HelpVideoButton'

export function Layout() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-gray-50 p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <Outlet />
          </div>
          <div className="ml-4 flex-shrink-0 sticky top-0">
            <HelpVideoButton />
          </div>
        </div>
      </main>
    </div>
  )
}
