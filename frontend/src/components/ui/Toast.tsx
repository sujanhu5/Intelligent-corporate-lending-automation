import React, { createContext, useContext, useCallback, useState } from 'react'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: number
  type: ToastType
  message: string
}

interface ToastCtx {
  success: (msg: string) => void
  error: (msg: string) => void
  warning: (msg: string) => void
  info: (msg: string) => void
}

const ToastContext = createContext<ToastCtx | null>(null)

let _id = 0

const icons: Record<ToastType, string> = {
  success: '✓', error: '✕', warning: '⚠', info: 'ℹ',
}

const styles: Record<ToastType, string> = {
  success: 'bg-success-50 border-success-500 text-green-800',
  error:   'bg-danger-50 border-danger-500 text-red-800',
  warning: 'bg-warning-50 border-warning-500 text-amber-800',
  info:    'bg-cr-50 border-primary text-cr-800',
}

const dotStyles: Record<ToastType, string> = {
  success: 'text-success-500',
  error:   'text-danger-500',
  warning: 'text-warning-500',
  info:    'text-primary',
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const remove = useCallback((id: number) => {
    setToasts(t => t.filter(x => x.id !== id))
  }, [])

  const add = useCallback((type: ToastType, message: string) => {
    const id = ++_id
    setToasts(t => [...t, { id, type, message }])
    setTimeout(() => remove(id), 4000)
  }, [remove])

  const ctx: ToastCtx = {
    success: (m) => add('success', m),
    error:   (m) => add('error', m),
    warning: (m) => add('warning', m),
    info:    (m) => add('info', m),
  }

  return (
    <ToastContext.Provider value={ctx}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`flex items-start gap-2.5 px-4 py-3 rounded-md border shadow-md
              text-sm font-medium max-w-sm animate-fade-in pointer-events-auto ${styles[t.type]}`}
          >
            <span className={`font-bold flex-shrink-0 ${dotStyles[t.type]}`}>{icons[t.type]}</span>
            <span>{t.message}</span>
            <button onClick={() => remove(t.id)} className="ml-auto opacity-60 hover:opacity-100">✕</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastCtx {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
