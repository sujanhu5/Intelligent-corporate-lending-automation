import React, { forwardRef } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: string
  error?: string
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, className = '', id, ...props }, ref
) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col">
      {label && <label htmlFor={inputId} className="label">{label}</label>}
      <input
        ref={ref}
        id={inputId}
        className={`input ${error ? 'input-error' : ''} ${className}`}
        {...props}
      />
      {error && <span className="field-error">{error}</span>}
      {!error && hint && <span className="hint">{hint}</span>}
    </div>
  )
})

export default Input

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  hint?: string
  error?: string
  options: { value: string; label: string }[]
  placeholder?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, hint, error, options, placeholder, className = '', id, ...props }, ref
) {
  const selectId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col">
      {label && <label htmlFor={selectId} className="label">{label}</label>}
      <select
        ref={ref}
        id={selectId}
        className={`input ${error ? 'input-error' : ''} ${className}`}
        {...props}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      {error && <span className="field-error">{error}</span>}
      {!error && hint && <span className="hint">{hint}</span>}
    </div>
  )
})

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  hint?: string
  error?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, hint, error, className = '', id, rows = 3, ...props }, ref
) {
  const textareaId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col">
      {label && <label htmlFor={textareaId} className="label">{label}</label>}
      <textarea
        ref={ref}
        id={textareaId}
        className={`input ${error ? 'input-error' : ''} ${className}`}
        rows={rows}
        {...props}
      />
      {error && <span className="field-error">{error}</span>}
      {!error && hint && <span className="hint">{hint}</span>}
    </div>
  )
})
