import type { ReactNode } from 'react'
import type { ApplicationStatus, FinalDecision, RiskLevel, DocumentStatus } from '@/types'

type BadgeVariant = 'approved' | 'rejected' | 'pending' | 'review' | 'draft' | 'info'

const variantStyles: Record<BadgeVariant, string> = {
  approved: 'bg-success-50 text-green-700',
  rejected: 'bg-danger-50 text-red-700',
  pending:  'bg-warning-50 text-amber-700',
  review:   'bg-teal-50 text-teal-700',
  draft:    'bg-surface-2 text-ink-secondary',
  info:     'bg-cr-50 text-cr-700',
}

const dotStyles: Record<BadgeVariant, string> = {
  approved: 'bg-success-500',
  rejected: 'bg-danger-500',
  pending:  'bg-warning-500',
  review:   'bg-teal-500',
  draft:    'bg-ink-muted',
  info:     'bg-primary',
}

interface BadgeProps {
  variant: BadgeVariant
  children: ReactNode
  dot?: boolean
}

export default function Badge({ variant, children, dot = true }: BadgeProps) {
  return (
    <span className={`badge ${variantStyles[variant]}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotStyles[variant]}`} />}
      {children}
    </span>
  )
}

export function ApplicationStatusBadge({ status }: { status: ApplicationStatus }) {
  const map: Record<ApplicationStatus, { variant: BadgeVariant; label: string }> = {
    draft:           { variant: 'draft',    label: 'Draft' },
    submitted:       { variant: 'pending',  label: 'Submitted' },
    under_review:    { variant: 'review',   label: 'Under Review' },
    ocr_processing:  { variant: 'pending',  label: 'OCR Processing' },
    ocr_complete:    { variant: 'pending',  label: 'OCR Complete' },
    ratio_calculated:{ variant: 'pending',  label: 'Ratios Calculated' },
    rule_evaluated:  { variant: 'pending',  label: 'Rules Evaluated' },
    ml_predicted:    { variant: 'pending',  label: 'ML Predicted' },
    report_generated:{ variant: 'info',     label: 'Report Generated' },
    approved:        { variant: 'approved', label: 'Approved' },
    rejected:        { variant: 'rejected', label: 'Rejected' },
    manual_review:   { variant: 'review',   label: 'Manual Review' },
    withdrawn:       { variant: 'draft',    label: 'Withdrawn' },
  }
  const { variant, label } = map[status] ?? { variant: 'draft', label: status }
  return <Badge variant={variant}>{label}</Badge>
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const map: Record<RiskLevel, { variant: BadgeVariant; label: string }> = {
    very_low:  { variant: 'approved', label: 'Very Low Risk' },
    low:       { variant: 'approved', label: 'Low Risk' },
    medium:    { variant: 'pending',  label: 'Medium Risk' },
    high:      { variant: 'review',   label: 'High Risk' },
    very_high: { variant: 'rejected', label: 'Very High Risk' },
  }
  const { variant, label } = map[level] ?? { variant: 'draft', label: level }
  return <Badge variant={variant}>{label}</Badge>
}

export function DocStatusBadge({ status }: { status: DocumentStatus }) {
  const map: Record<DocumentStatus, { variant: BadgeVariant; label: string }> = {
    uploaded:   { variant: 'pending',  label: 'Uploaded' },
    processing: { variant: 'info',     label: 'Processing' },
    extracted:  { variant: 'approved', label: 'Extracted' },
    failed:     { variant: 'rejected', label: 'Failed' },
  }
  const { variant, label } = map[status] ?? { variant: 'draft', label: status }
  return <Badge variant={variant}>{label}</Badge>
}

export function DecisionBadge({ decision }: { decision: FinalDecision }) {
  const map: Record<FinalDecision, { variant: BadgeVariant; label: string }> = {
    pending:       { variant: 'draft',    label: 'Pending' },
    approved:      { variant: 'approved', label: 'Approved' },
    rejected:      { variant: 'rejected', label: 'Rejected' },
    manual_review: { variant: 'review',   label: 'Manual Review' },
  }
  const { variant, label } = map[decision] ?? { variant: 'draft', label: decision }
  return <Badge variant={variant}>{label}</Badge>
}
