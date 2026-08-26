import { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuthStore } from '@/store/auth'
import { authApi, type CompanyRegisterPayload } from '@/api/auth'
import { client as apiClient, extractError } from '@/api/client'
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

const DOC_TYPES = [
  { value: 'balance_sheet', label: 'Balance Sheet' },
  { value: 'profit_loss', label: 'Profit & Loss Statement' },
  { value: 'cash_flow', label: 'Cash Flow Statement' },
  { value: 'auditor_report', label: 'Auditor Report' },
  { value: 'gst_report', label: 'GST Report' },
  { value: 'bank_statement', label: 'Bank Statement' },
  { value: 'other', label: 'Other Document' },
]

interface UploadedDoc {
  file: File
  type: string
  label: string
}

type Step = 1 | 2 | 3 | 4

export default function Register() {
  const navigate = useNavigate()
  const { success, error: showError } = useToast()
  const [step, setStep] = useState<Step>(1)
  const [serverError, setServerError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [documents, setDocuments] = useState<UploadedDoc[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedDocType, setSelectedDocType] = useState('balance_sheet')

  const { register, handleSubmit, formState: { errors }, trigger, getValues, watch } = useForm<CompanyRegisterPayload>({
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

  const handleFileAdd = () => {
    const files = fileInputRef.current?.files
    if (!files || files.length === 0) return
    const docLabel = DOC_TYPES.find(d => d.value === selectedDocType)?.label ?? selectedDocType
    const newDocs: UploadedDoc[] = Array.from(files).map(f => ({
      file: f,
      type: selectedDocType,
      label: docLabel,
    }))
    setDocuments(prev => [...prev, ...newDocs])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeDoc = (idx: number) => {
    setDocuments(prev => prev.filter((_, i) => i !== idx))
  }

  const onSubmit = async (values: CompanyRegisterPayload) => {
    setServerError('')
    setSubmitting(true)
    try {
      const data = await authApi.register(values)
      localStorage.setItem('access_token', data.access_token)

      if (documents.length > 0) {
        const appRes = await apiClient.post('/applications', {
          company_id: data.user.company_id,
          loan_amount_requested: values.annual_turnover || 1000000,
          loan_purpose: 'working_capital',
          loan_tenure_months: 12,
        })
        const appId = appRes.data.id

        for (const doc of documents) {
          const form = new FormData()
          form.append('file', doc.file)
          form.append('document_type', doc.type)
          await apiClient.post(`/documents/upload/${appId}`, form, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
        }

        await apiClient.post(`/applications/${appId}/submit`)
      }

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
    { n: 3, label: 'Documents' },
    { n: 4, label: 'Review & Submit' },
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
                  <button type="button" onClick={() => goToStep(3)} className="btn btn-primary">Next: Documents</button>
                </div>
              </div>
            )}

            {/* Step 3: Document Upload */}
            {step === 3 && (
              <div className="flex flex-col gap-4">
                <div>
                  <h3 className="text-sm font-bold text-ink-primary mb-1">Upload Financial Documents</h3>
                  <p className="text-xs text-ink-secondary mb-4">
                    Upload your company's financial statements. These will be processed automatically when your loan application is created.
                    You can skip this step and upload documents later from your portal.
                  </p>
                </div>

                <div className="flex items-end gap-3">
                  <div className="flex-1">
                    <label className="label">Document Type</label>
                    <select className="input" value={selectedDocType} onChange={e => setSelectedDocType(e.target.value)}>
                      {DOC_TYPES.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                    </select>
                  </div>
                  <div className="flex-1">
                    <label className="label">Select File (PDF)</label>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.PDF"
                      className="input text-xs file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-cr-50 file:text-primary hover:file:bg-cr-100 file:cursor-pointer"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleFileAdd}
                    className="btn btn-secondary flex-shrink-0 mb-px"
                  >
                    Add
                  </button>
                </div>

                {documents.length > 0 ? (
                  <div className="border border-border-subtle rounded-lg divide-y divide-border-subtle">
                    {documents.map((doc, idx) => (
                      <div key={idx} className="flex items-center justify-between px-4 py-3">
                        <div>
                          <div className="text-xs font-medium text-ink-primary">{doc.file.name}</div>
                          <div className="text-[11px] text-ink-muted">
                            {doc.label} · {(doc.file.size / 1024).toFixed(0)} KB
                          </div>
                        </div>
                        <button type="button" onClick={() => removeDoc(idx)}
                          className="text-xs text-ink-muted hover:text-red-600 transition-colors">
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="border-2 border-dashed border-border-subtle rounded-lg py-10 text-center">
                    <div className="text-2xl mb-2">📄</div>
                    <p className="text-xs text-ink-muted">No documents added yet. You can upload them now or later from your portal.</p>
                  </div>
                )}

                <div className="flex justify-between pt-3 border-t border-border-subtle">
                  <button type="button" onClick={() => setStep(2)} className="btn btn-secondary">Back</button>
                  <button type="button" onClick={() => goToStep(4)} className="btn btn-primary">
                    Next: Review
                  </button>
                </div>
              </div>
            )}

            {/* Step 4: Review & Submit */}
            {step === 4 && (
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
                  <h3 className="text-sm font-bold text-ink-primary mb-3">Documents ({documents.length})</h3>
                  {documents.length > 0 ? (
                    <div className="flex flex-col gap-1.5">
                      {documents.map((doc, i) => (
                        <div key={i} className="text-xs text-ink-secondary">
                          <span className="font-medium text-ink-primary">{doc.label}</span> — {doc.file.name} ({(doc.file.size / 1024).toFixed(0)} KB)
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-ink-muted">No documents uploaded. You can add them later from your company portal.</p>
                  )}
                </div>

                {serverError && (
                  <div className="bg-danger-50 border border-danger-500/30 text-red-700 rounded-lg px-3 py-2.5 text-small">
                    {serverError}
                  </div>
                )}

                <div className="flex justify-between pt-3 border-t border-border-subtle">
                  <button type="button" onClick={() => setStep(3)} className="btn btn-secondary">Back</button>
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
