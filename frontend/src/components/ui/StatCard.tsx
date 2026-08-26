interface StatCardProps {
  title: string
  value: string | number
  icon?: string
  change?: string
  changeType?: 'up' | 'down' | 'neutral'
  subtitle?: string
}

export default function StatCard({ title, value, icon, change, changeType = 'neutral', subtitle }: StatCardProps) {
  const changeColor = { up: 'text-up', down: 'text-down', neutral: 'text-ink-muted' }[changeType]

  return (
    <div className="card card-hover p-5 flex flex-col gap-3 relative overflow-hidden">
      {/* accent corner */}
      <div className="absolute top-0 right-0 w-16 h-16 -mr-8 -mt-8 rounded-full bg-cr-50 opacity-60" />

      <div className="flex items-start justify-between relative">
        <span className="text-[11px] font-bold uppercase tracking-wider text-ink-secondary font-mono">{title}</span>
        {icon && (
          <div className="w-9 h-9 rounded-lg gradient-orange flex items-center justify-center text-base text-white flex-shrink-0 shadow-orange">
            {icon}
          </div>
        )}
      </div>

      <div className="text-[32px] font-extrabold text-ink-primary tabular leading-none font-mono relative">{value}</div>

      {change && (
        <div className={`text-xs font-bold flex items-center gap-1 font-mono ${changeColor}`}>
          {changeType === 'up' && <span className="text-sm leading-none">↑</span>}
          {changeType === 'down' && <span className="text-sm leading-none">↓</span>}
          {change}
        </div>
      )}
      {subtitle && <div className="text-xs text-ink-muted">{subtitle}</div>}
    </div>
  )
}
