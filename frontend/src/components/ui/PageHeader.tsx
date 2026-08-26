import React from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  eyebrow?: string
  actions?: React.ReactNode
  breadcrumb?: { label: string; href?: string }[]
}

export default function PageHeader({ title, subtitle, eyebrow, actions, breadcrumb }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-1 mb-7">
      {breadcrumb && breadcrumb.length > 0 && (
        <nav className="flex items-center gap-1.5 text-xs text-ink-muted mb-1 font-mono">
          {breadcrumb.map((item, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span className="text-primary">/</span>}
              {item.href ? (
                <a href={item.href} className="hover:text-primary transition-colors">{item.label}</a>
              ) : (
                <span className="text-ink-secondary">{item.label}</span>
              )}
            </React.Fragment>
          ))}
        </nav>
      )}
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="eyebrow mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            {eyebrow ?? 'Corporate Lending'}
          </div>
          <h1 className="text-h2 text-ink-primary text-balance">{title}</h1>
          {subtitle && <p className="text-small text-ink-secondary mt-1.5 max-w-2xl">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
      </div>
    </div>
  )
}
