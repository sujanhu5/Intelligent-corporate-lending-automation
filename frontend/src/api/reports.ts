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

  delete: (reportId: string) =>
    client.delete<{ message: string; success: boolean }>(`/reports/${reportId}`).then(r => r.data),

  download: async (reportId: string, filename?: string) => {
    const res = await client.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `credit_report_${reportId}.pdf`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
}
