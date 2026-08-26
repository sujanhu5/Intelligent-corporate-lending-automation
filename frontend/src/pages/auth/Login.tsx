import { useState } from 'react'
import { useNavigate, Navigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuthStore } from '@/store/auth'
import { extractError } from '@/api/client'
import { useToast } from '@/components/ui/Toast'
import ThemeToggle from '@/components/ui/ThemeToggle'

type PortalType = 'select' | 'company' | 'bank' | 'admin'

interface FormValues { email: string; password: string; remember: boolean }

const PORTALS: { key: PortalType; title: string; subtitle: string; accent: string; iconBg: string; badge: string }[] = [
  {
    key: 'company',
    title: 'Company Portal',
    subtitle: 'Apply for corporate loans, upload financial documents, and track your application through every stage of the pipeline.',
    accent: 'border-blue-500/40 hover:border-blue-500',
    iconBg: 'bg-blue-500',
    badge: 'APPLICANT',
  },
  {
    key: 'bank',
    title: 'Bank Staff Portal',
    subtitle: 'Review applications, run credit assessments, manage the pipeline, and make lending decisions.',
    accent: 'border-amber-500/40 hover:border-amber-500',
    iconBg: 'bg-amber-500',
    badge: 'OFFICER',
  },
  {
    key: 'admin',
    title: 'System Administration',
    subtitle: 'Full platform control — manage users, companies, rules, ML models, and system configuration.',
    accent: 'border-violet-500/40 hover:border-violet-500',
    iconBg: 'bg-violet-500',
    badge: 'ADMIN',
  },
]

function getRedirectPath(role: string): string {
  return role === 'company' ? '/portal' : '/dashboard'
}

