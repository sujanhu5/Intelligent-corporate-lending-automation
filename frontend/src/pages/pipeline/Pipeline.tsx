import { useEffect, useState, useCallback } from 'react'
import { applicationsApi } from '@/api/applications'
import { pipelineApi } from '@/api/pipeline'
import type {
  Application,
  PipelineRunResponse,
  BatchPipelineResponse,
} from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import Button from '@/components/ui/Button'
import Badge from '@/components/ui/Badge'
import { PageLoader } from '@/components/ui/Spinner'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'

// ---------------------------------------------------------------------------
// Stage badge
// ---------------------------------------------------------------------------
function StageBadge({ status }: { status: string }) {
  if (status === 'completed') return <Badge variant="approved" dot={false}>done</Badge>
  if (status === 'skipped')  return <Badge variant="info" dot={false}>skipped</Badge>
  if (status === 'failed')   return <Badge variant="rejected" dot={false}>failed</Badge>
  return <Badge variant="draft" dot={false}>{status}</Badge>
}

// ---------------------------------------------------------------------------
// Run result panel
// ---------------------------------------------------------------------------
function RunResultPanel({
  result,
  onClose,
}: {
  result: PipelineRunResponse
  onClose: () => void
}) {
  const anyFailed = !!result.failed_stage
  return (
    <div className={`rounded border p-4 mb-6 ${anyFailed ? 'border-red-300 bg-red-50 dark:bg-red-950/20' : 'border-green-300 bg-green-50 dark:bg-green-950/20'}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="font-semibold text-sm mb-1">
            {result.application_number} — {anyFailed ? 'Pipeline stopped' : 'Pipeline complete'}
          </div>
          <div className="text-xs text-ink-secondary mb-3">{result.summary}</div>
          <div className="flex flex-wrap gap-1 mb-3">
            {result.stages.map(s => (
              <span key={s.stage} className="inline-flex items-center gap-1 text-xs bg-surface-2 border border-border-subtle rounded px-2 py-0.5">
                <span className="capitalize">{s.stage}</span>
                <StageBadge status={s.status} />
                <span className="text-ink-muted">{s.duration_seconds.toFixed(1)}s</span>
              </span>
            ))}
          </div>
          <div className="flex gap-4 text-xs text-ink-secondary">
            <span>Total: <strong>{result.total_duration_seconds.toFixed(1)}s</strong></span>
            <span>Decision: <strong>{result.final_decision.replace('_', ' ')}</strong></span>
            {result.risk_score != null && (
              <span>Risk score: <strong>{result.risk_score.toFixed(1)}</strong></span>
            )}
          </div>
        </div>
        <button onClick={onClose} className="text-ink-muted hover:text-ink-primary text-lg leading-none">×</button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Application row
// ---------------------------------------------------------------------------
function AppRow({
  app,
  onRun,
  running,
}: {
  app: Application
  onRun: (id: string) => void
  running: boolean
}) {
  const pipeline = app.pipeline
  const stages: [string, boolean][] = [
    ['OCR', pipeline.ocr_completed],
    ['Ratios', pipeline.ratios_calculated],
    ['Rules', pipeline.rules_evaluated],
    ['ML', pipeline.ml_predicted],
    ['Report', pipeline.report_generated],
  ]

  const statusVariant = (status: string): 'draft' | 'info' | 'approved' | 'rejected' | 'review' => {
    if (status === 'approved') return 'approved'
    if (status === 'rejected') return 'rejected'
    if (status === 'manual_review') return 'review'
    if (['submitted', 'under_review', 'ocr_processing', 'ocr_complete',
         'ratio_calculated', 'rule_evaluated', 'ml_predicted', 'report_generated'].includes(status))
      return 'info'
    return 'draft'
  }

  const isDecided = ['approved', 'rejected', 'manual_review', 'withdrawn'].includes(app.status)
  const canRun = app.status !== 'draft' && !isDecided

  return (
    <tr className="hover:bg-surface-2 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-ink-secondary">{app.application_number}</td>
      <td className="px-4 py-3 text-small font-medium text-ink-primary">{app.company?.name || '—'}</td>
      <td className="px-4 py-3">
        <Badge variant={statusVariant(app.status)} dot={false}>
          {app.status.replace('_', ' ')}
        </Badge>
      </td>
      <td className="px-4 py-3">
        <div className="flex gap-1">
          {stages.map(([label, done]) => (
            <span
              key={label}
              title={label}
              className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                done
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-surface-2 text-ink-muted border border-border-subtle'
              }`}
            >
              {label}
            </span>
          ))}
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-ink-secondary">
        {app.risk_score != null ? app.risk_score.toFixed(1) : '—'}
      </td>
      <td className="px-4 py-3">
        {!isDecided && (
          <Button
            size="sm"
            variant={canRun ? 'primary' : 'secondary'}
            loading={running}
            onClick={() => onRun(app.id)}
            disabled={running || app.status === 'draft'}
          >
            {app.status === 'draft' ? 'Not submitted' : 'Run'}
          </Button>
        )}
        {isDecided && (
          <span className="text-xs text-ink-muted italic">Decided</span>
        )}
      </td>
    </tr>
  )
}

