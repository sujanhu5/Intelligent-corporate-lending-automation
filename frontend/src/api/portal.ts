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
}
