import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuthStore } from '@/store/auth'
import { authApi, type CompanyRegisterPayload } from '@/api/auth'
import { extractError } from '@/api/client'
import { useToast } from '@/components/ui/Toast'
import ThemeToggle from '@/components/ui/ThemeToggle'

const COMPANY_TYPES = [
  { value: 'private_limited', label: 'Private Limited' },
  { value: 'public_limited', label: 'Public Limited' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'sole_proprietorship', label: 'Sole Proprietorship' },
  { value: 'llp', label: 'LLP' },
  { value: 'other', label: 'Other' },
]

const INDUSTRIES = [
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'retail', label: 'Retail' },
  { value: 'wholesale', label: 'Wholesale' },
  { value: 'services', label: 'Services' },
  { value: 'technology', label: 'Technology' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'construction', label: 'Construction' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'agriculture', label: 'Agriculture' },
  { value: 'financial', label: 'Financial Services' },
  { value: 'hospitality', label: 'Hospitality' },
  { value: 'transportation', label: 'Transportation' },
  { value: 'energy', label: 'Energy' },
  { value: 'other', label: 'Other' },
]

type Step = 1 | 2 | 3

export default function Register() {
  const navigate = useNavigate()
  const { success, error: showError } = useToast()
  const [step, setStep] = useState<Step>(1)
  const [serverError, setServerError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const { register, handleSubmit, formState: { errors }, trigger, getValues } = useForm<CompanyRegisterPayload>({
    defaultValues: { company_type: 'private_limited' },
  })

  const goToStep = async (target: Step) => {
    if (target > step) {
      const fieldsToValidate = step === 1
        ? ['company_name', 'registration_number', 'industry', 'company_type', 'registered_address'] as const
        : step === 2
        ? ['full_name', 'email', 'password'] as const
        : [] as const
      if (fieldsToValidate.length > 0) {
        const valid = await trigger(fieldsToValidate as any)
        if (!valid) return
      }
    }
    setStep(target)
  }

  const onSubmit = async (values: CompanyRegisterPayload) => {
    setServerError('')
    setSubmitting(true)
    try {
      const data = await authApi.register(values)
      localStorage.setItem('access_token', data.access_token)

      useAuthStore.getState().initialize()
      success('Company registered successfully! Welcome to CLA.')
      navigate('/portal')
    } catch (err) {
      setServerError(extractError(err))
    } finally {
      setSubmitting(false)
    }
  }

  const STEPS = [
    { n: 1, label: 'Company Details' },
    { n: 2, label: 'Account Setup' },
    { n: 3, label: 'Review & Submit' },
  ]

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <header className="h-14 flex items-center justify-between px-6 border-b border-border-subtle flex-shrink-0">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md gradient-orange flex items-center justify-center flex-shrink-0">
            <span className="text-white font-extrabold text-[10px] font-mono">CL</span>
          </div>
          <span className="text-xs font-bold text-ink-primary font-mono tracking-wide">CORPORATE LENDING AUTOMATION</span>
        </Link>
        <ThemeToggle variant="icon" />
      </header>

      <div className="flex-1 flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-[560px]">
          <div className="mb-6">
            <Link to="/login" className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-primary mb-4 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              Back to sign in
            </Link>
            <h1 className="text-h3 text-ink-primary">Register Your Company</h1>
            <p className="text-small text-ink-secondary mt-1.5">
              Complete the form below to create your company account and start applying for loans.
            </p>
          </div>

          {/* Step indicator */}
          <div className="flex items-center gap-1 mb-6">
            {STEPS.map((s, i) => (
              <div key={s.n} className="flex items-center flex-1">
                <div className="flex items-center gap-1.5 flex-1">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold font-mono flex-shrink-0
                    ${step >= s.n ? 'gradient-orange text-white' : 'bg-surface-2 text-ink-muted border border-border-subtle'}`}>
                    {step > s.n ? '✓' : s.n}
                  </div>
                  <span className={`text-[10px] font-semibold whitespace-nowrap ${step >= s.n ? 'text-ink-primary' : 'text-ink-muted'}`}>{s.label}</span>
                </div>
                {i < STEPS.length - 1 && <div className={`w-4 h-0.5 mx-1 rounded flex-shrink-0 ${step > s.n ? 'gradient-orange' : 'bg-border-subtle'}`} />}
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="card p-6" noValidate>
            {/* Step 1: Company Details */}
            {step === 1 && (
              <div className="flex flex-col gap-4">
                <div>
                  <label className="label">Company Name</label>
                  <input className={`input ${errors.company_name ? 'input-error' : ''}`} placeholder="Acme Industries Pvt. Ltd."
                    {...register('company_name', { required: 'Company name is required.', minLength: { value: 2, message: 'Min 2 characters.' } })} />
                  {errors.company_name && <span className="field-error">{errors.company_name.message}</span>}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">Registration Number</label>
                    <input className={`input ${errors.registration_number ? 'input-error' : ''}`} placeholder="U12345MH2020PTC123456"
                      {...register('registration_number', { required: 'Registration number is required.' })} />
                    {errors.registration_number && <span className="field-error">{errors.registration_number.message}</span>}
                  </div>
                  <div>
                    <label className="label">Company Type</label>
                    <select className="input" {...register('company_type')}>
                      {COMPANY_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="label">Industry Sector</label>
                  <select className={`input ${errors.industry ? 'input-error' : ''}`}
                    {...register('industry', { required: 'Select an industry.' })}>
                    <option value="">Select industry...</option>
                    {INDUSTRIES.map(i => <option key={i.value} value={i.value}>{i.label}</option>)}
                  </select>
                  {errors.industry && <span className="field-error">{errors.industry.message}</span>}
                </div>

                <div>
                  <label className="label">Registered Address</label>
                  <textarea className={`input min-h-[72px] ${errors.registered_address ? 'input-error' : ''}`} placeholder="123 Business Park, Industrial Area..."
                    {...register('registered_address', { required: 'Address is required.' })} />
                  {errors.registered_address && <span className="field-error">{errors.registered_address.message}</span>}
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="label">City</label>
                    <input className="input" placeholder="Mumbai" {...register('city')} />
                  </div>
                  <div>
                    <label className="label">State</label>
                    <input className="input" placeholder="Maharashtra" {...register('state')} />
                  </div>
                  <div>
                    <label className="label">Postal Code</label>
                    <input className="input" placeholder="400001" {...register('postal_code')} />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label">Annual Turnover (INR)</label>
                    <input className="input" type="number" step="any" placeholder="50000000" {...register('annual_turnover', { valueAsNumber: true })} />
                  </div>
                  <div>
                    <label className="label">Number of Employees</label>
                    <input className="input" type="number" placeholder="250" {...register('number_of_employees', { valueAsNumber: true })} />
                  </div>
                </div>

                <div className="flex justify-end pt-3 border-t border-border-subtle">
                  <button type="button" onClick={() => goToStep(2)} className="btn btn-primary">
                    Next: Account Setup
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Account Setup */}
            {step === 2 && (
              <div className="flex flex-col gap-4">
                <div>
                  <label className="label">Your Full Name</label>
                  <input className={`input ${errors.full_name ? 'input-error' : ''}`} placeholder="Rajesh Kumar"
                    {...register('full_name', { required: 'Full name is required.', minLength: { value: 2, message: 'Min 2 characters.' } })} />
                  {errors.full_name && <span className="field-error">{errors.full_name.message}</span>}
                </div>

                <div>
                  <label className="label">Email Address</label>
                  <input className={`input ${errors.email ? 'input-error' : ''}`} type="email" placeholder="rajesh@acmeindustries.com"
                    {...register('email', {
                      required: 'Email is required.',
                      pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email.' },
                    })} />
                  {errors.email && <span className="field-error">{errors.email.message}</span>}
                </div>

                <div>
                  <label className="label">Password</label>
                  <input className={`input ${errors.password ? 'input-error' : ''}`} type="password" placeholder="Min 8 chars, 1 uppercase, 1 number"
                    {...register('password', {
                      required: 'Password is required.',
                      minLength: { value: 8, message: 'Minimum 8 characters.' },
                    })} />
                  {errors.password && <span className="field-error">{errors.password.message}</span>}
                </div>

                <div>
                  <label className="label">Contact Phone</label>
                  <input className="input" type="tel" placeholder="+91 98765 43210" {...register('contact_phone')} />
                </div>

                <div>
                  <label className="label">Company Website</label>
                  <input className="input" placeholder="https://www.acmeindustries.com" {...register('website')} />
                </div>

                <div className="flex justify-between pt-3 border-t border-border-subtle">
                  <button type="button" onClick={() => setStep(1)} className="btn btn-secondary">Back</button>
                  <button type="button" onClick={() => goToStep(3)} className="btn btn-primary">Next: Review</button>
                </div>
              </div>
            )}

            {/* Step 3: Review & Submit */}
            {step === 3 && (
              <div className="flex flex-col gap-5">
                <div>
                  <h3 className="text-sm font-bold text-ink-primary mb-3">Company Information</h3>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    <ReviewRow label="Company" value={getValues('company_name')} />
                    <ReviewRow label="Registration No." value={getValues('registration_number')} />
                    <ReviewRow label="Type" value={COMPANY_TYPES.find(t => t.value === getValues('company_type'))?.label} />
                    <ReviewRow label="Industry" value={INDUSTRIES.find(i => i.value === getValues('industry'))?.label} />
                    <ReviewRow label="City" value={getValues('city')} />
                    <ReviewRow label="State" value={getValues('state')} />
                  </div>
                </div>

                <div className="border-t border-border-subtle pt-4">
                  <h3 className="text-sm font-bold text-ink-primary mb-3">Account Details</h3>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    <ReviewRow label="Name" value={getValues('full_name')} />
                    <ReviewRow label="Email" value={getValues('email')} />
                    <ReviewRow label="Phone" value={getValues('contact_phone')} />
                  </div>
                </div>

                <div className="border-t border-border-subtle pt-4">
                  <div className="bg-cr-50 rounded-lg p-4">
                    <p className="text-xs text-ink-secondary">
                      After registration, you can upload your company's annual report from the portal.
                      The system will automatically detect and extract financial statements (Balance Sheet,
                      Profit & Loss, Cash Flow) from the report.
                    </p>
                  </div>
                </div>

                {serverError && (
                  <div className="bg-danger-50 border border-danger-500/30 text-red-700 rounded-lg px-3 py-2.5 text-small">
                    {serverError}
                  </div>
                )}

                <div className="flex justify-between pt-3 border-t border-border-subtle">
                  <button type="button" onClick={() => setStep(2)} className="btn btn-secondary">Back</button>
                  <button type="submit" disabled={submitting} className="btn btn-primary btn-lg">
                    {submitting ? 'Registering...' : 'Register Company'}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>

      <footer className="flex items-center justify-between px-6 py-4 border-t border-border-subtle text-[11px] text-ink-muted font-mono flex-shrink-0">
        <span>&copy; 2026 Corporate Lending Automation</span>
        <div className="flex items-center gap-4">
          <span>v1.0.0</span>
        </div>
      </footer>
    </div>
  )
}

function ReviewRow({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <span className="text-ink-muted text-xs">{label}:</span>
      <span className="ml-1.5 text-ink-primary font-medium text-xs">{value || '—'}</span>
    </div>
  )
}
