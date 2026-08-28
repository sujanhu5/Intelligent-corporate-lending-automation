import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/api/auth'
import { usersApi, type UserCreate } from '@/api/users'
import type { User, UserRole } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import Button from '@/components/ui/Button'
import Input, { Select } from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import Badge from '@/components/ui/Badge'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'
import { PageLoader } from '@/components/ui/Spinner'

const ROLES: { value: UserRole; label: string }[] = [
  { value: 'admin',   label: 'Admin' },
  { value: 'officer', label: 'Loan Officer' },
  { value: 'analyst', label: 'Credit Analyst' },
  { value: 'viewer',  label: 'Viewer' },
]

interface PasswordForm { current_password: string; new_password: string; confirm_password: string }
interface EmailForm { email: string }

export default function Settings() {
  const { user, setUser } = useAuthStore()
  const [users, setUsers] = useState<User[]>([])
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [userModalOpen, setUserModalOpen] = useState(false)
  const [savingUser, setSavingUser] = useState(false)
  const { success, error } = useToast()

  const pwForm = useForm<PasswordForm>()
  const userForm = useForm<UserCreate>()
  const emailForm = useForm<EmailForm>({ defaultValues: { email: user?.email ?? '' } })

  useEffect(() => {
    if (user?.role === 'admin') {
      usersApi.list({ page_size: 100 }).then(r => setUsers(r.items))
        .finally(() => setLoadingUsers(false))
    } else {
      setLoadingUsers(false)
    }
  }, [user])

  const onChangeEmail = async (values: EmailForm) => {
    const newEmail = values.email.trim().toLowerCase()
    if (!newEmail || newEmail === user?.email?.toLowerCase()) {
      emailForm.setError('email', { message: 'Enter a different email address.' })
      return
    }
    try {
      const updated = await usersApi.updateMe({ email: newEmail })
      setUser(updated)
      emailForm.reset({ email: updated.email })
      success('Email address updated.')
    } catch (err) {
      error(extractError(err))
    }
  }

  const onChangePassword = async (values: PasswordForm) => {
    if (values.new_password !== values.confirm_password) {
      pwForm.setError('confirm_password', { message: 'Passwords do not match.' })
      return
    }
    try {
      await authApi.changePassword(values.current_password, values.new_password, values.confirm_password)
      success('Password changed successfully.')
      pwForm.reset()
    } catch (err) {
      error(extractError(err))
    }
  }

  const onCreateUser = async (values: UserCreate) => {
    setSavingUser(true)
    try {
      await usersApi.create(values)
      success(`User ${values.email} created.`)
      const r = await usersApi.list({ page_size: 100 })
      setUsers(r.items)
      setUserModalOpen(false)
      userForm.reset()
    } catch (err) {
      error(extractError(err))
    } finally {
      setSavingUser(false)
    }
  }

  const handleToggleUser = async (u: User) => {
    try {
      const active = u.status === 'active'
      await usersApi.setStatus(u.id, active ? 'inactive' : 'active')
      success(`User ${active ? 'deactivated' : 'activated'}.`)
      const r = await usersApi.list({ page_size: 100 })
      setUsers(r.items)
    } catch (err) {
      error(extractError(err))
    }
  }

  if (!user) return <PageLoader />

  return (
    <div className="max-w-2xl">
      <PageHeader title="Settings" subtitle="Account preferences and user management." />

      {/* Profile section */}
      <div className="card p-5 mb-6">
        <div className="flex items-center gap-4 mb-5">
          <div className="w-12 h-12 rounded-xl gradient-orange flex items-center justify-center shadow-orange">
            <span className="text-white font-extrabold text-lg font-mono">{user.full_name.charAt(0)}</span>
          </div>
          <div>
            <h3 className="text-h4 font-mono">{user.full_name}</h3>
            <div className="text-[11px] text-ink-muted font-mono uppercase tracking-wider">{user.role} · {user.email}</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted font-mono mb-1">Full Name</div>
            <div className="text-small text-ink-primary font-medium">{user.full_name}</div>
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted font-mono mb-1">Email</div>
            <div className="text-small text-ink-primary font-medium">{user.email}</div>
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted font-mono mb-1">Role</div>
            <Badge variant="info" dot={false}>{user.role}</Badge>
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted font-mono mb-1">Status</div>
            <Badge variant="approved" dot>Active</Badge>
          </div>
        </div>
      </div>

      {/* Change email */}
      <div className="card p-5 mb-6">
        <h3 className="text-h4 mb-1 font-mono">Change Email</h3>
        <p className="text-caption text-ink-muted mb-4">
          Update the email address used to sign in and receive notifications.
        </p>
        <form onSubmit={emailForm.handleSubmit(onChangeEmail)} className="flex flex-col gap-4">
          <Input
            label="Email Address"
            type="email"
            error={emailForm.formState.errors.email?.message}
            {...emailForm.register('email', {
              required: 'Required.',
              pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email address.' },
            })}
          />
          <div className="flex justify-end">
            <Button type="submit" loading={emailForm.formState.isSubmitting}>
              Update Email
            </Button>
          </div>
        </form>
      </div>

      {/* Change password */}
      <div className="card p-5 mb-6">
        <h3 className="text-h4 mb-4 font-mono">Change Password</h3>
        <form onSubmit={pwForm.handleSubmit(onChangePassword)} className="flex flex-col gap-4">
          <Input
            label="Current Password"
            type="password"
            error={pwForm.formState.errors.current_password?.message}
            {...pwForm.register('current_password', { required: 'Required.' })}
          />
          <Input
            label="New Password"
            type="password"
            error={pwForm.formState.errors.new_password?.message}
            {...pwForm.register('new_password', {
              required: 'Required.',
              minLength: { value: 8, message: 'Minimum 8 characters.' },
            })}
          />
          <Input
            label="Confirm New Password"
            type="password"
            error={pwForm.formState.errors.confirm_password?.message}
            {...pwForm.register('confirm_password', { required: 'Required.' })}
          />
          <div className="flex justify-end">
            <Button type="submit" loading={pwForm.formState.isSubmitting}>
              Update Password
            </Button>
          </div>
        </form>
      </div>

      {/* User management (admin only) */}
      {user.role === 'admin' && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-h4 font-mono">User Management</h3>
            <Button size="sm" onClick={() => setUserModalOpen(true)}>+ New User</Button>
          </div>

          {loadingUsers ? (
            <div className="py-8 text-center text-ink-muted text-small">Loading users…</div>
          ) : (
            <div className="overflow-x-auto rounded-sm border border-border-subtle">
              <table className="w-full border-collapse text-small">
                <thead className="bg-surface-2">
                  <tr>
                    {['Name', 'Email', 'Role', 'Status', ''].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {users.map(u => (
                    <tr key={u.id} className={`hover:bg-surface-2 transition-colors ${u.status !== 'active' ? 'opacity-50' : ''}`}>
                      <td className="px-4 py-3 font-medium text-ink-primary">{u.full_name}</td>
                      <td className="px-4 py-3 text-ink-secondary">{u.email}</td>
                      <td className="px-4 py-3"><Badge variant="info" dot={false}>{u.role}</Badge></td>
                      <td className="px-4 py-3">
                        <Badge variant={u.status === 'active' ? 'approved' : 'draft'} dot>
                          {u.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        {u.id !== user.id && (
                          <button
                            onClick={() => handleToggleUser(u)}
                            className="text-xs text-ink-secondary hover:text-primary transition-colors"
                          >
                            {u.status === 'active' ? 'Deactivate' : 'Activate'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Create user modal */}
      <Modal
        open={userModalOpen}
        title="New User"
        onClose={() => setUserModalOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setUserModalOpen(false)}>Cancel</Button>
            <Button form="user-form" type="submit" loading={savingUser}>Create User</Button>
          </>
        }
      >
        <form id="user-form" onSubmit={userForm.handleSubmit(onCreateUser)} className="flex flex-col gap-4">
          <Input
            label="Full Name"
            error={userForm.formState.errors.full_name?.message}
            {...userForm.register('full_name', { required: 'Required.' })}
          />
          <Input
            label="Email"
            type="email"
            error={userForm.formState.errors.email?.message}
            {...userForm.register('email', { required: 'Required.' })}
          />
          <Input
            label="Password"
            type="password"
            error={userForm.formState.errors.password?.message}
            {...userForm.register('password', {
              required: 'Required.',
              minLength: { value: 8, message: 'Minimum 8 characters.' },
            })}
          />
          <Select
            label="Role"
            options={ROLES}
            placeholder="Select role…"
            error={userForm.formState.errors.role?.message}
            {...userForm.register('role', { required: 'Required.' })}
          />
        </form>
      </Modal>
    </div>
  )
}
