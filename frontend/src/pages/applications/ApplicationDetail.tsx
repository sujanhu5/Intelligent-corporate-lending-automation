import React, { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { applicationsApi } from '@/api/applications'
import { documentsApi } from '@/api/documents'
import { ocrApi } from '@/api/ocr'
import { ratiosApi } from '@/api/ratios'
import { rulesApi } from '@/api/rules'
import { predictionsApi } from '@/api/predictions'
import { reportsApi } from '@/api/reports'
import type {
  Application, ApplicationOCRSummary, Document, FinancialRatioResponse,
  RuleEngineResponse, PredictionResponse, Report
} from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import { ApplicationStatusBadge, RiskBadge, DocStatusBadge } from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { PageLoader } from '@/components/ui/Spinner'
import Modal, { ConfirmModal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'

type Tab = 'overview' | 'documents' | 'ocr' | 'ratios' | 'rules' | 'prediction' | 'reports'

function PipelineStepper({ steps }: { steps: { label: string; done: boolean }[] }) {
  // First not-done step is the "current" one.
  const currentIdx = steps.findIndex(s => !s.done)
  return (
    <div className="flex items-center w-full">
      {steps.map((step, i) => {
        const isCurrent = i === currentIdx
        return (
          <div key={step.label} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-2">
              <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold font-mono border-2 transition-all
                ${step.done
                  ? 'gradient-orange text-white border-transparent shadow-orange'
                  : isCurrent
                    ? 'bg-surface-1 text-primary border-primary'
                    : 'bg-surface-1 text-ink-muted border-border-subtle'}`}>
                {step.done ? '✓' : i + 1}
              </div>
              <span className={`text-[10px] font-bold uppercase tracking-wide font-mono whitespace-nowrap
                ${step.done || isCurrent ? 'text-ink-primary' : 'text-ink-muted'}`}>
                {step.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className="flex-1 h-0.5 mx-2 -mt-6 rounded-full overflow-hidden bg-border-subtle">
                <div className={`h-full rounded-full transition-all duration-500 ${step.done ? 'gradient-orange w-full' : 'w-0'}`} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function ApplicationDetail() {
  const { id } = useParams<{ id: string }>()
  const { success, error: toastError } = useToast()

  const [app, setApp] = useState<Application | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [ratios, setRatios] = useState<FinancialRatioResponse | null>(null)
  const [ruleEval, setRuleEval] = useState<RuleEngineResponse | null>(null)
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [confirmWithdraw, setConfirmWithdraw] = useState(false)
  const [decisionModal, setDecisionModal] = useState<'approved' | 'rejected' | null>(null)
  const [decisionReason, setDecisionReason] = useState('')

  const load = useCallback(async () => {
    if (!id) return
    try {
      const a = await applicationsApi.get(id)
      setApp(a)

      const docs = await documentsApi.listForApplication(id).catch(() => null)
      setDocuments(docs?.items ?? [])

      if (a.pipeline.ratios_calculated) {
        setRatios(await ratiosApi.getForApplication(id).catch(() => null))
      }
      if (a.pipeline.rules_evaluated) {
        setRuleEval(await rulesApi.getEvaluation(id).catch(() => null))
      }
      if (a.pipeline.ml_predicted) {
        setPrediction(await predictionsApi.get(id).catch(() => null))
      }
      if (a.pipeline.report_generated) {
        setReport(await reportsApi.getLatest(id).catch(() => null))
      }
    } catch (err) {
      toastError(extractError(err))
    } finally {
      setLoading(false)
    }
  }, [id, toastError])

  useEffect(() => { load() }, [load])

  const run = async (action: string, fn: () => Promise<void>) => {
    setActionLoading(action)
    try { await fn(); await load() } catch (err) { toastError(extractError(err)) }
    finally { setActionLoading(null) }
  }

  if (loading) return <PageLoader />
  if (!app) return <div className="text-ink-muted">Application not found.</div>

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview',   label: 'Overview' },
    { key: 'documents',  label: `Documents (${documents.length})` },
    { key: 'ocr',        label: 'OCR' },
    { key: 'ratios',     label: 'Ratios' },
    { key: 'rules',      label: 'Rules' },
    { key: 'prediction', label: 'ML Prediction' },
    { key: 'reports',    label: 'Reports' },
  ]

  const pipeline = app.pipeline
  const canSubmit = app.status === 'draft' && documents.length > 0
  const canRunOCR = documents.some(d => d.status === 'uploaded')
  const canRunRatios = pipeline.ocr_completed && !pipeline.ratios_calculated
  const canRunRules = pipeline.ratios_calculated && !pipeline.rules_evaluated
  const canRunML = pipeline.rules_evaluated && !pipeline.ml_predicted
  const canGenReport = pipeline.ratios_calculated

  return (
    <div>
      <PageHeader
        title={app.application_number}
        subtitle={app.company?.name}
        breadcrumb={[{ label: 'Applications', href: '/applications' }, { label: app.application_number }]}
        actions={
          <div className="flex gap-2">
            {app.status === 'draft' && (
              <Button
                variant="secondary" size="sm"
                loading={actionLoading === 'submit'}
                disabled={!canSubmit}
                onClick={() => run('submit', () => applicationsApi.submit(app.id).then(() => success('Application submitted.')))}
              >
                Submit
              </Button>
            )}
            {['submitted', 'ocr_complete', 'ratio_calculated', 'rule_evaluated', 'ml_predicted', 'report_generated', 'manual_review'].includes(app.status) && (
              <>
                {canRunOCR && (
                  <Button size="sm" loading={actionLoading === 'ocr'}
                    onClick={() => run('ocr', async () => {
                      for (const doc of documents.filter(d => d.status === 'uploaded')) {
                        await ocrApi.process(doc.id)
                      }
                      success('OCR complete.')
                    })}>
                    Run OCR
                  </Button>
                )}
                {canRunRatios && (
                  <Button size="sm" loading={actionLoading === 'ratios'}
                    onClick={() => run('ratios', () => ratiosApi.calculate(app.id).then(() => success('Ratios calculated.')))}>
                    Calc Ratios
                  </Button>
                )}
                {canRunRules && (
                  <Button size="sm" loading={actionLoading === 'rules'}
                    onClick={() => run('rules', () => rulesApi.evaluate(app.id).then(() => success('Rules evaluated.')))}>
                    Eval Rules
                  </Button>
                )}
                {canRunML && (
                  <Button size="sm" loading={actionLoading === 'ml'}
                    onClick={() => run('ml', () => predictionsApi.predict(app.id).then(() => success('ML prediction complete.')))}>
                    Run ML
                  </Button>
                )}
                {canGenReport && (
                  <Button size="sm" variant="secondary" loading={actionLoading === 'report'}
                    onClick={() => run('report', () => reportsApi.generate(app.id).then(() => success('Report generated.')))}>
                    Gen Report
                  </Button>
                )}
              </>
            )}
            {!['approved', 'rejected', 'withdrawn'].includes(app.status) && (
              <>
                <Button size="sm" variant="ghost"
                  onClick={() => setDecisionModal('approved')}>
                  Approve
                </Button>
                <Button size="sm" variant="danger"
                  onClick={() => setDecisionModal('rejected')}>
                  Reject
                </Button>
              </>
            )}
            {!['approved', 'rejected', 'withdrawn'].includes(app.status) && (
              <Button size="sm" variant="secondary"
                onClick={() => setConfirmWithdraw(true)}>
                Withdraw
              </Button>
            )}
          </div>
        }
      />

      {/* Pipeline stepper */}
      <div className="card p-5 mb-6">
        <div className="flex items-center justify-between mb-5">
          <span className="eyebrow"><span className="w-1.5 h-1.5 rounded-full bg-primary" />Assessment Pipeline</span>
          <div className="flex items-center gap-2">
            <ApplicationStatusBadge status={app.status} />
            {prediction && <RiskBadge level={prediction.risk_level} />}
          </div>
        </div>
        <PipelineStepper steps={[
          { label: 'Documents', done: documents.length > 0 },
          { label: 'OCR', done: pipeline.ocr_completed },
          { label: 'Ratios', done: pipeline.ratios_calculated },
          { label: 'Rules', done: pipeline.rules_evaluated },
          { label: 'ML', done: pipeline.ml_predicted },
          { label: 'Report', done: pipeline.report_generated },
        ]} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5 mb-6 overflow-x-auto pb-1">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 rounded-full text-xs font-bold font-mono whitespace-nowrap transition-all
              ${activeTab === t.key
                ? 'gradient-orange text-white shadow-orange'
                : 'bg-surface-1 border border-border-subtle text-ink-secondary hover:text-ink-primary hover:border-border'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="card p-5">
            <h3 className="text-h4 mb-3">Loan Details</h3>
            {[
              ['Amount Requested', `RM ${app.loan_amount_requested.toLocaleString()}`],
              ['Purpose',          app.loan_purpose.replace(/_/g, ' ')],
              ['Tenure',           `${app.loan_tenure_months} months`],
              ['Interest Rate',    app.interest_rate_requested ? `${app.interest_rate_requested}%` : '—'],
              ['Collateral',       app.collateral_description ?? '—'],
              ['Collateral Value', app.collateral_value ? `RM ${app.collateral_value.toLocaleString()}` : '—'],
              ['Risk Score',       app.risk_score != null ? app.risk_score.toFixed(1) : '—'],
              ['Decision',         app.final_decision],
            ].map(([label, value]) => (
              <div key={label} className="flex gap-4 py-2.5 border-b border-border-subtle last:border-0">
                <span className="text-xs text-ink-secondary w-40 flex-shrink-0 font-mono uppercase tracking-wide pt-0.5">{label}</span>
                <span className="text-small text-ink-primary font-semibold font-mono">{value}</span>
              </div>
            ))}
          </div>
          <div className="card p-5">
            <h3 className="text-h4 mb-3">Notes</h3>
            <div className="text-small text-ink-secondary">
              {app.decision_reason || app.officer_notes
                ? <><p><strong>Decision reason:</strong> {app.decision_reason ?? '—'}</p>
                    <p className="mt-2"><strong>Officer notes:</strong> {app.officer_notes ?? '—'}</p></>
                : <span className="text-ink-muted">No notes yet.</span>}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'documents' && (
        <DocumentsTab appId={app.id} documents={documents} onRefresh={load} />
      )}

      {activeTab === 'ocr' && (
        <OCRTab appId={app.id} />
      )}

      {activeTab === 'ratios' && (
        <RatiosTab ratios={ratios} />
      )}

      {activeTab === 'rules' && (
        <RulesTab ruleEval={ruleEval} />
      )}

      {activeTab === 'prediction' && (
        <PredictionTab prediction={prediction} />
      )}

      {activeTab === 'reports' && (
        <ReportsTab appId={app.id} report={report} />
      )}

      {/* Withdraw confirm */}
      <ConfirmModal
        open={confirmWithdraw}
        title="Withdraw Application"
        description="This will move the application to withdrawn status. Are you sure?"
        confirmLabel="Withdraw"
        variant="danger"
        loading={actionLoading === 'withdraw'}
        onConfirm={() => run('withdraw', () => applicationsApi.withdraw(app.id).then(() => {
          success('Application withdrawn.'); setConfirmWithdraw(false)
        }))}
        onClose={() => setConfirmWithdraw(false)}
      />

      {/* Decision */}
      <Modal
        open={decisionModal !== null}
        title={decisionModal === 'approved' ? 'Approve Application' : 'Reject Application'}
        description={`Record the ${decisionModal} decision for ${app.application_number}. A reason is required and is written to the audit log.`}
        onClose={() => { setDecisionModal(null); setDecisionReason('') }}
        footer={
          <>
            <Button variant="secondary" onClick={() => { setDecisionModal(null); setDecisionReason('') }}>
              Cancel
            </Button>
            <Button
              variant={decisionModal === 'rejected' ? 'danger' : 'primary'}
              loading={actionLoading === 'decision'}
              disabled={!decisionReason.trim()}
              onClick={() => run('decision', () =>
                applicationsApi.decision(app.id, {
                  decision: decisionModal!,
                  decision_reason: decisionReason.trim(),
                }).then(() => {
                  success(`Application ${decisionModal}.`)
                  setDecisionModal(null)
                  setDecisionReason('')
                })
              )}
            >
              {decisionModal === 'approved' ? 'Approve' : 'Reject'}
            </Button>
          </>
        }
      >
        <Textarea
          label="Decision reason"
          rows={4}
          value={decisionReason}
          onChange={e => setDecisionReason(e.target.value)}
          placeholder="e.g. Strong liquidity and coverage ratios; all mandatory rules passed."
        />
      </Modal>
    </div>
  )
}

// ─── Sub-tab components ───────────────────────────────────────────────────────

function DocumentsTab({ appId, documents, onRefresh }: {
  appId: string; documents: Document[]; onRefresh: () => void
}) {
  const [uploading, setUploading] = useState(false)
  const [docType, setDocType] = useState('balance_sheet')
  const [year, setYear] = useState('')
  const { success, error } = useToast()

  const DOC_TYPES = [
    { value: 'balance_sheet',   label: 'Balance Sheet' },
    { value: 'profit_loss',     label: 'Profit & Loss Statement' },
    { value: 'cash_flow',       label: 'Cash Flow Statement' },
    { value: 'auditor_report',  label: 'Auditor Report' },
    { value: 'gst_report',      label: 'GST Report' },
    { value: 'bank_statement',  label: 'Bank Statement' },
    { value: 'other',           label: 'Other' },
  ]

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await documentsApi.upload(appId, file, docType, year ? parseInt(year) : undefined)
      success(`${file.name} uploaded.`)
      onRefresh()
    } catch (err) {
      error(extractError(err))
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleDelete = async (docId: string, filename: string) => {
    try {
      await documentsApi.delete(docId)
      success(`${filename} deleted.`)
      onRefresh()
    } catch (err) {
      error(extractError(err))
    }
  }

  return (
    <div>
      {/* Upload bar */}
      <div className="card p-4 mb-5 flex flex-wrap items-end gap-3">
        <div>
          <label className="label">Document Type</label>
          <select className="input w-52" value={docType} onChange={e => setDocType(e.target.value)}>
            {DOC_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Financial Year (optional)</label>
          <input className="input w-28" type="number" placeholder="e.g. 2024" value={year} onChange={e => setYear(e.target.value)} />
        </div>
        <label className={`btn btn-primary ${uploading ? 'opacity-50 pointer-events-none' : ''} cursor-pointer`}>
          {uploading ? 'Uploading…' : '+ Upload PDF'}
          <input type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff" className="hidden" onChange={handleUpload} />
        </label>
      </div>

      {documents.length === 0 ? (
        <div className="card flex items-center justify-center py-14 text-ink-muted text-small">
          No documents uploaded yet.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {documents.map(doc => (
            <div key={doc.id} className="card px-4 py-3 flex items-center gap-4">
              <span className="text-2xl">📄</span>
              <div className="flex-1 min-w-0">
                <div className="text-small font-medium text-ink-primary truncate">{doc.original_filename}</div>
                <div className="text-[11px] text-ink-muted mt-0.5">
                  {doc.document_type.replace(/_/g, ' ')}
                  {doc.financial_year && ` · FY${doc.financial_year}`}
                  · {(doc.file_size_bytes / 1024).toFixed(0)} KB
                </div>
              </div>
              <DocStatusBadge status={doc.status} />
              <button
                onClick={() => handleDelete(doc.id, doc.original_filename)}
                className="text-xs text-ink-muted hover:text-danger-500 transition-colors"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function OCRTab({ appId }: { appId: string }) {
  const [data, setData] = useState<ApplicationOCRSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const { error } = useToast()

  useEffect(() => {
    ocrApi.getForApplication(appId)
      .then(setData)
      .catch(err => error(extractError(err)))
      .finally(() => setLoading(false))
  }, [appId, error])

  if (loading) return <div className="py-10 flex justify-center"><span className="text-ink-muted text-small">Loading OCR data…</span></div>
  if (!data) return <div className="text-ink-muted text-small">No OCR data available.</div>

  const fields = Object.entries(data.combined_fields ?? {})
  const populated = fields.filter(([, v]) => v != null)

  return (
    <div>
      <div className="mb-4 card px-4 py-3 flex items-center gap-6 flex-wrap text-small">
        <span className="text-ink-secondary">
          Documents: <span className="text-ink-primary font-medium">{data.extracted_documents}/{data.total_documents} extracted</span>
        </span>
        {data.failed_documents > 0 && (
          <span className="text-red-700">{data.failed_documents} failed</span>
        )}
        <span className="text-ink-secondary">
          Fields: <span className="text-ink-primary font-medium">{populated.length}/{fields.length}</span>
        </span>
        {data.overall_confidence != null && (
          <span className="text-ink-muted text-xs ml-auto">
            Confidence {(data.overall_confidence * 100).toFixed(1)}%
          </span>
        )}
      </div>

      {data.warnings.length > 0 && (
        <div className="mb-4 p-3 rounded-sm bg-warning-50 border border-warning-500 text-small text-amber-700">
          {data.warnings.map((w, i) => <div key={i}>{w}</div>)}
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="bg-surface-2 px-4 py-3 border-b border-border-subtle">
          <span className="text-caption text-ink-secondary uppercase tracking-wider">Extracted Financial Fields</span>
        </div>
        <div className="divide-y divide-border-subtle">
          {fields.length === 0 ? (
            <div className="px-4 py-8 text-ink-muted text-small text-center">No fields extracted yet.</div>
          ) : fields.map(([k, v]) => (
            <div key={k} className="flex gap-4 px-4 py-2.5">
              <span className="text-small text-ink-secondary w-56 flex-shrink-0 font-mono text-xs">{k}</span>
              <span className={`text-small font-medium tabular ${v == null ? 'text-ink-muted' : 'text-ink-primary'}`}>
                {v == null ? '—' : `RM ${v.toLocaleString()}`}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function RatiosTab({ ratios }: { ratios: FinancialRatioResponse | null }) {
  if (!ratios) return <div className="text-ink-muted text-small">Ratios not calculated yet. Run ratio calculation from the action bar above.</div>

  const riskColor: Record<string, string> = {
    low:      'text-green-700 bg-success-50',
    medium:   'text-amber-700 bg-warning-50',
    high:     'text-teal-700 bg-teal-50',
    critical: 'text-red-700 bg-danger-50',
  }

  return (
    <div>
      {ratios.overall_health && (
        <div className="mb-4 card px-4 py-3 flex items-center gap-3">
          <span className="text-small font-semibold text-ink-secondary">Overall Health:</span>
          <span className={`badge ${riskColor[ratios.overall_health] ?? ''}`}>{ratios.overall_health.toUpperCase()}</span>
        </div>
      )}
      <div className="overflow-x-auto rounded-md border border-border-subtle shadow-xs">
        <table className="w-full border-collapse text-small">
          <thead className="bg-surface-2">
            <tr>
              {['Ratio', 'Value', 'Benchmark', 'Risk Level', 'Interpretation'].map(h => (
                <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-surface-1 divide-y divide-border-subtle">
            {ratios.ratios.map(r => (
              <tr key={r.name}>
                <td className="px-4 py-3 font-medium">{r.display_name}</td>
                <td className="px-4 py-3 tabular text-right">
                  {r.value != null ? `${r.value.toFixed(4)} ${r.unit}` : '—'}
                </td>
                <td className="px-4 py-3 tabular text-right text-ink-secondary text-xs">
                  {r.benchmark_min != null && r.benchmark_max != null
                    ? `${r.benchmark_min} – ${r.benchmark_max}`
                    : '—'}
                </td>
                <td className="px-4 py-3">
                  <span className={`badge ${riskColor[r.risk_level] ?? ''}`}>{r.risk_level}</span>
                </td>
                <td className="px-4 py-3 text-ink-secondary max-w-xs">{r.interpretation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function RulesTab({ ruleEval }: { ruleEval: RuleEngineResponse | null }) {
  if (!ruleEval) return <div className="text-ink-muted text-small">Rules not evaluated yet.</div>

  const outcomeColor: Record<string, string> = {
    pass:          'bg-success-50 text-green-700',
    reject:        'bg-danger-50 text-red-700',
    manual_review: 'bg-teal-50 text-teal-700',
  }

  // Failures first, then by configured priority.
  const rules = [...ruleEval.results].sort(
    (a, b) => Number(b.triggered) - Number(a.triggered) || a.priority - b.priority
  )

  return (
    <div>
      <div className="mb-4 card px-4 py-3 flex items-center gap-4 flex-wrap">
        <span className="text-small font-semibold text-ink-secondary">Verdict:</span>
        <span className={`badge ${outcomeColor[ruleEval.overall_outcome] ?? ''}`}>
          {ruleEval.overall_outcome.replace(/_/g, ' ')}
        </span>
        <span className="text-xs text-ink-muted ml-auto">
          {ruleEval.passed_rules.length}/{ruleEval.total_rules} passed
          · {ruleEval.triggered_count} triggered
          · ML {ruleEval.ml_should_run ? 'will run' : 'skipped'}
        </span>
      </div>

      {ruleEval.rejection_reason && (
        <div className="mb-4 p-3 rounded-sm bg-danger-50 border border-danger-500 text-small text-red-700">
          {ruleEval.rejection_reason}
        </div>
      )}

      <div className="overflow-x-auto rounded-md border border-border-subtle shadow-xs">
        <table className="w-full border-collapse text-small">
          <thead className="bg-surface-2">
            <tr>
              {['Rule', 'Metric', 'Value', 'Threshold', 'Mandatory', 'Result', 'Message'].map(h => (
                <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-surface-1 divide-y divide-border-subtle">
            {rules.map(r => (
              <tr key={r.rule_id}>
                <td className="px-4 py-3 font-medium">{r.rule_name}</td>
                <td className="px-4 py-3 font-mono text-xs text-ink-secondary">{r.metric_field}</td>
                <td className="px-4 py-3 tabular text-right">{r.metric_value?.toFixed(4) ?? '—'}</td>
                <td className="px-4 py-3 tabular text-right">{r.threshold ?? '—'}</td>
                <td className="px-4 py-3 text-xs text-ink-secondary">{r.is_mandatory ? 'Yes' : 'No'}</td>
                <td className="px-4 py-3">
                  <span className={`badge ${r.triggered ? 'bg-danger-50 text-red-700' : 'bg-success-50 text-green-700'}`}>
                    {r.triggered ? `FAIL · ${r.action.replace(/_/g, ' ')}` : 'PASS'}
                  </span>
                </td>
                <td className="px-4 py-3 text-ink-secondary text-xs max-w-xs">{r.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PredictionTab({ prediction }: { prediction: PredictionResponse | null }) {
  if (!prediction) return <div className="text-ink-muted text-small">ML prediction not run yet.</div>

  const shapEntries = Object.entries(prediction.shap_values)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 10)

  const maxAbs = Math.max(...shapEntries.map(([, v]) => Math.abs(v)), 0.001)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="card p-5">
        <h3 className="text-h4 mb-4">Prediction Summary</h3>

        {/* Risk score hero */}
        <div className="rounded-xl gradient-orange p-5 mb-5 relative overflow-hidden">
          <div
            className="absolute inset-0 opacity-[0.12]"
            style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,.6) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.6) 1px,transparent 1px)', backgroundSize: '28px 28px' }}
          />
          <div className="relative flex items-end justify-between">
            <div>
              <div className="text-white/80 text-[10px] font-bold uppercase tracking-[0.12em] font-mono mb-1">Composite Risk Score</div>
              <div className="text-white text-5xl font-extrabold font-mono tabular leading-none">{prediction.risk_score.toFixed(1)}</div>
              <div className="text-white/85 text-xs font-mono mt-2 uppercase tracking-wide">{prediction.risk_level.replace(/_/g, ' ')} · {prediction.outcome.replace(/_/g, ' ')}</div>
            </div>
            <div className="text-right">
              <div className="text-white/80 text-[10px] font-bold uppercase tracking-[0.12em] font-mono mb-1">Prob. of Default</div>
              <div className="text-white text-3xl font-extrabold font-mono tabular leading-none">{(prediction.probability_of_default * 100).toFixed(1)}%</div>
            </div>
          </div>
        </div>

        {[
          ['Model Used', prediction.model_used.replace(/_/g, ' ')],
          ['Probability of Default', `${(prediction.probability_of_default * 100).toFixed(2)}%`],
          ['Risk Score', prediction.risk_score.toFixed(1)],
          ['Risk Level', prediction.risk_level],
          ['Outcome', prediction.outcome.replace(/_/g, ' ')],
          ['ML Executed', prediction.ml_executed ? 'Yes' : 'No (bypassed)'],
          ...(prediction.skip_reason ? [['Skip Reason', prediction.skip_reason]] : []),
        ].map(([label, value]) => (
          <div key={label as string} className="flex gap-4 py-2 border-b border-border-subtle last:border-0">
            <span className="text-xs text-ink-secondary w-44 flex-shrink-0 font-mono uppercase tracking-wide pt-0.5">{label}</span>
            <span className="text-small text-ink-primary font-semibold font-mono capitalize">{value}</span>
          </div>
        ))}
        {prediction.recommendation && (
          <div className="mt-4 p-3 bg-cr-50 rounded-sm text-small text-cr-800 border border-cr-200">
            <strong>Recommendation:</strong> {prediction.recommendation}
          </div>
        )}
      </div>

      <div className="card p-5">
        <h3 className="text-h4 mb-4">Top SHAP Drivers</h3>
        {shapEntries.length === 0 ? (
          <div className="text-ink-muted text-small">No SHAP values available.</div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {shapEntries.map(([feature, value]) => {
              const pct = (Math.abs(value) / maxAbs) * 100
              const positive = value > 0
              return (
                <div key={feature}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-ink-secondary font-mono">{feature.replace(/_/g, ' ')}</span>
                    <span className={`font-semibold ${positive ? 'text-red-600' : 'text-green-600'}`}>
                      {positive ? '↑' : '↓'} {Math.abs(value).toFixed(4)}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${positive ? 'bg-danger-500' : 'bg-success-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
        {prediction.explanation_text && (
          <p className="mt-4 text-small text-ink-secondary border-t border-border-subtle pt-4">
            {prediction.explanation_text}
          </p>
        )}
      </div>
    </div>
  )
}

function ReportsTab({ appId, report }: { appId: string; report: Report | null }) {
  const [reports, setReports] = useState<Report[]>([])
  const [generating, setGenerating] = useState(false)
  const { success, error } = useToast()

  useEffect(() => {
    reportsApi.list(appId).then(r => setReports(r.items)).catch(() => {})
  }, [appId, report])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      await reportsApi.generate(appId)
      const r = await reportsApi.list(appId)
      setReports(r.items)
      success('Report generated.')
    } catch (err) {
      error(extractError(err))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div>
      <div className="mb-4">
        <Button onClick={handleGenerate} loading={generating}>Generate New Report</Button>
      </div>
      {reports.length === 0 ? (
        <div className="card flex items-center justify-center py-12 text-ink-muted text-small">
          No reports generated yet.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {reports.map(r => (
            <div key={r.id} className="card px-4 py-3 flex items-center gap-4">
              <span className="text-xl">📊</span>
              <div className="flex-1 min-w-0">
                <div className="text-small font-medium text-ink-primary">{r.filename}</div>
                <div className="text-[11px] text-ink-muted mt-0.5">
                  v{r.version} · {new Date(r.created_at).toLocaleString()}
                  {r.file_size_bytes && ` · ${(r.file_size_bytes / 1024).toFixed(0)} KB`}
                </div>
              </div>
              <span className={`badge ${r.status === 'complete' ? 'bg-success-50 text-green-700' : r.status === 'failed' ? 'bg-danger-50 text-red-700' : 'bg-warning-50 text-amber-700'}`}>
                {r.status}
              </span>
              {r.status === 'complete' && (
                <a
                  href={reportsApi.downloadUrl(r.id)}
                  download={r.filename}
                  className="btn btn-secondary btn-sm"
                  target="_blank" rel="noreferrer"
                >
                  Download
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
