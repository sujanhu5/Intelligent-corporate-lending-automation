import { client } from './client'
import type { Report } from '@/types'

export const reportsApi = {
  generate: (applicationId: string) =>
    client.post<Report>(`/reports/generate/${applicationId}`).then(r => r.data),

  getLatest: (applicationId: string) =>
    client.get<Report>(`/reports/${applicationId}`).then(r => r.data),

  list: (applicationId: string) =>
    client.get<{ items: Report[]; total: number }>(`/reports/${applicationId}/list`).then(r => r.data),

  downloadUrl: (reportId: string) => `/api/v1/reports/${reportId}/download`,
}
