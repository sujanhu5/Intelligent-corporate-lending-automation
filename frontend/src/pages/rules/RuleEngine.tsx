import { useEffect, useState, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { rulesApi } from '@/api/rules'
import type { Rule, RuleCreate } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Input, { Select, Textarea } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'
import Badge from '@/components/ui/Badge'
import { PageLoader } from '@/components/ui/Spinner'

const OPERATORS = [
  { value: 'gt',          label: '> Greater than' },
  { value: 'gte',         label: '>= Greater or equal' },
  { value: 'lt',          label: '< Less than' },
  { value: 'lte',         label: '<= Less or equal' },
  { value: 'eq',          label: '= Equal to' },
  { value: 'neq',         label: '≠ Not equal to' },
  { value: 'is_positive', label: 'Is positive (> 0)' },
  { value: 'is_negative', label: 'Is negative (< 0)' },
]

const CATEGORIES = [
  { value: 'liquidity',     label: 'Liquidity' },
  { value: 'solvency',      label: 'Solvency' },
  { value: 'profitability', label: 'Profitability' },
  { value: 'cash_flow',     label: 'Cash Flow' },
  { value: 'leverage',      label: 'Leverage' },
  { value: 'coverage',      label: 'Coverage' },
  { value: 'qualitative',   label: 'Qualitative' },
  { value: 'regulatory',    label: 'Regulatory' },
]

// Must match the ratio names produced by backend/ratios/calculator.py —
// a rule referencing an unknown metric is silently skipped at evaluation.
const RATIO_FIELDS = [
  'current_ratio','quick_ratio','current_asset_ratio','working_capital',
  'debt_equity_ratio','debt_ratio','financial_leverage',
  'gross_profit_margin','operating_margin','net_profit_margin','ebitda_margin',
  'return_on_assets','return_on_equity',
  'interest_coverage_ratio','debt_service_coverage_ratio',
  'cash_flow_ratio','operating_cash_flow_ratio',
  'asset_turnover','inventory_turnover','receivable_turnover',
].map(v => ({ value: v, label: v.replace(/_/g, ' ') }))

const ACTIONS = [
  { value: 'reject',        label: 'Reject application' },
  { value: 'manual_review', label: 'Flag for manual review' },
  { value: 'flag',          label: 'Flag only' },
]

const INDUSTRIES = [
  { value: '',               label: 'All Industries (Global)' },
  { value: 'manufacturing',  label: 'Manufacturing' },
  { value: 'retail',         label: 'Retail' },
  { value: 'wholesale',      label: 'Wholesale' },
  { value: 'services',       label: 'Services' },
  { value: 'technology',     label: 'Technology' },
  { value: 'healthcare',     label: 'Healthcare' },
  { value: 'construction',   label: 'Construction' },
  { value: 'real_estate',    label: 'Real Estate' },
  { value: 'agriculture',    label: 'Agriculture' },
  { value: 'financial',      label: 'Financial Services' },
  { value: 'hospitality',    label: 'Hospitality' },
  { value: 'transportation', label: 'Transportation' },
  { value: 'energy',         label: 'Energy' },
  { value: 'other',          label: 'Other' },
]

const MANDATORY_OPS = ['lt','lte','gt','gte','eq','neq']

export default function RuleEngine() {
  const [rules, setRules] = useState<Rule[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Rule | null>(null)
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<RuleCreate>()
  const watchOp = watch('operator')

  const needsThreshold = watchOp && MANDATORY_OPS.includes(watchOp)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await rulesApi.list()
      setRules(res.items)
    } catch (err) {
      error(extractError(err))
    } finally {
      setLoading(false)
    }
  }, [error])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditTarget(null); reset({}); setModalOpen(true) }
  const openEdit = (r: Rule) => {
    setEditTarget(r)
    reset({
      name: r.name, description: r.description ?? '', metric_field: r.metric_field,
      operator: r.operator, threshold: r.threshold ?? undefined, action: r.action,
      is_mandatory: r.is_mandatory, category: r.category, priority: r.priority,
      industry: r.industry ?? undefined,
    })
    setModalOpen(true)
  }

  const onSubmit = async (values: RuleCreate) => {
    if (!values.industry) values.industry = null
    setSaving(true)
    try {
      if (editTarget) {
        await rulesApi.update(editTarget.id, values)
        success('Rule updated.')
      } else {
        await rulesApi.create(values)
        success('Rule created.')
      }
      setModalOpen(false)
      load()
    } catch (err) {
      error(extractError(err))
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (r: Rule) => {
    try {
      await rulesApi.toggle(r.id)
      success(`Rule ${r.is_active ? 'disabled' : 'enabled'}.`)
      load()
    } catch (err) {
      error(extractError(err))
    }
  }

  const handleDelete = async (r: Rule) => {
    try {
      await rulesApi.delete(r.id)
      success('Rule deleted.')
      load()
    } catch (err) {
      error(extractError(err))
    }
  }

  if (loading) return <PageLoader />

  const mandatory = rules.filter(r => r.is_mandatory)
  const advisory  = rules.filter(r => !r.is_mandatory)

  return (
    <div>
      <PageHeader
        title="Rule Engine"
        subtitle="Configure mandatory and advisory banking rules for credit evaluation."
        actions={<Button onClick={openCreate}>+ New Rule</Button>}
      />

      {[
        { label: 'Mandatory Rules', items: mandatory, desc: 'Failure immediately rejects the application and skips ML.', tag: 'REJECT' },
        { label: 'Advisory Rules',  items: advisory,  desc: 'Failure flags manual review but ML still runs.', tag: 'REVIEW' },
      ].map(group => (
        <div key={group.label} className="mb-8">
          <div className="mb-3 flex items-start gap-3">
            <div className={`mt-0.5 px-2.5 py-1 rounded-full text-[9px] font-extrabold font-mono uppercase tracking-wider
              ${group.tag === 'REJECT' ? 'gradient-orange text-white shadow-orange' : 'bg-surface-2 text-ink-secondary border border-border-subtle'}`}>
              {group.tag}
            </div>
            <div>
              <h3 className="text-h4 text-ink-primary font-mono">{group.label}</h3>
              <p className="text-small text-ink-secondary mt-0.5">{group.desc}</p>
            </div>
          </div>
          {group.items.length === 0 ? (
            <div className="card flex items-center justify-center py-10 text-ink-muted text-small">
              No {group.label.toLowerCase()} configured.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-md border border-border-subtle shadow-xs">
              <table className="w-full border-collapse text-small">
                <thead className="bg-surface-2">
                  <tr>
                    {['Rule Name', 'Field', 'Condition', 'Category', 'Industry', 'Priority', 'Status', ''].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-surface-1 divide-y divide-border-subtle">
                  {group.items.map(r => (
                    <tr key={r.id} className={r.is_active ? '' : 'opacity-50'}>
                      <td className="px-4 py-3 font-medium text-ink-primary">{r.name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-ink-secondary">{r.metric_field}</td>
                      <td className="px-4 py-3 text-ink-secondary">
                        {r.operator.replace(/_/g, ' ')}
                        {r.threshold != null && <span className="font-mono ml-1">{r.threshold}</span>}
                      </td>
                      <td className="px-4 py-3">{r.category}</td>
                      <td className="px-4 py-3 text-xs text-ink-secondary capitalize">{r.industry?.replace(/_/g, ' ') ?? 'All'}</td>
                      <td className="px-4 py-3 tabular text-right">{r.priority}</td>
                      <td className="px-4 py-3">
                        <Badge variant={r.is_active ? 'approved' : 'draft'} dot>
                          {r.is_active ? 'Active' : 'Disabled'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <button onClick={() => openEdit(r)} className="text-xs text-ink-secondary hover:text-primary transition-colors">Edit</button>
                          <button onClick={() => handleToggle(r)} className="text-xs text-ink-secondary hover:text-primary transition-colors">
                            {r.is_active ? 'Disable' : 'Enable'}
                          </button>
                          <button onClick={() => handleDelete(r)} className="text-xs text-ink-secondary hover:text-danger-500 transition-colors">Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}

      <Modal
        open={modalOpen}
        title={editTarget ? 'Edit Rule' : 'New Rule'}
        onClose={() => setModalOpen(false)}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button form="rule-form" type="submit" loading={saving}>
              {editTarget ? 'Save Changes' : 'Create Rule'}
            </Button>
          </>
        }
      >
        <form id="rule-form" onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input label="Rule Name" error={errors.name?.message}
            {...register('name', { required: 'Required.' })} />

          <Textarea label="Description (optional)" rows={2} {...register('description')} />

          <div className="grid grid-cols-2 gap-4">
            <Select label="Ratio Field" options={RATIO_FIELDS} placeholder="Select field…"
              error={errors.metric_field?.message}
              {...register('metric_field', { required: 'Required.' })} />
            <Select label="Operator" options={OPERATORS} placeholder="Select operator…"
              error={errors.operator?.message}
              {...register('operator', { required: 'Required.' })} />
          </div>

          {needsThreshold && (
            <Input label="Threshold" type="number" step="any"
              error={errors.threshold?.message}
              {...register('threshold', {
                valueAsNumber: true,
                validate: v => (!needsThreshold || v != null) || 'Required for this operator.',
              })} />
          )}

          <div className="grid grid-cols-2 gap-4">
            <Select label="Category" options={CATEGORIES} placeholder="Select…"
              error={errors.category?.message}
              {...register('category', { required: 'Required.' })} />
            <Select label="Action on failure" options={ACTIONS} placeholder="Select…"
              error={errors.action?.message}
              {...register('action', { required: 'Required.' })} />
          </div>

          <Select label="Industry Scope" options={INDUSTRIES} placeholder="All Industries"
            {...register('industry')} />

          <Input label="Priority (lower = first)" type="number"
            defaultValue={10} {...register('priority', { valueAsNumber: true })} />

          <div className="flex items-center gap-3">
            <input type="checkbox" id="mandatory" {...register('is_mandatory')} className="w-4 h-4 accent-primary" />
            <label htmlFor="mandatory" className="text-small text-ink-primary">
              Mandatory — failure immediately rejects application
            </label>
          </div>
        </form>
      </Modal>
    </div>
  )
}
