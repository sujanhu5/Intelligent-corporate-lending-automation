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

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-h2 text-ink-primary">{data?.company_name ?? 'Company'}</h1>
        <p className="text-small text-ink-secondary mt-1">
          Company status:{' '}
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wide
            ${data?.company_status === 'active' ? 'bg-green-100 text-green-800'
            : data?.company_status === 'under_review' ? 'bg-amber-100 text-amber-800'
            : 'bg-gray-100 text-gray-700'}`}>
            {data?.company_status?.replace('_', ' ')}
          </span>
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Applications" value={data?.total_applications ?? 0} color="text-ink-primary" />
        <StatCard label="Approved" value={data?.approved ?? 0} color="text-green-600" />
        <StatCard label="Under Review" value={(data?.in_pipeline ?? 0) + (data?.manual_review ?? 0)} color="text-amber-600" />
        <StatCard label="Rejected" value={data?.rejected ?? 0} color="text-red-600" />
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        <button
          onClick={() => navigate('/portal/applications')}
          className="card card-hover p-5 text-left"
        >
          <div className="text-lg mb-2">📋</div>
          <div className="text-sm font-bold text-ink-primary">View All Applications</div>
          <div className="text-xs text-ink-secondary mt-1">Track the status of all your loan applications</div>
        </button>

        <button
          onClick={() => navigate('/portal/company')}
          className="card card-hover p-5 text-left"
        >
          <div className="text-lg mb-2">🏢</div>
          <div className="text-sm font-bold text-ink-primary">Company Profile</div>
          <div className="text-xs text-ink-secondary mt-1">View and manage your company information</div>
        </button>

        <div className="card p-5 text-left">
          <div className="text-lg mb-2">📞</div>
          <div className="text-sm font-bold text-ink-primary">Need Help?</div>
          <div className="text-xs text-ink-secondary mt-1">Contact your assigned loan officer for assistance</div>
        </div>
      </div>

      {/* Recent applications */}
      <div className="card">
        <div className="p-5 border-b border-border-subtle">
          <h2 className="text-h4 text-ink-primary">Recent Applications</h2>
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
                    INR {app.loan_amount.toLocaleString()} &middot; {new Date(app.created_at).toLocaleDateString()}
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide
                  ${STATUS_COLORS[app.final_decision] ?? STATUS_COLORS[app.status] ?? 'bg-gray-100 text-gray-700'}`}>
                  {(app.final_decision !== 'pending' ? app.final_decision : app.status).replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-ink-muted text-small">
            No applications yet. Your loan applications will appear here once submitted.
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="card p-5">
      <div className={`text-3xl font-extrabold font-mono tabular ${color}`}>{value}</div>
      <div className="text-[10px] font-bold uppercase tracking-wider text-ink-muted mt-1.5 font-mono">{label}</div>
    </div>
  )
}
