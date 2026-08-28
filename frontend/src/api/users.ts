import { client } from './client'
import type { PaginatedResponse, User, UserRole, UserStatus } from '@/types'

export interface UserCreate {
  email: string
  full_name: string
  password: string
  role: UserRole
}

export const usersApi = {
  list: (params?: { page?: number; page_size?: number; role?: UserRole; status?: UserStatus }) =>
    client.get<PaginatedResponse<User>>('/users', { params }).then(r => r.data),

  get: (id: string) => client.get<User>(`/users/${id}`).then(r => r.data),

  create: (data: UserCreate) => client.post<User>('/users', data).then(r => r.data),

  update: (id: string, data: Partial<{ full_name: string; role: UserRole }>) =>
    client.put<User>(`/users/${id}`, data).then(r => r.data),

  setStatus: (id: string, status: UserStatus, reason?: string) =>
    client.patch<User>(`/users/${id}/status`, { status, reason }).then(r => r.data),

  adminResetPassword: (id: string, new_password: string) =>
    client.post(`/users/${id}/reset-password`, { new_password }).then(r => r.data),

  updateMe: (data: Partial<{ email: string; full_name: string; department: string; phone: string }>) =>
    client.patch<User>('/users/me', data).then(r => r.data),
}
