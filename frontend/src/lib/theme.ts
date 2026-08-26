import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'cla-theme'

/** Resolve the theme that should be active right now. */
export function resolveTheme(): Theme {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/** Stamp the theme onto <html> so the CSS variables switch. */
export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme)
}

/** Persist + apply a theme choice. */
export function setTheme(theme: Theme): void {
  localStorage.setItem(STORAGE_KEY, theme)
  applyTheme(theme)
  window.dispatchEvent(new CustomEvent('cla-theme-change', { detail: theme }))
}

/** Call once at boot (before/at first render) to prevent a flash of the wrong theme. */
export function initTheme(): void {
  applyTheme(resolveTheme())
}

/** React hook: current theme + a toggle, kept in sync across the app. */
export function useTheme(): { theme: Theme; toggle: () => void; setTheme: (t: Theme) => void } {
  const [theme, setThemeState] = useState<Theme>(() =>
    (document.documentElement.getAttribute('data-theme') as Theme) || resolveTheme()
  )

  useEffect(() => {
    const onChange = (e: Event) => {
      const t = (e as CustomEvent).detail as Theme
      setThemeState(t)
    }
    window.addEventListener('cla-theme-change', onChange)
    return () => window.removeEventListener('cla-theme-change', onChange)
  }, [])

  return {
    theme,
    toggle: () => setTheme(theme === 'dark' ? 'light' : 'dark'),
    setTheme,
  }
}
