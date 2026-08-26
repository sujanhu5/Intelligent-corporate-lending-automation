import Button from './Button'

interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export default function EmptyState({ icon = '📂', title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
      <span className="text-4xl">{icon}</span>
      <h3 className="text-h4 text-ink-primary">{title}</h3>
      {description && <p className="text-small text-ink-secondary max-w-sm">{description}</p>}
      {action && (
        <div className="mt-2">
          <Button onClick={action.onClick}>{action.label}</Button>
        </div>
      )}
    </div>
  )
}
