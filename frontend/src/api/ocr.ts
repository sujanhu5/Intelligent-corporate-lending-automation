import { client } from './client'
import type { ApplicationOCRSummary, OCRResult } from '@/types'

export const ocrApi = {
  process: (documentId: string) =>
    client.post<OCRResult>(`/ocr/extract/${documentId}`).then(r => r.data),

  processAll: (applicationId: string) =>
    client.post<OCRResult[]>(`/ocr/extract-all/${applicationId}`).then(r => r.data),

  getForApplication: (applicationId: string) =>
    client.get<ApplicationOCRSummary>(`/ocr/application/${applicationId}`).then(r => r.data),

  getForDocument: (documentId: string) =>
    client.get<OCRResult>(`/ocr/result/${documentId}`).then(r => r.data),
}
