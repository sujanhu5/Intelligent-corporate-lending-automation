import { useState } from 'react'
import { useNavigate, Navigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuthStore } from '@/store/auth'
import { extractError } from '@/api/client'
import { useToast } from '@/components/ui/Toast'
import ThemeToggle from '@/components/ui/ThemeToggle'

type PortalType = 'select' | 'company' | 'bank' | 'admin'

interface FormValues { email: string; password: string; remember: boolean }

const PORTALS: { key: PortalType; icon: string; title: string; subtitle: string; color: string }[] = [
  { key: 'company', icon: '🏢', title: 'Company Portal', subtitle: 'Apply for a loan, track your application status', color: 'bg-blue-50 border-blue-200 hover:border-blue-400' },
  { key: 'bank', icon: '🏦', title: 'Bank Staff', subtitle: 'Officers, analysts, and reviewers', color: 'bg-amber-50 border-amber-200 hover:border-amber-400' },
  { key: 'admin', icon: '⚙', title: 'System Administrator', subtitle: 'Full platform management and oversight', color: 'bg-purple-50 border-purple-200 hover:border-purple-400' },
]

function getRedirectPath(role: string): string {
  switch (role) {
    case 'company': return '/portal'
    case 'admin': return '/dashboard'
    default: return '/dashboard'
  }
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
        <div className="w-full max-w-[440px]">

          {portal === 'select' ? (
            <>
              <div className="mb-8 text-center">
                <h1 className="text-h3 text-ink-primary">Welcome to CLA</h1>
                <p className="text-small text-ink-secondary mt-2">
                  Select your portal to sign in
                </p>
              </div>

              <div className="flex flex-col gap-3">
                {PORTALS.map(p => (
                  <button
                    key={p.key}
                    onClick={() => setPortal(p.key)}
                    className={`flex items-center gap-4 p-4 rounded-xl border-2 text-left transition-all ${p.color}`}
                  >
                    <span className="text-2xl">{p.icon}</span>
                    <div>
                      <div className="text-sm font-bold text-ink-primary">{p.title}</div>
                      <div className="text-xs text-ink-secondary mt-0.5">{p.subtitle}</div>
                    </div>
                    <svg className="w-4 h-4 ml-auto text-ink-muted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                ))}
              </div>

              <div className="mt-6 text-center">
                <p className="text-xs text-ink-muted">
                  New company?{' '}
                  <Link to="/register" className="text-primary font-semibold hover:underline">
                    Register for a loan application
                  </Link>
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="mb-7">
                <button
                  onClick={handleBack}
                  className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-primary mb-4 transition-colors"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                  Back to portal selection
                </button>
                <h1 className="text-h3 text-ink-primary">
                  {portal === 'company' ? 'Company Portal Sign In' : portal === 'admin' ? 'Administrator Sign In' : 'Bank Staff Sign In'}
                </h1>
                <p className="text-small text-ink-secondary mt-1.5">
                  {portal === 'company'
                    ? 'Sign in with your company account to manage loan applications.'
                    : portal === 'admin'
                    ? 'System administrator access with full platform control.'
                    : 'Sign in with your bank-issued credentials.'}
                </p>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
                <div>
                  <label htmlFor="email" className="label">Email address</label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
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
                      className="text-xs font-medium text-primary hover:underline mb-1.5"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    className={`input ${errors.password ? 'input-error' : ''}`}
                    placeholder="••••••••"
                    {...register('password', { required: 'Password is required.' })}
                  />
                  {errors.password && <span className="field-error">{errors.password.message}</span>}
                </div>

                <label className="flex items-center gap-2 text-xs text-ink-secondary select-none cursor-pointer -mt-1">
                  <input
                    type="checkbox"
                    className="w-3.5 h-3.5 rounded-sm border-border accent-primary cursor-pointer"
                    {...register('remember')}
                  />
                  Keep me signed in on this device
                </label>

                {serverError && (
                  <div className="bg-danger-50 border border-danger-500/30 text-red-700 rounded-lg px-3 py-2.5 text-small">
                    {serverError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn btn-primary btn-lg mt-1 w-full"
                >
                  {isSubmitting ? 'Signing in...' : 'Sign in'}
                </button>
              </form>

              {portal === 'company' && (
                <div className="mt-5 text-center">
                  <p className="text-xs text-ink-muted">
                    Don't have an account?{' '}
                    <Link to="/register" className="text-primary font-semibold hover:underline">
                      Register your company
                    </Link>
                  </p>
                </div>
              )}

              <div className="mt-6 flex items-start gap-2 text-[11px] text-ink-muted leading-relaxed border-t border-border-subtle pt-5">
                <svg className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span>
                  All sign-ins and actions are logged for audit and regulatory compliance purposes.
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      <footer className="flex items-center justify-between px-6 py-4 border-t border-border-subtle text-[11px] text-ink-muted font-mono flex-shrink-0">
        <span>&copy; 2026 Corporate Lending Automation</span>
        <div className="flex items-center gap-4">
          <span>v1.0.0</span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-up" />
            All systems operational
          </span>
        </div>
      </footer>
    </div>
  )
}
