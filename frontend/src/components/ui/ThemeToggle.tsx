import { useTheme } from '@/lib/theme'

interface ThemeToggleProps {
  /** 'switch' = sliding pill (default), 'icon' = single icon button */
  variant?: 'switch' | 'icon'
  className?: string
}

export default function ThemeToggle({ variant = 'switch', className = '' }: ThemeToggleProps) {
  const { theme, toggle } = useTheme()
  const isDark = theme === 'dark'

  if (variant === 'icon') {
    return (
      <button
        onClick={toggle}
        className={`text-ink-muted hover:text-primary transition-colors p-2 rounded-lg hover:bg-surface-2 ${className}`}
        title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
        aria-label="Toggle colour theme"
      >
        {isDark ? <SunIcon /> : <MoonIcon />}
      </button>
    )
  }

  return (
    <button
      onClick={toggle}
      role="switch"
      aria-checked={isDark}
      aria-label="Toggle colour theme"
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      className={`relative inline-flex items-center h-8 w-[60px] rounded-full border border-border-subtle
                  bg-surface-2 transition-colors ${className}`}
    >
      {/* track icons */}
      <span className="absolute left-2 text-[11px] text-ink-muted"><SunIcon small /></span>
      <span className="absolute right-2 text-[11px] text-ink-muted"><MoonIcon small /></span>
      {/* knob */}
      <span
        className={`z-10 inline-flex items-center justify-center w-6 h-6 rounded-full gradient-orange text-white shadow-orange
                    transform transition-transform duration-200 ${isDark ? 'translate-x-[31px]' : 'translate-x-[3px]'}`}
      >
        {isDark ? <MoonIcon small /> : <SunIcon small />}
      </span>
    </button>
  )
}

function SunIcon({ small }: { small?: boolean }) {
  const s = small ? 'w-3.5 h-3.5' : 'w-4 h-4'
  return (
    <svg className={s} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

function MoonIcon({ small }: { small?: boolean }) {
  const s = small ? 'w-3.5 h-3.5' : 'w-4 h-4'
  return (
    <svg className={s} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  )
}
