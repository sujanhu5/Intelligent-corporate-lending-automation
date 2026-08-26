import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { portalApi } from '@/api/portal'
import { PageLoader } from '@/components/ui/Spinner'

const STATUS_COLORS: Record<string, string> = {
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  manual_review: 'bg-amber-100 text-amber-800',
  pending: 'bg-gray-100 text-gray-700',
  submitted: 'bg-blue-100 text-blue-800',
  draft: 'bg-gray-100 text-gray-600',
  ocr_complete: 'bg-cyan-100 text-cyan-800',
  ratio_calculated: 'bg-indigo-100 text-indigo-800',
  rule_evaluated: 'bg-violet-100 text-violet-800',
  ml_predicted: 'bg-purple-100 text-purple-800',
  report_generated: 'bg-teal-100 text-teal-800',
}

interface AppItem {
  id: string
  application_number: string
  loan_amount_requested: number
  loan_purpose: string | null
  loan_tenure_months: number
  status: string
  final_decision: string
  risk_score: number | null
  created_at: string
  updated_at: string
  pipeline: {
    ocr_completed: boolean
    ratios_calculated: boolean
    rules_evaluated: boolean
    ml_predicted: boolean
    report_generated: boolean
  }
}

export default function PortalApplications() {
  const [apps, setApps] = useState<AppItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    portalApi.applications(1, 50)
      .then((data: any) => { setApps(data.items); setTotal(data.total) })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <PageLoader />

  const completedStages = (p: AppItem['pipeline']) =>
    [p.ocr_completed, p.ratios_calculated, p.rules_evaluated, p.ml_predicted, p.report_generated].filter(Boolean).length

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-h2 text-ink-primary">My Applications</h1>
          <p className="text-small text-ink-secondary mt-1">{total} application{total !== 1 ? 's' : ''} total</p>
        </div>
      </div>

      {apps.length > 0 ? (
        <div className="flex flex-col gap-3">
          {apps.map(app => (
            <div
              key={app.id}
              onClick={() => navigate(`/portal/applications/${app.id}`)}
              className="card card-hover p-5 cursor-pointer"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm font-bold text-ink-primary font-mono">{app.application_number}</div>
                  <div className="text-xs text-ink-secondary mt-1">
                    INR {app.loan_amount_requested.toLocaleString()} &middot;{' '}
                    {app.loan_purpose?.replace('_', ' ')} &middot;{' '}
                    {app.loan_tenure_months} months
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide flex-shrink-0
                  ${STATUS_COLORS[app.final_decision !== 'pending' ? app.final_decision : app.status] ?? 'bg-gray-100 text-gray-700'}`}>
                  {(app.final_decision !== 'pending' ? app.final_decision : app.status).replace(/_/g, ' ')}
                </span>
              </div>

              {/* Pipeline progress bar */}
              <div className="mt-3 flex items-center gap-1.5">
                {['OCR', 'Ratios', 'Rules', 'ML', 'Report'].map((stage, i) => {
                  const done = [
                    app.pipeline.ocr_completed,
                    app.pipeline.ratios_calculated,
                    app.pipeline.rules_evaluated,
                    app.pipeline.ml_predicted,
                    app.pipeline.report_generated,
                  ][i]
                  return (
                    <div key={stage} className="flex items-center flex-1">
                      <div className={`h-1.5 flex-1 rounded-full transition-colors ${done ? 'gradient-orange' : 'bg-surface-2'}`} />
                    </div>
                  )
                })}
                <span className="text-[10px] text-ink-muted font-mono ml-1">{completedStages(app.pipeline)}/5</span>
              </div>

              <div className="mt-2 flex items-center gap-4 text-[11px] text-ink-muted">
                <span>Submitted {new Date(app.created_at).toLocaleDateString()}</span>
                <span>Updated {new Date(app.updated_at).toLocaleDateString()}</span>
                {app.risk_score != null && <span>Risk: {app.risk_score.toFixed(1)}/100</span>}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="text-4xl mb-3">📋</div>
          <h3 className="text-sm font-bold text-ink-primary">No applications yet</h3>
          <p className="text-xs text-ink-secondary mt-1">Your loan applications will appear here once the bank processes them.</p>
        </div>
      )}
    </div>
  )
}
