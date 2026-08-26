import { client } from './client'
import type {
  AnalyticsSummary,
  ApplicationTrend,
  RiskDistribution,
  IndustryBreakdown,
  LoanPurposeBreakdown,
  PipelineFunnelStage,
  RuleTriggerStat,
  PipelineMetrics,
} from '@/types'

export const analyticsApi = {
  summary: () =>
    client.get<AnalyticsSummary>('/analytics/summary').then(r => r.data),

  trends: (days = 30) =>
    client.get<ApplicationTrend[]>('/analytics/trends', { params: { days } }).then(r => r.data),

  riskDistribution: () =>
    client.get<RiskDistribution[]>('/analytics/risk-distribution').then(r => r.data),

  industryBreakdown: () =>
    client.get<IndustryBreakdown[]>('/analytics/industry-breakdown').then(r => r.data),

  loanPurposeBreakdown: () =>
    client.get<LoanPurposeBreakdown[]>('/analytics/loan-purpose-breakdown').then(r => r.data),

  pipelineFunnel: () =>
    client.get<PipelineFunnelStage[]>('/analytics/pipeline-funnel').then(r => r.data),

  ruleTriggers: (limit = 20) =>
    client.get<RuleTriggerStat[]>('/analytics/rule-triggers', { params: { limit } }).then(r => r.data),

  pipelineMetrics: () =>
    client.get<PipelineMetrics>('/analytics/pipeline-metrics').then(r => r.data),
}
