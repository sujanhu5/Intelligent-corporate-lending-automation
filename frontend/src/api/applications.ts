import { client } from './client'
import type { Application, ApplicationCreate, DashboardStats, FinalDecision, PaginatedResponse } from '@/types'

export const applicationsApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; company_id?: string }) =>
    client.get<PaginatedResponse<Application>>('/applications', { params }).then(r => r.data),

  get: (id: string) => client.get<Application>(`/applications/${id}`).then(r => r.data),

  create: (data: ApplicationCreate) =>
    client.post<Application>('/applications', data).then(r => r.data),

  update: (id: string, data: Partial<ApplicationCreate>) =>
    client.put<Application>(`/applications/${id}`, data).then(r => r.data),

  submit: (id: string) =>
    client.post<Application>(`/applications/${id}/submit`).then(r => r.data),

  decision: (id: string, data: { decision: FinalDecision; decision_reason: string; officer_notes?: string }) =>
    client.patch<Application>(`/applications/${id}/decision`, data).then(r => r.data),

  withdraw: (id: string) =>
    client.post<Application>(`/applications/${id}/withdraw`).then(r => r.data),

  assign: (id: string, officer_id: string) =>
    client.post<Application>(`/applications/${id}/assign`, { officer_id }).then(r => r.data),

  dashboardStats: () =>
    client.get<DashboardStats>('/applications/stats/dashboard').then(r => r.data),
}
