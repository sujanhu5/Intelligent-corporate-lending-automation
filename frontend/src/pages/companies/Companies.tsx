import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { companiesApi } from '@/api/companies'
import type { Company, CompanyCreate } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import Table, { Pagination } from '@/components/ui/Table'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Input, { Select } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'
import Badge from '@/components/ui/Badge'

const COMPANY_TYPES = [
  { value: 'private_limited',     label: 'Private Limited (Sdn Bhd)' },
  { value: 'public_limited',      label: 'Public Limited (Bhd)' },
  { value: 'partnership',         label: 'Partnership' },
  { value: 'sole_proprietorship', label: 'Sole Proprietorship' },
  { value: 'llp',                 label: 'Limited Liability Partnership' },
  { value: 'other',               label: 'Other' },
]

const INDUSTRIES = [
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

export default function Companies() {
  const [data, setData] = useState<Company[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Company | null>(null)
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()
  const { success, error } = useToast()
  const PAGE_SIZE = 15

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CompanyCreate>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await companiesApi.list({ page, page_size: PAGE_SIZE, search: search || undefined })
      setData(res.items)
      setTotal(res.total)
    } catch (err) {
      error(extractError(err))
    } finally {
      setLoading(false)
    }
  }, [page, search, error])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditTarget(null); reset({}); setModalOpen(true) }
  const openEdit = (c: Company) => {
    setEditTarget(c)
    reset({
      name: c.name, registration_number: c.registration_number, tax_id: c.tax_id ?? '',
      contact_email: c.contact_email, contact_phone: c.contact_phone ?? '',
      registered_address: c.registered_address, city: c.city ?? '', state: c.state ?? '',
      company_type: c.company_type ?? undefined, industry: c.industry ?? undefined,
      annual_turnover: c.annual_turnover ?? undefined, number_of_employees: c.number_of_employees ?? undefined,
    })
    setModalOpen(true)
  }

  const onSubmit = async (values: CompanyCreate) => {
    setSaving(true)
    try {
      if (editTarget) {
        await companiesApi.update(editTarget.id, values)
        success('Company updated.')
      } else {
        await companiesApi.create(values)
        success('Company created.')
      }
      setModalOpen(false)
      load()
    } catch (err) {
      error(extractError(err))
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      key: 'name', header: 'Company', className: 'font-medium',
      render: (c: Company) => (
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg gradient-orange flex items-center justify-center flex-shrink-0 shadow-orange">
            <span className="text-white font-extrabold text-[11px] font-mono">{c.name.slice(0, 2).toUpperCase()}</span>
          </div>
          <div>
            <div className="text-ink-primary font-medium">{c.name}</div>
            <div className="text-[11px] text-ink-muted font-mono">{c.registration_number}</div>
          </div>
        </div>
      ),
    },
    { key: 'industry', header: 'Industry', render: (c: Company) => (
      <span className="capitalize text-ink-secondary">{c.industry ? c.industry.replace(/_/g, ' ') : '—'}</span>
    )},
    { key: 'type', header: 'Type', render: (c: Company) => (
      <span className="capitalize text-ink-secondary">{c.company_type ? c.company_type.replace(/_/g, ' ') : '—'}</span>
    )},
    {
      key: 'turnover', header: 'Annual Turnover', className: 'text-right',
      render: (c: Company) => (
        <span className="font-mono font-semibold tabular text-ink-primary">
          {c.annual_turnover ? `RM ${(c.annual_turnover / 1_000_000).toFixed(2)}M` : '—'}
        </span>
      ),
    },
    {
      key: 'status', header: 'Status',
      render: (c: Company) => <Badge variant={c.status === 'active' ? 'approved' : 'draft'} dot>{c.status.replace(/_/g, ' ')}</Badge>,
    },
    {
      key: 'actions', header: '',
      render: (c: Company) => (
        <button
          onClick={e => { e.stopPropagation(); openEdit(c) }}
          className="text-xs font-mono font-semibold text-ink-secondary hover:text-primary transition-colors uppercase tracking-wide"
        >
          Edit
        </button>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Companies"
        subtitle="Manage corporate borrower profiles."
        actions={<Button onClick={openCreate}>+ New Company</Button>}
      />

      <div className="mb-4 flex gap-3">
        <input
          className="input max-w-xs"
          placeholder="Search companies…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
        />
      </div>

      <Table
        columns={columns}
        data={data}
        loading={loading}
        keyExtractor={c => c.id}
        onRowClick={c => navigate(`/companies/${c.id}`)}
        emptyTitle="No companies found"
        emptyDescription="Add a company to start a loan application."
      />
      <Pagination page={page} pages={Math.ceil(total / PAGE_SIZE)} total={total} pageSize={PAGE_SIZE} onChange={setPage} />

      <Modal
        open={modalOpen}
        title={editTarget ? 'Edit Company' : 'New Company'}
        onClose={() => setModalOpen(false)}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button form="company-form" type="submit" loading={saving}>
              {editTarget ? 'Save Changes' : 'Create Company'}
            </Button>
          </>
        }
      >
        <form id="company-form" onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <Input label="Company Name" error={errors.name?.message}
              {...register('name', { required: 'Required.' })} />
          </div>
          <Input label="Registration Number" error={errors.registration_number?.message}
            {...register('registration_number', { required: 'Required.' })} />
          <Input label="Tax ID" {...register('tax_id')} />
          <Select label="Company Type" options={COMPANY_TYPES} placeholder="Select type…" {...register('company_type')} />
          <Select label="Industry" options={INDUSTRIES} placeholder="Select industry…" {...register('industry')} />
          <div className="col-span-2">
            <Input label="Registered Address" {...register('registered_address', { required: 'Required.' })}
              error={errors.registered_address?.message} />
          </div>
          <Input label="City" {...register('city')} />
          <Input label="State" {...register('state')} />
          <Input label="Contact Email" type="email" error={errors.contact_email?.message}
            {...register('contact_email', { required: 'Required.' })} />
          <Input label="Contact Phone" {...register('contact_phone')} />
          <Input label="Annual Turnover (RM)" type="number" step="any"
            {...register('annual_turnover', { valueAsNumber: true })} />
          <Input label="Number of Employees" type="number"
            {...register('number_of_employees', { valueAsNumber: true })} />
        </form>
      </Modal>
    </div>
  )
}
