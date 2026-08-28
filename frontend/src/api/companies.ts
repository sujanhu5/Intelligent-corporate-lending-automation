import { client } from './client'
import type { Company, CompanyCreate, CompanyStatus, PaginatedResponse } from '@/types'

export const companiesApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; status?: CompanyStatus }) =>
    client.get<PaginatedResponse<Company>>('/companies', { params }).then(r => r.data),

  get: (id: string) => client.get<Company>(`/companies/${id}`).then(r => r.data),

  create: (data: CompanyCreate) =>
    client.post<Company>('/companies', data).then(r => r.data),

  update: (id: string, data: Partial<CompanyCreate>) =>
    client.put<Company>(`/companies/${id}`, data).then(r => r.data),

  deactivate: (id: string) =>
    client.delete<Company>(`/companies/${id}`).then(r => r.data),

  permanentDelete: (id: string) =>
    client.delete(`/companies/${id}/permanent`).then(r => r.data),
}
