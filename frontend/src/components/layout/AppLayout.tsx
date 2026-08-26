import { Outlet, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import { PageLoader } from '@/components/ui/Spinner'

export default function AppLayout() {
  const { user, initialized } = useAuthStore()

  if (!initialized) return <PageLoader />
  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto grid-bg">
          <div className="max-w-[1240px] mx-auto px-6 py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
