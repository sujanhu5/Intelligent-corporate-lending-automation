import { client } from './client'
import type { TokenResponse, User } from '@/types'

export const authApi = {
  login: (email: string, password: string) =>
    client.post<TokenResponse>('/auth/login', { email, password }).then(r => r.data),

  me: () => client.get<User>('/auth/me').then(r => r.data),

  logout: () => client.post('/auth/logout').then(r => r.data),

  changePassword: (current_password: string, new_password: string, confirm_password: string) =>
    client.post('/auth/change-password', { current_password, new_password, confirm_password }).then(r => r.data),
}
