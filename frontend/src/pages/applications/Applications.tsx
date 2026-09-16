import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { applicationsApi } from '@/api/applications'
import type { Application } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import Table, { Pagination } from '@/components/ui/Table'
import Button from '@/components/ui/Button'
import { ApplicationStatusBadge } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'draft',           label: 'Draft' },
  { value: 'submitted',       label: 'Submitted' },
  { value: 'ocr_complete',    label: 'OCR Complete' },
  { value: 'ratio_calculated',label: 'Ratios Calculated' },
  { value: 'rule_evaluated',  label: 'Rules Evaluated' },
  { value: 'ml_predicted',    label: 'ML Predicted' },
  { value: 'report_generated',label: 'Report Generated' },
  { value: 'approved',        label: 'Approved' },
  { value: 'rejected',        label: 'Rejected' },
  { value: 'manual_review',   label: 'Manual Review' },
  { value: 'withdrawn',       label: 'Withdrawn' },
]

export default function Applications() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<Application[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState(searchParams.get('status') ?? '')
  const navigate = useNavigate()
  const { error } = useToast()
  const PAGE_SIZE = 20

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await applicationsApi.list({
        page, page_size: PAGE_SIZE, status: status || undefined,
      })
      setData(res.items); setTotal(res.total)
    } catch (err) {
      error(extractError(err))
    } finally {
      setLoading(false)
    }
  }, [page, status, error])

  useEffect(() => { load() }, [load])

  const handleStatus = (s: string) => {
    setStatus(s); setPage(1)
    if (s) setSearchParams({ status: s }); else setSearchParams({})
  }

  const columns = [
    {
      key: 'appno', header: 'Application No.',
      render: (a: Application) => (
        <span className="font-mono text-xs text-ink-secondary">{a.application_number}</span>
      ),
    },
    {
      key: 'company', header: 'Company',
      render: (a: Application) => (
        <div className="font-medium text-ink-primary">{a.company?.name ?? '—'}</div>
      ),
    },
    {
      key: 'amount', header: 'Amount (₹)', className: 'text-right',
      render: (a: Application) => (
        <span className="tabular">
          {a.loan_amount_requested.toLocaleString(undefined, { minimumFractionDigits: 0 })}
        </span>
      ),
    },
    {
      key: 'purpose', header: 'Purpose',
      render: (a: Application) => a.loan_purpose.replace(/_/g, ' '),
    },
    {
      key: 'tenure', header: 'Tenure', className: 'text-right',
      render: (a: Application) => `${a.loan_tenure_months}mo`,
    },
    {
      key: 'risk', header: 'Risk', className: 'text-right',
      render: (a: Application) => (
        <span className="tabular font-medium">
          {a.risk_score != null ? a.risk_score.toFixed(1) : '—'}
        </span>
      ),
    },
    {
      key: 'status', header: 'Status',
      render: (a: Application) => <ApplicationStatusBadge status={a.status} />,
    },
    {
      key: 'date', header: 'Date',
      render: (a: Application) => new Date(a.created_at).toLocaleDateString(),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Applications"
        subtitle="Manage corporate credit applications across all pipeline stages."
        actions={<Button onClick={() => navigate('/applications/new')}>+ New Application</Button>}
      />

      <div className="flex gap-2 mb-5 flex-wrap">
        {STATUS_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => handleStatus(opt.value)}
            className={`px-3 py-1.5 rounded-full text-[11px] font-bold font-mono uppercase tracking-wide transition-all
              ${status === opt.value
                ? 'gradient-orange text-white shadow-orange'
                : 'bg-surface-2 text-ink-secondary hover:bg-border-subtle border border-border-subtle'}`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <Table
        columns={columns}
        data={data}
        loading={loading}
        keyExtractor={a => a.id}
        onRowClick={a => navigate(`/applications/${a.id}`)}
        emptyTitle="No applications"
        emptyDescription="Create a new application to get started."
      />
      <Pagination
        page={page} pages={Math.ceil(total / PAGE_SIZE)} total={total}
        pageSize={PAGE_SIZE} onChange={setPage}
      />
    </div>
  )
}
