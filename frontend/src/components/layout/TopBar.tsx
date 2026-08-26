import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { useToast } from '@/components/ui/Toast'
import ThemeToggle from '@/components/ui/ThemeToggle'

export default function TopBar() {
  const { user, logout } = useAuthStore()
  const { success } = useToast()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    success('Signed out successfully.')
    navigate('/login')
  }

  return (
    <header className="h-14 flex items-center justify-between gap-3 px-6 border-b border-border-subtle bg-surface-1/80 backdrop-blur-sm flex-shrink-0 sticky top-0 z-20">
      {/* Left — live status pill */}
      <div className="flex items-center gap-2 text-[11px] font-mono font-semibold text-ink-secondary uppercase tracking-wider">
        <span className="w-2 h-2 rounded-full bg-up animate-pulse" />
        System Online
      </div>

      {/* Right */}
      <div className="flex items-center gap-3">
        <ThemeToggle variant="switch" />

        {user && (
          <div className="flex items-center gap-3 pl-3 border-l border-border-subtle">
            <span className="text-xs text-ink-secondary hidden sm:inline font-mono">{user.email}</span>
            <button
              onClick={handleLogout}
              className="text-xs font-bold font-mono text-ink-secondary hover:text-primary transition-colors uppercase tracking-wide"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
