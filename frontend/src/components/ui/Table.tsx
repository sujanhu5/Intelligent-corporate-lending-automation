import React from 'react'
import Spinner from './Spinner'
import EmptyState from './EmptyState'

interface Column<T> {
  key: string
  header: string
  render: (row: T) => React.ReactNode
  className?: string
}

interface TableProps<T> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyTitle?: string
  emptyDescription?: string
  onRowClick?: (row: T) => void
  keyExtractor: (row: T) => string
}

export default function Table<T>({
  columns, data, loading, emptyTitle = 'No records found',
  emptyDescription, onRowClick, keyExtractor,
}: TableProps<T>) {
  if (loading) {
    return (
      <div className="card flex items-center justify-center py-16">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className="card">
        <EmptyState title={emptyTitle} description={emptyDescription} />
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-md border border-border-subtle shadow-xs">
      <table className="w-full border-collapse text-small">
        <thead className="bg-surface-2">
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                className={`px-4 py-3 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider whitespace-nowrap font-mono ${col.className ?? ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-surface-1 divide-y divide-border-subtle">
          {data.map(row => (
            <tr
              key={keyExtractor(row)}
              onClick={() => onRowClick?.(row)}
              className={`${onRowClick ? 'cursor-pointer hover:bg-surface-2' : ''} transition-colors`}
            >
              {columns.map(col => (
                <td key={col.key} className={`px-4 py-3 text-ink-primary ${col.className ?? ''}`}>
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Pagination({
  page, pages, total, pageSize, onChange,
}: { page: number; pages: number; total: number; pageSize: number; onChange: (p: number) => void }) {
  if (pages <= 1) return null
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)

  return (
    <div className="flex items-center justify-between mt-4 text-small text-ink-secondary">
      <span>Showing {start}–{end} of {total}</span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          className="px-3 py-1.5 rounded-xs border border-border text-ink-secondary hover:bg-surface-2
                     disabled:opacity-40 disabled:pointer-events-none transition-colors text-xs"
        >
          Previous
        </button>
        {Array.from({ length: Math.min(pages, 7) }, (_, i) => {
          const p = i + 1
          return (
            <button
              key={p}
              onClick={() => onChange(p)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-colors
                ${p === page
                  ? 'gradient-orange text-white border-transparent'
                  : 'border-border text-ink-secondary hover:bg-surface-2'}`}
            >
              {p}
            </button>
          )
        })}
        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= pages}
          className="px-3 py-1.5 rounded-xs border border-border text-ink-secondary hover:bg-surface-2
                     disabled:opacity-40 disabled:pointer-events-none transition-colors text-xs"
        >
          Next
        </button>
      </div>
    </div>
  )
}
