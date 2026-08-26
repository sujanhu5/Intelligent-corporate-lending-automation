import { client } from './client'
import type { Rule, RuleCreate, RuleEngineResponse } from '@/types'

export const rulesApi = {
  list: (params?: { category?: string; is_mandatory?: boolean; is_active?: boolean }) =>
    client.get<{ items: Rule[]; total: number }>('/rules', { params }).then(r => r.data),

  get: (id: string) => client.get<Rule>(`/rules/${id}`).then(r => r.data),

  create: (data: RuleCreate) => client.post<Rule>('/rules', data).then(r => r.data),

  update: (id: string, data: Partial<RuleCreate>) =>
    client.put<Rule>(`/rules/${id}`, data).then(r => r.data),

  toggle: (id: string) =>
    client.patch<Rule>(`/rules/${id}/toggle`).then(r => r.data),

  delete: (id: string) => client.delete(`/rules/${id}`).then(r => r.data),

  evaluate: (applicationId: string) =>
    client.post<RuleEngineResponse>(`/rules/evaluate/${applicationId}`).then(r => r.data),

  getEvaluation: (applicationId: string) =>
    client.get<RuleEngineResponse>(`/rules/evaluation/${applicationId}`).then(r => r.data),
}
