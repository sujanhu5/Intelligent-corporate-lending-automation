import { client } from './client'
import type { ModelStatus, PredictionResponse, TrainingResponse } from '@/types'

export const predictionsApi = {
  train: () => client.post<TrainingResponse>('/predictions/train').then(r => r.data),

  modelStatus: () => client.get<ModelStatus>('/predictions/model-status').then(r => r.data),

  predict: (applicationId: string) =>
    client.post<PredictionResponse>(`/predictions/predict/${applicationId}`).then(r => r.data),

  get: (applicationId: string) =>
    client.get<PredictionResponse>(`/predictions/${applicationId}`).then(r => r.data),

  getSummary: (applicationId: string) =>
    client.get<PredictionResponse>(`/predictions/${applicationId}/summary`).then(r => r.data),
}
