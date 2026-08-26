import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { portalApi } from '@/api/portal'
import { PageLoader } from '@/components/ui/Spinner'

interface DashboardData {
  company_name: string
  company_status: string
  total_applications: number
  approved: number
  rejected: number
  manual_review: number
  pending: number
  in_pipeline: number
  recent_applications: {
    id: string
    application_number: string
    status: string
    final_decision: string
    loan_amount: number
    created_at: string
  }[]
}

const STATUS_COLORS: Record<string, string> = {
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  manual_review: 'bg-amber-100 text-amber-800',
  pending: 'bg-gray-100 text-gray-700',
  submitted: 'bg-blue-100 text-blue-800',
  draft: 'bg-gray-100 text-gray-600',
}

const COMPANY_STATUS: Record<string, { bg: string; label: string }> = {
  active: { bg: 'bg-green-100 text-green-800', label: 'Active' },
  under_review: { bg: 'bg-amber-100 text-amber-800', label: 'Under Review' },
  inactive: { bg: 'bg-gray-100 text-gray-700', label: 'Inactive' },
  blacklisted: { bg: 'bg-red-100 text-red-800', label: 'Blacklisted' },
}

export default function PortalDashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    portalApi.dashboard()
      .then(setData)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <PageLoader />

  const companyStatus = COMPANY_STATUS[data?.company_status ?? ''] ?? COMPANY_STATUS.inactive

  return (
    <div>
      {/* Company header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary font-mono mb-2">Company Portal</div>
          <h1 className="text-h2 text-ink-primary">{data?.company_name ?? 'Company'}</h1>
          <div className="flex items-center gap-3 mt-2">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide ${companyStatus.bg}`}>
              {companyStatus.label}
            </span>
            {data?.company_status === 'active' && (
              <span className="text-xs text-ink-secondary">Your company is verified and eligible to apply for loans</span>
            )}
            {data?.company_status === 'under_review' && (
              <span className="text-xs text-amber-600">Your registration is being reviewed by our team</span>
            )}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        <StatCard label="Total Applications" value={data?.total_applications ?? 0} />
        <StatCard label="Approved" value={data?.approved ?? 0} color="text-green-600" />
        <StatCard label="Under Review" value={(data?.in_pipeline ?? 0) + (data?.manual_review ?? 0)} color="text-amber-600" />
        <StatCard label="Pending Decision" value={data?.pending ?? 0} color="text-ink-secondary" />
        <StatCard label="Rejected" value={data?.rejected ?? 0} color="text-red-600" />
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        <button
          onClick={() => navigate('/portal/applications')}
          className="card card-hover p-5 text-left group"
        >
          <div className="w-9 h-9 rounded-lg gradient-orange flex items-center justify-center mb-3 shadow-orange">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="text-sm font-bold text-ink-primary">My Applications</div>
          <div className="text-xs text-ink-secondary mt-1">Track status and view details of all your loan applications</div>
        </button>

        <button
          onClick={() => navigate('/portal/documents')}
          className="card card-hover p-5 text-left group"
        >
          <div className="w-9 h-9 rounded-lg bg-[var(--cr-700)] flex items-center justify-center mb-3">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <div className="text-sm font-bold text-ink-primary">Upload Documents</div>
          <div className="text-xs text-ink-secondary mt-1">Upload financial statements, balance sheets, and supporting PDFs</div>
        </button>

        <button
          onClick={() => navigate('/portal/company')}
          className="card card-hover p-5 text-left group"
        >
          <div className="w-9 h-9 rounded-lg bg-[var(--cr-800)] flex items-center justify-center mb-3">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <div className="text-sm font-bold text-ink-primary">Company Profile</div>
          <div className="text-xs text-ink-secondary mt-1">View your company registration details and financial summary</div>
        </button>

        <div className="card p-5 text-left">
          <div className="w-9 h-9 rounded-lg bg-[var(--cr-900)] flex items-center justify-center mb-3">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
          <div className="text-sm font-bold text-ink-primary">Need Help?</div>
          <div className="text-xs text-ink-secondary mt-1">Contact your assigned loan officer or reach out to support</div>
        </div>
      </div>

      {/* How it works — for companies with no applications yet */}
      {(data?.total_applications ?? 0) === 0 && (
        <div className="card p-6 mb-8 border-2 border-dashed border-border-default">
          <h2 className="text-sm font-bold text-ink-primary font-mono mb-4">How the Loan Process Works</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { step: '1', title: 'Upload Documents', desc: 'Submit your balance sheets, P&L statements, and cash flow reports as PDF files.' },
              { step: '2', title: 'Automated Analysis', desc: 'Our system extracts financial data via OCR and computes key ratios automatically.' },
              { step: '3', title: 'Credit Assessment', desc: 'Applications are evaluated against banking rules and ML-based risk models.' },
              { step: '4', title: 'Decision', desc: 'You receive an approval, rejection, or manual review notification with a detailed report.' },
            ].map(item => (
              <div key={item.step} className="flex gap-3">
                <div className="w-7 h-7 rounded-full gradient-orange flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-0.5">
                  {item.step}
                </div>
                <div>
                  <div className="text-xs font-bold text-ink-primary">{item.title}</div>
                  <div className="text-[11px] text-ink-secondary mt-0.5 leading-relaxed">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent applications */}
      <div className="card">
        <div className="p-5 border-b border-border-subtle flex items-center justify-between">
          <h2 className="text-sm font-bold text-ink-primary font-mono">Recent Applications</h2>
          {(data?.total_applications ?? 0) > 0 && (
            <button
              onClick={() => navigate('/portal/applications')}
              className="text-[11px] font-bold text-primary hover:underline"
            >
              View all
            </button>
          )}
        </div>
        {data?.recent_applications && data.recent_applications.length > 0 ? (
          <div className="divide-y divide-border-subtle">
            {data.recent_applications.map(app => (
              <div
                key={app.id}
                onClick={() => navigate(`/portal/applications/${app.id}`)}
                className="px-5 py-4 flex items-center justify-between hover:bg-surface-2 cursor-pointer transition-colors"
              >
                <div>
                  <div className="text-sm font-bold text-ink-primary font-mono">{app.application_number}</div>
                  <div className="text-xs text-ink-muted mt-0.5">
                    INR {app.loan_amount.toLocaleString()} &middot; {new Date(app.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide
                  ${STATUS_COLORS[app.final_decision] ?? STATUS_COLORS[app.status] ?? 'bg-gray-100 text-gray-700'}`}>
                  {(app.final_decision !== 'pending' ? app.final_decision : app.status).replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-10 text-center">
            <div className="w-12 h-12 rounded-xl bg-cr-50 flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-sm font-bold text-ink-primary">No applications yet</h3>
            <p className="text-xs text-ink-secondary mt-1 max-w-xs mx-auto">
              Start by uploading your financial documents. Once the bank creates your application, you can track its progress here.
            </p>
            <button
              onClick={() => navigate('/portal/documents')}
              className="btn btn-primary mt-4"
            >
              Upload Documents
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color = 'text-ink-primary' }: { label: string; value: number; color?: string }) {
  return (
    <div className="card p-4">
      <div className={`text-2xl font-extrabold font-mono tabular ${color}`}>{value}</div>
      <div className="text-[10px] font-bold uppercase tracking-wider text-ink-muted mt-1 font-mono">{label}</div>
    </div>
  )
}