// ---------------------------------------------------------------------------
// Batch result panel
// ---------------------------------------------------------------------------
function BatchResultPanel({
  result,
  onClose,
}: {
  result: BatchPipelineResponse
  onClose: () => void
}) {
  return (
    <div className="rounded border border-border p-4 mb-6 bg-surface-1">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="font-semibold text-sm mb-2">
            Batch run complete — {result.requested} applications processed in {result.duration_seconds.toFixed(1)}s
          </div>
          <div className="flex gap-4 text-xs mb-3">
            <span className="text-green-700 dark:text-green-400">✓ {result.succeeded} succeeded</span>
            <span className="text-red-700 dark:text-red-400">✗ {result.failed} failed</span>
            <span className="text-ink-muted">↷ {result.skipped} skipped</span>
          </div>
          {result.items.filter(i => i.status !== 'succeeded').length > 0 && (
            <div className="space-y-1">
              {result.items.filter(i => i.status !== 'succeeded').map(item => (
                <div key={item.application_id} className="text-xs text-red-700 dark:text-red-400">
                  {item.application_number}: {item.detail}
                </div>
              ))}
            </div>
          )}
        </div>
        <button onClick={onClose} className="text-ink-muted hover:text-ink-primary text-lg leading-none">×</button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function Pipeline() {
  const [apps, setApps] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [batchRunning, setBatchRunning] = useState(false)
  const [runResult, setRunResult] = useState<PipelineRunResponse | null>(null)
  const [batchResult, setBatchResult] = useState<BatchPipelineResponse | null>(null)
  const { success, error } = useToast()

  const loadApps = useCallback(() => {
    setLoading(true)
    applicationsApi.list({ page_size: 50 })
      .then(r => setApps(r.items))
      .catch(err => error(extractError(err)))
      .finally(() => setLoading(false))
  }, [error])

  useEffect(() => { loadApps() }, [loadApps])

  const handleRun = async (appId: string) => {
    setRunningId(appId)
    setRunResult(null)
    setBatchResult(null)
    try {
      const result = await pipelineApi.run(appId)
      setRunResult(result)
      success(`Pipeline complete for ${result.application_number}`)
      loadApps()
    } catch (err) {
      error(extractError(err))
    } finally {
      setRunningId(null)
    }
  }

  const handleBatch = async () => {
    setBatchRunning(true)
    setRunResult(null)
    setBatchResult(null)
    try {
      const result = await pipelineApi.runBatch({ limit: 25 })
      setBatchResult(result)
      success(`Batch: ${result.succeeded}/${result.requested} succeeded`)
      loadApps()
    } catch (err) {
      error(extractError(err))
    } finally {
      setBatchRunning(false)
    }
  }

  const pending = apps.filter(a =>
    !['draft', 'approved', 'rejected', 'manual_review', 'withdrawn'].includes(a.status)
  )
  const decided = apps.filter(a =>
    ['approved', 'rejected', 'manual_review'].includes(a.status)
  )

  if (loading) return <PageLoader />

  return (
    <div>
      <PageHeader
        title="Pipeline Orchestrator"
        subtitle="Run the full credit-assessment pipeline for submitted applications."
        actions={
          <Button
            onClick={handleBatch}
            loading={batchRunning}
            disabled={pending.length === 0 || batchRunning}
          >
            Run Batch ({pending.length})
          </Button>
        }
      />

      {runResult && (
        <RunResultPanel result={runResult} onClose={() => setRunResult(null)} />
      )}
      {batchResult && (
        <BatchResultPanel result={batchResult} onClose={() => setBatchResult(null)} />
      )}

      {/* Stage legend */}
      <div className="flex gap-3 mb-4 text-xs text-ink-secondary">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm bg-green-100 border border-green-300" /> Stage complete
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm bg-surface-2 border border-border-subtle" /> Pending
        </span>
      </div>

      {/* Pending applications */}
      <div className="card overflow-hidden mb-6">
        <div className="px-4 py-3 border-b border-border-subtle bg-surface-2">
          <h3 className="text-small font-semibold text-ink-primary">
            In Pipeline ({pending.length})
          </h3>
        </div>
        {pending.length === 0 ? (
          <div className="px-4 py-8 text-center text-ink-muted text-small">
            No applications currently in the pipeline.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-small">
              <thead className="bg-surface-2">
                <tr>
                  {['Ref', 'Company', 'Status', 'Stages', 'Risk', ''].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {pending.map(app => (
                  <AppRow
                    key={app.id}
                    app={app}
                    onRun={handleRun}
                    running={runningId === app.id}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Decided applications */}
      {decided.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-border-subtle bg-surface-2">
            <h3 className="text-small font-semibold text-ink-primary">
              Decided ({decided.length})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-small">
              <thead className="bg-surface-2">
                <tr>
                  {['Ref', 'Company', 'Decision', 'Stages', 'Risk', ''].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {decided.map(app => (
                  <AppRow
                    key={app.id}
                    app={app}
                    onRun={handleRun}
                    running={runningId === app.id}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
