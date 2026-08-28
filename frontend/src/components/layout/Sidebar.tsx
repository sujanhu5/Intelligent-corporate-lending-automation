import { NavLink } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import type { UserRole } from '@/types'

interface NavItem {
  href: string
  label: string
  icon: string
  roles?: UserRole[]
}

const NAV: NavItem[] = [
  { href: '/dashboard',    label: 'Dashboard',    icon: '◧' },
  { href: '/applications', label: 'Applications', icon: '▦' },
  { href: '/companies',    label: 'Companies',    icon: '⬢' },
  { href: '/rules',        label: 'Rule Engine',  icon: '⚙', roles: ['admin'] },
  { href: '/predictions',  label: 'ML Models',    icon: '◈', roles: ['admin'] },
  { href: '/analytics',    label: 'Analytics',    icon: '▤', roles: ['admin', 'analyst'] },
  { href: '/pipeline',     label: 'Pipeline',     icon: '⟐', roles: ['admin', 'officer', 'analyst'] },
  { href: '/settings',     label: 'Settings',     icon: '⛭', roles: ['admin'] },
]

export default function Sidebar() {
  const { user } = useAuthStore()

  const visibleItems = NAV.filter(item =>
    !item.roles || (user && item.roles.includes(user.role))
  )

  return (
    <aside className="w-[232px] flex-shrink-0 h-screen sticky top-0 flex flex-col
                      bg-surface-1 border-r border-border-subtle overflow-y-auto">
      {/* Logo */}
      <div className="px-5 py-5 flex items-center gap-3 border-b border-border-subtle">
        <div className="w-9 h-9 rounded-lg gradient-orange flex items-center justify-center shadow-orange flex-shrink-0">
          <span className="text-white font-extrabold text-sm font-mono tracking-tighter">CL</span>
        </div>
        <div className="min-w-0">
          <div className="text-sm font-extrabold tracking-tight text-ink-primary font-mono leading-none">CLA</div>
          <div className="text-[9px] text-ink-muted mt-1 uppercase tracking-[0.1em] font-mono truncate">Lending OS</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 flex flex-col gap-1">
        {visibleItems.map(item => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              `group flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-semibold font-mono transition-all duration-150
               ${isActive
                 ? 'gradient-orange text-white shadow-orange'
                 : 'text-ink-secondary hover:text-ink-primary hover:bg-surface-2'}`
            }
          >
            {({ isActive }) => (
              <>
                <span className={`text-base leading-none ${isActive ? 'text-white' : 'text-ink-muted group-hover:text-primary'}`}>
                  {item.icon}
                </span>
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      {user && (
        <div className="border-t border-border-subtle px-4 py-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-cr-50 border border-border-subtle flex items-center justify-center flex-shrink-0">
            <span className="text-primary font-bold text-xs font-mono">
              {user.full_name?.charAt(0)?.toUpperCase() ?? 'U'}
            </span>
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-ink-primary truncate font-mono">{user.full_name}</div>
            <div className="text-[9px] text-ink-muted mt-0.5 uppercase tracking-[0.1em] font-mono">{user.role}</div>
          </div>
        </div>
      )}
    </aside>
  )
}
