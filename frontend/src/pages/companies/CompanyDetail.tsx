import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { companiesApi } from '@/api/companies'
import { applicationsApi } from '@/api/applications'
import type { Company, Application } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import { ApplicationStatusBadge } from '@/components/ui/Badge'
import { PageLoader } from '@/components/ui/Spinner'
import Button from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'
import { useAuthStore } from '@/store/auth'

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-4 py-3 border-b border-border-subtle last:border-0">
      <span className="text-[11px] font-bold uppercase tracking-wider text-ink-muted font-mono w-44 flex-shrink-0 pt-0.5">{label}</span>
      <span className="text-small text-ink-primary font-medium">{value ?? '—'}</span>
    </div>
  )
}

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>()
  const [company, setCompany] = useState<Company | null>(null)
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmName, setConfirmName] = useState('')
  const navigate = useNavigate()
  const { error, success } = useToast()
  const user = useAuthStore(s => s.user)
  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    if (!id) return
    Promise.all([
      companiesApi.get(id),
      applicationsApi.list({ company_id: id, page_size: 50 }),
    ]).then(([c, a]) => { setCompany(c); setApplications(a.items) })
      .catch(err => error(extractError(err)))
      .finally(() => setLoading(false))
  }, [id, error])

  const handleDelete = async () => {
    if (!id || confirmName !== company?.name) return
    setDeleting(true)
    try {
      const res = await companiesApi.permanentDelete(id)
      success(res.message || 'Company permanently deleted.')
      navigate('/companies')
    } catch (err) {
      error(extractError(err))
    } finally {
      setDeleting(false)
      setShowDeleteModal(false)
      setConfirmName('')
    }
  }

  if (loading) return <PageLoader />
  if (!company) return <div className="text-ink-muted">Company not found.</div>

  return (
    <div>
      <PageHeader
        title={company.name}
        subtitle={company.registration_number}
        breadcrumb={[{ label: 'Companies', href: '/companies' }, { label: company.name }]}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => navigate('/applications/new', { state: { company_id: company.id } })}>
              + New Application
            </Button>
            {isAdmin && (
              <Button
                variant="danger"
                onClick={() => setShowDeleteModal(true)}
              >
                Delete Company
              </Button>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Profile */}
        <div className="card p-5">
          <h3 className="text-h4 text-ink-primary mb-1 font-mono">Company Profile</h3>
          <div className="mt-3">
            <Row label="Registration No." value={company.registration_number} />
            <Row label="Tax ID" value={company.tax_id} />
            <Row label="GST Number" value={company.gst_number} />
            <Row label="Company Type" value={company.company_type?.replace(/_/g, ' ')} />
            <Row label="Industry" value={company.industry?.replace(/_/g, ' ')} />
            <Row label="Incorporation Date" value={company.incorporation_date} />
            <Row label="Country" value={company.country_of_incorporation} />
          </div>
        </div>

        {/* Contact & Financial */}
        <div className="card p-5">
          <h3 className="text-h4 text-ink-primary mb-1 font-mono">Contact & Financials</h3>
          <div className="mt-3">
            <Row label="Registered Address" value={company.registered_address} />
            <Row label="City / State" value={[company.city, company.state].filter(Boolean).join(', ')} />
            <Row label="Email" value={company.contact_email} />
            <Row label="Phone" value={company.contact_phone} />
            <Row label="Annual Turnover"
              value={company.annual_turnover ? `₹${company.annual_turnover.toLocaleString()}` : null} />
            <Row label="Employees" value={company.number_of_employees?.toLocaleString()} />
          </div>
        </div>
      </div>

      {/* Applications */}
      <div className="mt-6">
        <h3 className="text-h4 text-ink-primary mb-4 font-mono">Loan Applications</h3>
        {applications.length === 0 ? (
          <div className="card flex items-center justify-center py-12 text-ink-muted text-small">
            No applications yet for this company.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-md border border-border-subtle shadow-xs">
            <table className="w-full border-collapse text-small">
              <thead className="bg-surface-2">
                <tr>
                  {['Application No.', 'Amount (₹)', 'Purpose', 'Tenure', 'Risk Score', 'Status'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-surface-1 divide-y divide-border-subtle">
                {applications.map(app => (
                  <tr
                    key={app.id}
                    className="cursor-pointer hover:bg-surface-2 transition-colors"
                    onClick={() => navigate(`/applications/${app.id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-ink-secondary">{app.application_number}</td>
                    <td className="px-4 py-3 tabular text-right">
                      {app.loan_amount_requested.toLocaleString()}
                    </td>
                    <td className="px-4 py-3">{app.loan_purpose.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3 tabular">{app.loan_tenure_months}mo</td>
                    <td className="px-4 py-3 tabular text-right">
                      {app.risk_score != null ? app.risk_score.toFixed(1) : '—'}
                    </td>
                    <td className="px-4 py-3"><ApplicationStatusBadge status={app.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-surface-1 rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h3 className="text-h4 text-ink-primary mb-2 font-mono">Permanently Delete Company</h3>
            <p className="text-small text-ink-secondary mb-4">
              This will permanently delete <strong>{company.name}</strong> along with all applications,
              documents, and associated data. Company users will be deactivated. This action cannot be undone.
            </p>
            <label className="text-caption text-ink-muted block mb-1">
              Type the company name to confirm:
            </label>
            <input
              type="text"
              value={confirmName}
              onChange={e => setConfirmName(e.target.value)}
              placeholder={company.name}
              className="w-full px-3 py-2 rounded border border-border bg-surface-2 text-ink-primary text-small mb-4 focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => { setShowDeleteModal(false); setConfirmName('') }}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={confirmName !== company.name || deleting}
              >
                {deleting ? 'Deleting...' : 'Delete Permanently'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
