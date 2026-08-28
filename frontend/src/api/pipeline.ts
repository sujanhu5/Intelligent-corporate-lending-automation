import { client } from './client'
import type {
  PipelineStatusResponse,
  PipelineRunResponse,
  BatchPipelineResponse,
} from '@/types'

export const pipelineApi = {
  status: (applicationId: string) =>
    client.get<PipelineStatusResponse>(`/pipeline/status/${applicationId}`).then(r => r.data),

  run: (applicationId: string, generateReport = true) =>
    client.post<PipelineRunResponse>(`/pipeline/run/${applicationId}`, null, {
      params: { generate_report: generateReport },
    }).then(r => r.data),

  runBatch: (body: { application_ids?: string[]; limit?: number; generate_report?: boolean }) =>
    client.post<BatchPipelineResponse>('/pipeline/run-batch', body).then(r => r.data),

  resetStage: (applicationId: string, stage: string) =>
    client.post(`/pipeline/reset-stage/${applicationId}`, null, {
      params: { stage },
    }).then(r => r.data),
}