export default function Login() {
  const { login, user } = useAuthStore()
  const navigate = useNavigate()
  const { info } = useToast()
  const [portal, setPortal] = useState<PortalType>('select')
  const [serverError, setServerError] = useState('')

  const { register, handleSubmit, formState: { errors, isSubmitting }, reset } = useForm<FormValues>({
    defaultValues: { remember: true },
  })

  if (user) return <Navigate to={getRedirectPath(user.role)} replace />

  const onSubmit = async (values: FormValues) => {
    setServerError('')
    try {
      await login(values.email, values.password)
      const stored = useAuthStore.getState().user
      navigate(stored ? getRedirectPath(stored.role) : '/dashboard')
    } catch (err) {
      setServerError(extractError(err))
    }
  }

  const handleBack = () => {
    setPortal('select')
    setServerError('')
    reset()
  }

  const handleForgotPassword = () => {
    info('Password resets are handled by your system administrator. Contact IT support to regain access.')
  }

  const placeholders: Record<string, string> = {
    company: 'finance@yourcompany.com',
    bank: 'officer@bank.com',
    admin: 'admin@corporatelending.com',
  }

  const portalTitles: Record<string, string> = {
    company: 'Company Portal',
    bank: 'Bank Staff Portal',
    admin: 'Administrator',
  }

  const portalDescriptions: Record<string, string> = {
    company: 'Sign in with your company account to manage loan applications and track their progress.',
    bank: 'Sign in with your bank-issued credentials to review and process applications.',
    admin: 'System administrator access with full platform oversight and control.',
  }

  return (
    <div className="min-h-screen bg-canvas flex">
      {/* Left branded panel */}
      <div className="hidden lg:flex lg:w-[480px] xl:w-[540px] flex-col justify-between p-10 relative overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
        }}>
        <div className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
            backgroundSize: '32px 32px',
          }}
        />

        <div className="relative z-10">
          <Link to="/" className="flex items-center gap-3 mb-16">
            <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center border border-white/20">
              <span className="text-white font-extrabold text-sm font-mono">CL</span>
            </div>
            <div>
              <div className="text-white text-sm font-extrabold font-mono tracking-wide">CLA</div>
              <div className="text-white/50 text-[10px] font-mono uppercase tracking-widest">Lending Platform</div>
            </div>
          </Link>

          <h2 className="text-white text-[2rem] font-extrabold leading-[1.15] tracking-tight font-mono max-w-[380px]">
            Corporate Credit
            <br />
            Assessment
            <br />
            <span className="text-transparent bg-clip-text" style={{ backgroundImage: 'linear-gradient(90deg, #f97316, #fb923c)' }}>
              Platform.
            </span>
          </h2>

          <p className="text-white/60 text-sm leading-relaxed mt-6 max-w-[340px]">
            End-to-end loan underwriting — from document intake and OCR extraction
            through financial analysis, rule evaluation, and ML risk scoring.
          </p>
        </div>

        <div className="relative z-10 flex flex-col gap-4">
          <div className="flex items-center gap-5 text-white/40 text-[11px] font-mono">
            {['OCR Engine', 'Rule Engine', 'ML Models', 'Credit Reports'].map((feature, i) => (
              <span key={feature} className="flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-orange-400" />
                {feature}
              </span>
            ))}
          </div>
          <div className="text-white/30 text-[10px] font-mono">
            &copy; 2026 Corporate Lending Automation &middot; v1.0.0
          </div>
        </div>
      </div>

      {/* Right content panel */}
      <div className="flex-1 flex flex-col min-h-screen">
        <header className="h-14 flex items-center justify-between px-6 border-b border-border-subtle flex-shrink-0">
          <Link to="/" className="lg:hidden flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md gradient-orange flex items-center justify-center flex-shrink-0">
              <span className="text-white font-extrabold text-[10px] font-mono">CL</span>
            </div>
            <span className="text-xs font-bold text-ink-primary font-mono">CLA</span>
          </Link>
          <div className="hidden lg:block" />
          <div className="flex items-center gap-3">
            <ThemeToggle variant="icon" />
            <span className="flex items-center gap-1.5 text-[11px] text-ink-muted font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              Online
            </span>
          </div>
        </header>

        <div className="flex-1 flex items-center justify-center px-6 py-10">
          <div className="w-full max-w-[460px]">

            {portal === 'select' ? (
              <>
                <div className="mb-8">
                  <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-primary font-mono mb-3">
                    Sign In
                  </div>
                  <h1 className="text-[1.75rem] font-extrabold text-ink-primary leading-tight tracking-tight font-mono">
                    Choose your portal
                  </h1>
                  <p className="text-sm text-ink-secondary mt-2 leading-relaxed">
                    Select the appropriate access level to continue to the platform.
                  </p>
                </div>

                <div className="flex flex-col gap-3">
                  {PORTALS.map(p => (
                    <button
                      key={p.key}
                      onClick={() => setPortal(p.key)}
                      className={`group flex items-start gap-4 p-5 rounded-xl border-2 text-left transition-all duration-200 bg-surface-1 hover:bg-surface-2 ${p.accent}`}
                    >
                      <div className={`w-10 h-10 rounded-lg ${p.iconBg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                        <span className="text-[10px] font-extrabold text-white font-mono tracking-tight">{p.badge.slice(0, 3)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-ink-primary">{p.title}</span>
                          <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${p.iconBg} text-white`}>
                            {p.badge}
                          </span>
                        </div>
                        <p className="text-xs text-ink-secondary mt-1 leading-relaxed">{p.subtitle}</p>
                      </div>
                      <svg className="w-4 h-4 text-ink-muted flex-shrink-0 mt-1.5 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ))}
                </div>

                <div className="mt-8 pt-6 border-t border-border-subtle text-center">
                  <p className="text-xs text-ink-muted">
                    Need a loan?{' '}
                    <Link to="/register" className="text-primary font-bold hover:underline">
                      Register your company
                    </Link>
                    {' '}to get started.
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="mb-7">
                  <button
                    onClick={handleBack}
                    className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-primary mb-5 transition-colors font-medium"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                    </svg>
                    All portals
                  </button>

                  <div className="flex items-center gap-3 mb-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      portal === 'company' ? 'bg-blue-500' : portal === 'admin' ? 'bg-violet-500' : 'bg-amber-500'
                    }`}>
                      <span className="text-[9px] font-extrabold text-white font-mono">
                        {portal === 'company' ? 'APP' : portal === 'admin' ? 'ADM' : 'OFF'}
                      </span>
                    </div>
                    <div>
                      <h1 className="text-lg font-extrabold text-ink-primary font-mono leading-tight">
                        {portalTitles[portal]}
                      </h1>
                    </div>
                  </div>
                  <p className="text-sm text-ink-secondary leading-relaxed">
                    {portalDescriptions[portal]}
                  </p>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="card p-6 flex flex-col gap-4" noValidate>
                  <div>
                    <label htmlFor="email" className="label">Email address</label>
                    <input
                      id="email"
                      type="email"
                      autoComplete="email"
                      autoFocus
                      className={`input ${errors.email ? 'input-error' : ''}`}
                      placeholder={placeholders[portal] ?? ''}
                      {...register('email', {
                        required: 'Email is required.',
                        pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email.' },
                      })}
                    />
                    {errors.email && <span className="field-error">{errors.email.message}</span>}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label htmlFor="password" className="label mb-0">Password</label>
                      <button
                        type="button"
                        onClick={handleForgotPassword}
                        className="text-[11px] font-medium text-primary hover:underline mb-1.5"
                      >
                        Forgot password?
                      </button>
                    </div>
                    <input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      className={`input ${errors.password ? 'input-error' : ''}`}
                      placeholder="Enter your password"
                      {...register('password', { required: 'Password is required.' })}
                    />
                    {errors.password && <span className="field-error">{errors.password.message}</span>}
                  </div>

                  <label className="flex items-center gap-2 text-xs text-ink-secondary select-none cursor-pointer">
                    <input
                      type="checkbox"
                      className="w-3.5 h-3.5 rounded-sm border-border accent-primary cursor-pointer"
                      {...register('remember')}
                    />
                    Keep me signed in on this device
                  </label>

                  {serverError && (
                    <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-3.5 py-2.5 text-xs font-medium">
                      {serverError}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="btn btn-primary btn-lg w-full mt-1"
                  >
                    {isSubmitting ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Signing in...
                      </span>
                    ) : 'Sign in'}
                  </button>
                </form>

                {portal === 'company' && (
                  <div className="mt-5 text-center">
                    <p className="text-xs text-ink-muted">
                      Don't have an account?{' '}
                      <Link to="/register" className="text-primary font-bold hover:underline">
                        Register your company
                      </Link>
                    </p>
                  </div>
                )}

                <div className="mt-6 flex items-start gap-2.5 text-[11px] text-ink-muted leading-relaxed border-t border-border-subtle pt-5">
                  <svg className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-ink-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <span>
                    All sign-ins are logged for audit and regulatory compliance. Unauthorized access attempts are recorded and may be reported.
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        <footer className="lg:hidden flex items-center justify-between px-6 py-3 border-t border-border-subtle text-[11px] text-ink-muted font-mono flex-shrink-0">
          <span>&copy; 2026 CLA</span>
          <span>v1.0.0</span>
        </footer>
      </div>
    </div>
  )
}
