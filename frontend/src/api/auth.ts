import { client } from './client'
import type { TokenResponse, User } from '@/types'

export interface CompanyRegisterPayload {
  company_name: string
  registration_number: string
  company_type: string
  industry: string
  incorporation_date?: string
  registered_address: string
  city?: string
  state?: string
  postal_code?: string
  contact_phone?: string
  website?: string
  annual_turnover?: number
  number_of_employees?: number
  full_name: string
  email: string
  password: string
}

export const authApi = {
  login: (email: string, password: string) =>
    client.post<TokenResponse>('/auth/login', { email, password }).then(r => r.data),

  register: (data: CompanyRegisterPayload) =>
    client.post<TokenResponse>('/auth/register', data).then(r => r.data),

  me: () => client.get<User>('/auth/me').then(r => r.data),

  logout: () => client.post('/auth/logout').then(r => r.data),

  changePassword: (current_password: string, new_password: string, confirm_password: string) =>
    client.post('/auth/change-password', { current_password, new_password, confirm_password }).then(r => r.data),
}
