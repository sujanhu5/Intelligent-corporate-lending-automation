import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { applicationsApi } from '@/api/applications'
import { companiesApi } from '@/api/companies'
import type { ApplicationCreate, Company } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import Button from '@/components/ui/Button'
import Input, { Select, Textarea } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'

const PURPOSES = [
  { value: 'working_capital',     label: 'Working Capital' },
  { value: 'capital_expenditure', label: 'Capital Expenditure' },
  { value: 'debt_refinancing',    label: 'Debt Refinancing' },
  { value: 'expansion',           label: 'Expansion' },
  { value: 'acquisition',         label: 'Acquisition' },
  { value: 'trade_finance',       label: 'Trade Finance' },
  { value: 'other',               label: 'Other' },
]

export default function NewApplication() {
  const navigate = useNavigate()
  const location = useLocation()
  const [companies, setCompanies] = useState<Company[]>([])
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()

  const { register, handleSubmit, formState: { errors } } = useForm<ApplicationCreate>({
    defaultValues: { company_id: (location.state as { company_id?: string })?.company_id ?? '' },
  })

  useEffect(() => {
    companiesApi.list({ page_size: 200, status: 'active' }).then(r => setCompanies(r.items))
  }, [])

  const onSubmit = async (values: ApplicationCreate) => {
    setSaving(true)
    try {
      const app = await applicationsApi.create(values)
      success(`Application ${app.application_number} created.`)
      navigate(`/applications/${app.id}`)
    } catch (err) {
      error(extractError(err))
    } finally {
      setSaving(false)
    }
  }

  const companyOptions = companies.map(c => ({ value: c.id, label: c.name }))

  return (
    <div className="max-w-2xl">
      <PageHeader
        title="New Application"
        subtitle="Submit a corporate credit facility request."
        breadcrumb={[
          { label: 'Applications', href: '/applications' },
          { label: 'New Application' },
        ]}
      />

      <form onSubmit={handleSubmit(onSubmit)} className="card p-6 flex flex-col gap-5">
        <Select
          label="Company"
          options={companyOptions}
          placeholder="Select company…"
          error={errors.company_id?.message}
          {...register('company_id', { required: 'Select a company.' })}
        />

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Loan Amount Requested (RM)"
            type="number"
            step="any"
            placeholder="e.g. 1200000"
            error={errors.loan_amount_requested?.message}
            {...register('loan_amount_requested', {
              required: 'Required.',
              valueAsNumber: true,
              min: { value: 10000, message: 'Minimum RM 10,000.' },
            })}
          />
          <Input
            label="Loan Tenure (months)"
            type="number"
            placeholder="e.g. 60"
            error={errors.loan_tenure_months?.message}
            {...register('loan_tenure_months', {
              required: 'Required.',
              valueAsNumber: true,
              min: { value: 1, message: 'Minimum 1 month.' },
              max: { value: 360, message: 'Maximum 360 months.' },
            })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Loan Purpose"
            options={PURPOSES}
            placeholder="Select purpose…"
            error={errors.loan_purpose?.message}
            {...register('loan_purpose', { required: 'Required.' })}
          />
          <Input
            label="Interest Rate Requested (%)"
            type="number"
            step="0.01"
            placeholder="e.g. 4.50"
            {...register('interest_rate_requested', { valueAsNumber: true })}
          />
        </div>

        <Textarea
          label="Collateral Description"
          placeholder="Describe the security offered (property, equipment, etc.)…"
          {...register('collateral_description')}
        />

        <Input
          label="Collateral Value (RM)"
          type="number"
          step="any"
          placeholder="Estimated market value"
          {...register('collateral_value', { valueAsNumber: true })}
        />

        <div className="flex justify-end gap-3 pt-2 border-t border-border-subtle">
          <Button variant="secondary" type="button" onClick={() => navigate('/applications')}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Create Application
          </Button>
        </div>
      </form>
    </div>
  )
}
