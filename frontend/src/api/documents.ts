import { client } from './client'
import type { Document } from '@/types'

export const documentsApi = {
  listForApplication: (applicationId: string) =>
    client.get<{ items: Document[]; total: number }>(`/documents/application/${applicationId}`).then(r => r.data),

  upload: (applicationId: string, file: File, documentType: string, financialYear?: number) => {
    const form = new FormData()
    form.append('file', file)
    form.append('document_type', documentType)
    if (financialYear) form.append('financial_year', String(financialYear))
    return client.post<Document>(`/documents/upload/${applicationId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  download: (documentId: string) =>
    client.get(`/documents/${documentId}/download`, { responseType: 'blob' }).then(r => r.data),

  delete: (documentId: string) =>
    client.delete(`/documents/${documentId}`).then(r => r.data),

  verifyChecksum: (documentId: string) =>
    client.get<{ valid: boolean; stored: string; actual: string }>(`/documents/${documentId}/verify-checksum`).then(r => r.data),
}
