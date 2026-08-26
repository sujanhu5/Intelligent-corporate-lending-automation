import { useEffect, useState } from 'react'
import { portalApi } from '@/api/portal'
import { PageLoader } from '@/components/ui/Spinner'

interface CompanyProfile {
  id: string
  name: string
  registration_number: string
  company_type: string | null
  industry: string | null
  status: string
  incorporation_date: string | null
  registered_address: string | null
  city: string | null
  state: string | null
  postal_code: string | null
  contact_email: string | null
  contact_phone: string | null
  website: string | null
  annual_turnover: number | null
  number_of_employees: number | null
  created_at: string
}

export default function PortalCompany() {
  const [company, setCompany] = useState<CompanyProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    portalApi.company()
      .then(setCompany)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <PageLoader />
  if (!company) return <div className="card p-8 text-center text-ink-muted">Company profile not available.</div>

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-h2 text-ink-primary">Company Profile</h1>
        <p className="text-small text-ink-secondary mt-1">Your company registration details</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-sm font-bold text-ink-primary mb-4 pb-3 border-b border-border-subtle">General Information</h3>
          <div className="flex flex-col gap-3">
            <Row label="Company Name" value={company.name} />
            <Row label="Registration Number" value={company.registration_number} mono />
            <Row label="Company Type" value={company.company_type?.replace(/_/g, ' ')} />
            <Row label="Industry" value={company.industry?.replace(/_/g, ' ')} />
            <Row label="Status" value={company.status?.replace(/_/g, ' ')} badge />
            <Row label="Incorporation Date" value={company.incorporation_date} />
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-sm font-bold text-ink-primary mb-4 pb-3 border-b border-border-subtle">Contact & Address</h3>
          <div className="flex flex-col gap-3">
            <Row label="Address" value={company.registered_address} />
            <Row label="City" value={company.city} />
            <Row label="State" value={company.state} />
            <Row label="Postal Code" value={company.postal_code} />
            <Row label="Email" value={company.contact_email} />
            <Row label="Phone" value={company.contact_phone} />
            <Row label="Website" value={company.website} />
          </div>
        </div>

        <div className="card p-6 lg:col-span-2">
          <h3 className="text-sm font-bold text-ink-primary mb-4 pb-3 border-b border-border-subtle">Financial Summary</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-ink-muted font-mono mb-1">Annual Turnover</div>
              <div className="text-lg font-extrabold text-ink-primary font-mono tabular">
                {company.annual_turnover ? `INR ${company.annual_turnover.toLocaleString()}` : '—'}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-ink-muted font-mono mb-1">Employees</div>
              <div className="text-lg font-extrabold text-ink-primary font-mono tabular">
                {company.number_of_employees?.toLocaleString() ?? '—'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value, mono, badge }: { label: string; value?: string | null; mono?: boolean; badge?: boolean }) {
  return (
    <div className="flex justify-between items-start">
      <span className="text-xs text-ink-muted flex-shrink-0">{label}</span>
      {badge ? (
        <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wide
          ${value === 'active' ? 'bg-green-100 text-green-800' : value === 'under review' ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-700'}`}>
          {value ?? '—'}
        </span>
      ) : (
        <span className={`text-xs font-medium text-ink-primary text-right max-w-[60%] ${mono ? 'font-mono' : ''}`}>
          {value ?? '—'}
        </span>
      )}
    </div>
  )
}
