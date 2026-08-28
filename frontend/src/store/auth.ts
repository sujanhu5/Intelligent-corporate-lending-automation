import { create } from 'zustand'
import type { User } from '@/types'
import { authApi } from '@/api/auth'

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  initialized: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  initialize: () => Promise<void>
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  loading: false,
  initialized: false,

  login: async (email, password) => {
    set({ loading: true })
    try {
      const data = await authApi.login(email, password)
      localStorage.setItem('access_token', data.access_token)
      // initialized: true guards against a slower, stale initialize() call
      // (kicked off on app mount with a leftover token) resolving afterwards
      // and clobbering this fresh login — see the token-freshness check below.
      set({ user: data.user, token: data.access_token, loading: false, initialized: true })
    } catch (err) {
      set({ loading: false })
      throw err
    }
  },

  logout: async () => {
    try { await authApi.logout() } catch { /* ignore */ }
    localStorage.removeItem('access_token')
    set({ user: null, token: null })
  },

  setUser: (user) => set({ user }),

  initialize: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) { set({ initialized: true }); return }
    try {
      const user = await authApi.me()
      // Only apply the result if this is still the active token — a newer
      // login() may have replaced it while this request was in flight.
      if (localStorage.getItem('access_token') === token) {
        set({ user, token, initialized: true })
      }
    } catch {
      // Same guard: don't log out a session that has since logged in fresh.
      if (localStorage.getItem('access_token') === token) {
        localStorage.removeItem('access_token')
        set({ user: null, token: null, initialized: true })
      }
    }
  },
}))
