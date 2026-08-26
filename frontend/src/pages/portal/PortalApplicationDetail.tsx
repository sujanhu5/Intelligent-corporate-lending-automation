import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { portalApi } from '@/api/portal'
import { PageLoader } from '@/components/ui/Spinner'

interface TimelineStep {
  label: string
  key: string
  completed: boolean
  current: boolean
}

interface DocItem {
  id: string
  document_type: string | null
  original_filename: string
  status: string | null
  uploaded_at: string
}

interface AppDetail {
  id: string
  application_number: string
  loan_amount_requested: number
  loan_purpose: string | null
  loan_tenure_months: number
  interest_rate_requested: number | null
  collateral_description: string | null
  collateral_value: number | null
  status: string
  final_decision: string
  decision_reason: string | null
  risk_score: number | null
  created_at: string
  updated_at: string
  pipeline: Record<string, boolean>
  timeline: TimelineStep[]
  documents: DocItem[]
}

const DECISION_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  approved: { bg: 'bg-green-50 border-green-200', text: 'text-green-800', label: 'Approved' },
  rejected: { bg: 'bg-red-50 border-red-200', text: 'text-red-800', label: 'Rejected' },
  manual_review: { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-800', label: 'Under Manual Review' },
  pending: { bg: 'bg-gray-50 border-gray-200', text: 'text-gray-700', label: 'Decision Pending' },
}

export default function PortalApplicationDetail() {
  const { id } = useParams<{ id: string }>()
  const [app, setApp] = useState<AppDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    portalApi.applicationDetail(id)
      .then(setApp)
      .catch(() => setError('Application not found.'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <PageLoader />
  if (error || !app) return (
    <div className="card p-12 text-center">
      <h2 className="text-h4 text-ink-primary">Application Not Found</h2>
      <p className="text-small text-ink-secondary mt-2">{error}</p>
      <Link to="/portal/applications" className="btn btn-secondary mt-4">Back to Applications</Link>
    </div>
  )

  const decisionStyle = DECISION_STYLE[app.final_decision] ?? DECISION_STYLE.pending
  const completedSteps = app.timeline.filter(t => t.completed).length
  const totalSteps = app.timeline.length
  const progressPct = Math.round((completedSteps / totalSteps) * 100)

  return (
    <div>
      <Link to="/portal/applications" className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-primary mb-4 transition-colors">
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to applications
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-h2 text-ink-primary font-mono">{app.application_number}</h1>
          <p className="text-small text-ink-secondary mt-1">
            Submitted on {new Date(app.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        </div>
        <div className={`px-4 py-2 rounded-xl border-2 ${decisionStyle.bg}`}>
          <div className={`text-sm font-bold ${decisionStyle.text}`}>{decisionStyle.label}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Timeline + Decision */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Progress overview */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-h4 text-ink-primary">Processing Progress</h2>
              <span className="text-xs font-bold text-ink-muted font-mono">{progressPct}% complete</span>
            </div>
            <div className="w-full h-2 bg-surface-2 rounded-full overflow-hidden mb-4">
              <div className="h-full gradient-orange rounded-full transition-all" style={{ width: `${progressPct}%` }} />
            </div>

            {/* Timeline */}
            <div className="flex flex-col gap-0">
              {app.timeline.map((step, i) => (
                <div key={step.key} className="flex items-start gap-3">
                  <div className="flex flex-col items-center">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0
                      ${step.completed ? 'gradient-orange text-white' : step.current ? 'border-2 border-primary bg-cr-50 text-primary' : 'bg-surface-2 border border-border-subtle text-ink-muted'}`}>
                      {step.completed ? '✓' : i + 1}
                    </div>
                    {i < app.timeline.length - 1 && (
                      <div className={`w-0.5 h-6 ${step.completed ? 'bg-primary' : 'bg-border-subtle'}`} />
                    )}
                  </div>
                  <div className="pb-4">
                    <div className={`text-sm font-semibold ${step.completed ? 'text-ink-primary' : step.current ? 'text-primary' : 'text-ink-muted'}`}>
                      {step.label}
                    </div>
                    {step.current && (
                      <div className="text-[11px] text-primary mt-0.5 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                        In progress
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Decision reason */}
          {app.decision_reason && (
            <div className={`card p-5 border-2 ${decisionStyle.bg}`}>
              <h3 className={`text-sm font-bold ${decisionStyle.text} mb-2`}>Decision Summary</h3>
              <p className="text-sm text-ink-secondary leading-relaxed">{app.decision_reason}</p>
            </div>
          )}
        </div>

        {/* Right column: Loan details + Documents */}
        <div className="flex flex-col gap-6">
          <div className="card p-5">
            <h3 className="text-h4 text-ink-primary mb-4">Loan Details</h3>
            <div className="flex flex-col gap-3">
              <DetailRow label="Amount Requested" value={`INR ${app.loan_amount_requested.toLocaleString()}`} />
              <DetailRow label="Purpose" value={app.loan_purpose?.replace(/_/g, ' ')} />
              <DetailRow label="Tenure" value={`${app.loan_tenure_months} months`} />
              {app.interest_rate_requested && <DetailRow label="Interest Rate" value={`${app.interest_rate_requested}%`} />}
              {app.collateral_description && <DetailRow label="Collateral" value={app.collateral_description} />}
              {app.collateral_value && <DetailRow label="Collateral Value" value={`INR ${app.collateral_value.toLocaleString()}`} />}
              {app.risk_score != null && <DetailRow label="Risk Score" value={`${app.risk_score.toFixed(1)} / 100`} />}
            </div>
          </div>

          {app.documents.length > 0 && (
            <div className="card p-5">
              <h3 className="text-h4 text-ink-primary mb-4">Documents</h3>
              <div className="flex flex-col gap-2">
                {app.documents.map(doc => (
                  <div key={doc.id} className="flex items-center justify-between py-2 border-b border-border-subtle last:border-0">
                    <div>
                      <div className="text-xs font-medium text-ink-primary">{doc.original_filename}</div>
                      <div className="text-[11px] text-ink-muted">{doc.document_type?.replace(/_/g, ' ')}</div>
                    </div>
                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full
                      ${doc.status === 'extracted' ? 'bg-green-100 text-green-800'
                      : doc.status === 'failed' ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-700'}`}>
                      {doc.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="card p-5">
            <h3 className="text-h4 text-ink-primary mb-2">Last Updated</h3>
            <p className="text-sm text-ink-secondary">
              {new Date(app.updated_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex justify-between">
      <span className="text-xs text-ink-muted">{label}</span>
      <span className="text-xs font-medium text-ink-primary text-right">{value ?? '—'}</span>
    </div>
  )
}
