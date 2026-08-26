import { useState } from 'react'
import { useNavigate, Navigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuthStore } from '@/store/auth'
import { extractError } from '@/api/client'
import { useToast } from '@/components/ui/Toast'
import ThemeToggle from '@/components/ui/ThemeToggle'

interface FormValues { email: string; password: string; remember: boolean }

export default function Login() {
  const { login, user } = useAuthStore()
  const navigate = useNavigate()
  const { info } = useToast()
  const [serverError, setServerError] = useState('')

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    defaultValues: { remember: true },
  })

  if (user) return <Navigate to="/dashboard" replace />

  const onSubmit = async (values: FormValues) => {
    setServerError('')
    try {
      await login(values.email, values.password)
      navigate('/dashboard')
    } catch (err) {
      setServerError(extractError(err))
    }
  }

  const handleForgotPassword = () => {
    info('Password resets are handled by your system administrator. Contact IT support to regain access.')
  }

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      {/* Minimal top bar — logo left, theme toggle right, like a real internal tool */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-border-subtle flex-shrink-0">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md gradient-orange flex items-center justify-center flex-shrink-0">
            <span className="text-white font-extrabold text-[10px] font-mono">CL</span>
          </div>
          <span className="text-xs font-bold text-ink-primary font-mono tracking-wide">CORPORATE LENDING AUTOMATION</span>
        </Link>
        <ThemeToggle variant="icon" />
      </header>

      {/* Body */}
      <div className="flex-1 flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-[380px]">
          <div className="mb-7">
            <h1 className="text-h3 text-ink-primary">Sign in to your account</h1>
            <p className="text-small text-ink-secondary mt-1.5">
              Use the credentials issued by your loan-operations administrator.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
            <div>
              <label htmlFor="email" className="label">Work email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                className={`input ${errors.email ? 'input-error' : ''}`}
                placeholder="j.tan@yourbank.com.my"
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
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          {/* Real-world compliance notice — the kind every bank-facing tool has */}
          <div className="mt-6 flex items-start gap-2 text-[11px] text-ink-muted leading-relaxed border-t border-border-subtle pt-5">
            <svg className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span>
              This system is restricted to authorized personnel. All sign-ins and actions are
              logged for audit and regulatory compliance purposes. Unauthorized access is
              prohibited and may be subject to disciplinary or legal action.
            </span>
          </div>
        </div>
      </div>

      {/* Footer — the small dry details that make an internal tool feel real */}
      <footer className="flex items-center justify-between px-6 py-4 border-t border-border-subtle text-[11px] text-ink-muted font-mono flex-shrink-0">
        <span>© 2026 Corporate Lending Automation</span>
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
