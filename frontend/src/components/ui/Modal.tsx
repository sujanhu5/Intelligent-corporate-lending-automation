import React, { useEffect } from 'react'
import Button from './Button'

interface ModalProps {
  open: boolean
  title: string
  description?: string
  onClose: () => void
  children?: React.ReactNode
  footer?: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const sizeClass = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' }

export default function Modal({ open, title, description, onClose, children, footer, size = 'md' }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div
        className={`relative w-full ${sizeClass[size]} bg-surface-1 rounded-md shadow-xl border border-border-subtle animate-fade-in`}
        role="dialog"
        aria-modal
        aria-labelledby="modal-title"
      >
        <div className="flex items-start justify-between p-5 border-b border-border-subtle">
          <div>
            <h3 id="modal-title" className="text-h4 text-ink-primary">{title}</h3>
            {description && <p className="text-small text-ink-secondary mt-1">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="text-ink-muted hover:text-ink-primary transition-colors ml-4 flex-shrink-0"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        {children && <div className="p-5">{children}</div>}
        {footer && (
          <div className="flex justify-end gap-3 px-5 py-4 border-t border-border-subtle bg-surface-2 rounded-b-md">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

interface ConfirmModalProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'primary' | 'danger'
  loading?: boolean
  onConfirm: () => void
  onClose: () => void
}

export function ConfirmModal({
  open, title, description, confirmLabel = 'Confirm', cancelLabel = 'Cancel',
  variant = 'primary', loading, onConfirm, onClose,
}: ConfirmModalProps) {
  return (
    <Modal
      open={open}
      title={title}
      description={description}
      onClose={onClose}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>{cancelLabel}</Button>
          <Button variant={variant} onClick={onConfirm} loading={loading}>{confirmLabel}</Button>
        </>
      }
    />
  )
}
