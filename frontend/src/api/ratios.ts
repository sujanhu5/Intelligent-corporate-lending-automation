import { client } from './client'
import type { FinancialRatioResponse, RatioSummary } from '@/types'

export const ratiosApi = {
  calculate: (applicationId: string) =>
    client.post<FinancialRatioResponse>(`/ratios/calculate/${applicationId}`).then(r => r.data),

  getForApplication: (applicationId: string) =>
    client.get<FinancialRatioResponse>(`/ratios/application/${applicationId}`).then(r => r.data),

  getSummary: (applicationId: string) =>
    client.get<RatioSummary>(`/ratios/application/${applicationId}/summary`).then(r => r.data),
}
