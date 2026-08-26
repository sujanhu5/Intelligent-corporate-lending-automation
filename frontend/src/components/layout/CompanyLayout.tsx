import { Outlet, Navigate, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import ThemeToggle from '@/components/ui/ThemeToggle'
import { PageLoader } from '@/components/ui/Spinner'

const NAV_ITEMS = [
  { path: '/portal', label: 'Dashboard' },
  { path: '/portal/applications', label: 'My Applications' },
  { path: '/portal/documents', label: 'Documents' },
  { path: '/portal/company', label: 'Company Profile' },
]

export default function CompanyLayout() {
  const { user, initialized, logout } = useAuthStore()
  const location = useLocation()

  if (!initialized) return <PageLoader />
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'company') return <Navigate to="/dashboard" replace />

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      {/* Top bar */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-border-subtle flex-shrink-0 bg-canvas/80 backdrop-blur-md sticky top-0 z-30">
        <div className="flex items-center gap-6">
          <Link to="/portal" className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md gradient-orange flex items-center justify-center flex-shrink-0">
              <span className="text-white font-extrabold text-[10px] font-mono">CL</span>
            </div>
            <div className="leading-none">
              <span className="text-xs font-bold text-ink-primary font-mono">CLA</span>
              <span className="text-[9px] text-ink-muted ml-1.5 font-mono">Company Portal</span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(item => {
              const active = location.pathname === item.path || (item.path !== '/portal' && location.pathname.startsWith(item.path))
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors
                    ${active ? 'bg-cr-50 text-primary' : 'text-ink-secondary hover:text-ink-primary hover:bg-surface-2'}`}
                >
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggle variant="icon" />
          <div className="text-xs text-ink-secondary font-mono hidden sm:block">{user.full_name}</div>
          <button
            onClick={async () => { await logout(); }}
            className="text-xs text-ink-muted hover:text-red-600 font-semibold transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1100px] mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>

      <footer className="flex items-center justify-center px-6 py-3 border-t border-border-subtle text-[11px] text-ink-muted font-mono flex-shrink-0">
        &copy; 2026 Corporate Lending Automation
      </footer>
    </div>
  )
}
