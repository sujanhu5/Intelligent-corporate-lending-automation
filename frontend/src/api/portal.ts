import { client } from './client'

export const portalApi = {
  dashboard: () =>
    client.get('/portal/dashboard').then(r => r.data),

  company: () =>
    client.get('/portal/company').then(r => r.data),

  applications: (page = 1, pageSize = 20) =>
    client.get('/portal/applications', { params: { page, page_size: pageSize } }).then(r => r.data),

  applicationDetail: (id: string) =>
    client.get(`/portal/applications/${id}`).then(r => r.data),

  documents: () =>
    client.get('/portal/documents').then(r => r.data),

  createApplication: (loanAmount = 1000000, loanPurpose = 'working_capital', tenureMonths = 12) =>
    client.post('/portal/applications', null, {
      params: { loan_amount: loanAmount, loan_purpose: loanPurpose, loan_tenure_months: tenureMonths },
    }).then(r => r.data),

  uploadDocument: (applicationId: string, file: File, documentType: string, financialYear?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('document_type', documentType)
    if (financialYear) form.append('financial_year', financialYear)
    return client.post(`/portal/documents/upload/${applicationId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  uploadAnnualReport: (applicationId: string, file: File, financialYear?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (financialYear) form.append('financial_year', financialYear)
    return client.post(`/portal/annual-report/upload/${applicationId}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    }).then(r => r.data)
  },

  analyzeAnnualReport: (documentId: string) =>
    client.post(`/portal/annual-report/analyze/${documentId}`, null, {
      timeout: 600000,
    }).then(r => r.data),

  annualReportStatus: (documentId: string) =>
    client.get(`/portal/annual-report/status/${documentId}`).then(r => r.data),
}
