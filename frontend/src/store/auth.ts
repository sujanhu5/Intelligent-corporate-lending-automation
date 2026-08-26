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
      set({ user: data.user, token: data.access_token, loading: false })
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

  initialize: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) { set({ initialized: true }); return }
    try {
      const user = await authApi.me()
      set({ user, token, initialized: true })
    } catch {
      localStorage.removeItem('access_token')
      set({ user: null, token: null, initialized: true })
    }
  },
}))
