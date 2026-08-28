import { useEffect, useState } from 'react'
import { analyticsApi } from '@/api/analytics'
import type {
  AnalyticsSummary,
  ApplicationTrend,
  RiskDistribution,
  IndustryBreakdown,
  PipelineFunnelStage,
  RuleTriggerStat,
} from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import { PageLoader } from '@/components/ui/Spinner'
import {
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
  BarChart, Bar,
  AreaChart, Area, CartesianGrid,
  LabelList,
} from 'recharts'

const chartTooltipStyle = {
  backgroundColor: 'var(--surface-1)',
  border: '1px solid var(--border-subtle)',
  borderRadius: 8,
  boxShadow: '0 8px 24px -12px rgba(0,0,0,0.25)',
  fontSize: 12,
  padding: '8px 12px',
}
const chartTooltipLabel = { color: 'var(--ink-muted)', fontSize: 10, textTransform: 'uppercase' as const, letterSpacing: '.06em', marginBottom: 2 }
const chartTooltipItem  = { color: 'var(--ink-primary)', fontWeight: 600 }

const RISK_COLORS: Record<string, string> = {
  very_low: '#12A150',
  low: '#7CB518',
  medium: '#F4A300',
  high: '#EF6C1A',
  very_high: '#E5484D',
}

const OUTCOME_COLORS = ['#12A150', '#E5484D', '#F4A300', '#C9C0B4']

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card px-5 py-4">
      <div className="text-2xl font-bold tabular text-ink-primary">{value}</div>
      <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted mt-1">{label}</div>
    </div>
  )
}

export default function Analytics() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [trends, setTrends] = useState<ApplicationTrend[]>([])
  const [riskDist, setRiskDist] = useState<RiskDistribution[]>([])
  const [industryData, setIndustryData] = useState<IndustryBreakdown[]>([])
  const [funnel, setFunnel] = useState<PipelineFunnelStage[]>([])
  const [ruleTriggers, setRuleTriggers] = useState<RuleTriggerStat[]>([])
  const [loading, setLoading] = useState(true)
  const [trendDays, setTrendDays] = useState(30)

  useEffect(() => {
    Promise.all([
      analyticsApi.summary(),
      analyticsApi.trends(trendDays),
      analyticsApi.riskDistribution(),
      analyticsApi.industryBreakdown(),
      analyticsApi.pipelineFunnel(),
      analyticsApi.ruleTriggers(10),
    ]).then(([s, t, r, ind, f, rt]) => {
      setSummary(s)
      setTrends(t)
      setRiskDist(r)
      setIndustryData(ind)
      setFunnel(f)
      setRuleTriggers(rt)
    }).finally(() => setLoading(false))
  }, [trendDays])

  if (loading) return <PageLoader />

  const outcomeData = summary ? [
    { name: 'Approved',      value: summary.total_approved      },
    { name: 'Rejected',      value: summary.total_rejected      },
    { name: 'Manual Review', value: summary.total_manual_review },
    { name: 'Pending',       value: summary.total_pending       },
  ].filter(d => d.value > 0) : []

  const fmtRM = (n: number) => `RM ${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Pipeline funnel, decision outcomes, risk distribution, and portfolio metrics."
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard label="Total Applications" value={summary?.total_applications ?? 0} />
        <KpiCard label="Approval Rate" value={`${summary?.approval_rate ?? 0}%`} />
        <KpiCard label="Avg Risk Score" value={summary?.avg_risk_score?.toFixed(1) ?? '—'} />
        <KpiCard label="Approved Portfolio" value={summary ? fmtRM(summary.total_loan_amount_approved) : '—'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Submission trends */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-h4">Submission Trends</h3>
            <select
              value={trendDays}
              onChange={e => setTrendDays(Number(e.target.value))}
              className="text-xs border border-border rounded px-2 py-1 bg-surface-1 text-ink-primary"
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
              <option value={365}>1 year</option>
            </select>
          </div>
          {trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={trends} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradSubmitAna" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="var(--cr-500)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--cr-500)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradApproveAna" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#12A150" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#12A150" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-subtle)" strokeOpacity={0.6} vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--ink-muted)' }} tickFormatter={d => d.slice(5)} tickLine={false} axisLine={{ stroke: 'var(--border-subtle)' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: 'var(--ink-muted)' }} tickLine={false} axisLine={false} width={30} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartTooltipLabel} itemStyle={chartTooltipItem} cursor={{ stroke: 'var(--border)', strokeDasharray: '3 3' }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                <Area type="monotone" dataKey="submitted" stroke="var(--cr-500)" strokeWidth={2.2} fill="url(#gradSubmitAna)" dot={false} activeDot={{ r: 4, strokeWidth: 2 }} animationDuration={800} />
                <Area type="monotone" dataKey="approved"  stroke="#12A150"       strokeWidth={2}   fill="url(#gradApproveAna)" dot={false} activeDot={{ r: 4, strokeWidth: 2 }} animationDuration={900} />
                <Area type="monotone" dataKey="rejected"  stroke="#E5484D"       strokeWidth={1.6} fill="none" strokeDasharray="4 4" dot={false} animationDuration={1000} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-ink-muted text-small">No data for this period.</div>
          )}
        </div>

        {/* Decision outcomes */}
        <div className="card p-5">
          <h3 className="text-h4 mb-4">Decision Outcomes</h3>
          {outcomeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={outcomeData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%" cy="50%"
                  outerRadius={90}
                  innerRadius={50}
                  paddingAngle={3}
                  stroke="var(--surface-1)"
                  strokeWidth={2}
                  animationDuration={900}
                  label={({ percent }) => percent && percent > 0.05 ? `${(percent * 100).toFixed(0)}%` : ''}
                  labelLine={false}
                >
                  {outcomeData.map((_, i) => (
                    <Cell key={i} fill={OUTCOME_COLORS[i % OUTCOME_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartTooltipLabel} itemStyle={chartTooltipItem} formatter={(v: number) => [v, 'Applications']} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-ink-muted text-small">No decision data yet.</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Risk distribution */}
        <div className="card p-5">
          <h3 className="text-h4 mb-4">Risk Level Distribution</h3>
          {riskDist.some(r => r.count > 0) ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={riskDist} margin={{ top: 12, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-subtle)" strokeOpacity={0.6} vertical={false} />
                <XAxis dataKey="risk_level" tick={{ fontSize: 11, fill: 'var(--ink-muted)' }} tickFormatter={r => r.replace('_', ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())} tickLine={false} axisLine={{ stroke: 'var(--border-subtle)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--ink-muted)' }} allowDecimals={false} tickLine={false} axisLine={false} width={28} />
                <Tooltip contentStyle={chartTooltipStyle} labelStyle={chartTooltipLabel} itemStyle={chartTooltipItem} cursor={{ fill: 'var(--surface-2)', opacity: 0.5 }} formatter={(v: number) => [v, 'Applications']} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} animationDuration={800}>
                  {riskDist.map((entry, i) => (
                    <Cell key={i} fill={RISK_COLORS[entry.risk_level] ?? '#9CA3AF'} />
                  ))}
                  <LabelList dataKey="count" position="top" style={{ fontSize: 10, fill: 'var(--ink-secondary)', fontWeight: 600 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-ink-muted text-small">No ML predictions yet.</div>
          )}
        </div>

        {/* Pipeline funnel */}
        <div className="card p-5">
          <h3 className="text-h4 mb-4">Pipeline Funnel</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={funnel} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="gradFunnel" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%"   stopColor="var(--cr-400)" />
                  <stop offset="100%" stopColor="var(--cr-600)" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" stroke="var(--border-subtle)" strokeOpacity={0.6} horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--ink-muted)' }} allowDecimals={false} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="label" width={130} tick={{ fontSize: 10, fill: 'var(--ink-secondary)' }} tickLine={false} axisLine={{ stroke: 'var(--border-subtle)' }} />
              <Tooltip
                contentStyle={chartTooltipStyle}
                labelStyle={chartTooltipLabel}
                itemStyle={chartTooltipItem}
                cursor={{ fill: 'var(--surface-2)', opacity: 0.5 }}
                formatter={(v: number, _: string, entry: { payload?: PipelineFunnelStage }) => [
                  entry.payload?.conversion_rate != null
                    ? `${v} (${entry.payload.conversion_rate}% conversion)`
                    : v,
                  'Applications',
                ]}
              />
              <Bar dataKey="count" fill="url(#gradFunnel)" radius={[0, 6, 6, 0]} animationDuration={900}>
                <LabelList dataKey="count" position="right" style={{ fontSize: 10, fill: 'var(--ink-secondary)', fontWeight: 600 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Industry breakdown */}
        <div className="card overflow-hidden">
          <div className="bg-surface-2 px-5 py-3 border-b border-border-subtle">
            <span className="text-caption text-ink-secondary uppercase tracking-wider">Industry Breakdown</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-small">
              <thead className="bg-surface-2">
                <tr>
                  {['Industry', 'Apps', 'Avg Risk'].map(h => (
                    <th key={h} className="px-4 py-2 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {industryData.slice(0, 8).map(row => (
                  <tr key={row.industry} className="hover:bg-surface-2 transition-colors">
                    <td className="px-4 py-2.5 font-medium capitalize text-ink-primary">{row.industry.replace('_', ' ')}</td>
                    <td className="px-4 py-2.5 tabular text-ink-secondary">{row.count}</td>
                    <td className="px-4 py-2.5 tabular text-ink-secondary">
                      {row.avg_risk_score != null ? row.avg_risk_score.toFixed(1) : '—'}
                    </td>
                  </tr>
                ))}
                {industryData.length === 0 && (
                  <tr><td colSpan={3} className="px-4 py-6 text-center text-ink-muted text-small">No data.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Rule triggers */}
        <div className="card overflow-hidden">
          <div className="bg-surface-2 px-5 py-3 border-b border-border-subtle">
            <span className="text-caption text-ink-secondary uppercase tracking-wider">Top Rule Triggers</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-small">
              <thead className="bg-surface-2">
                <tr>
                  {['Rule', 'Category', 'Triggers', 'Type'].map(h => (
                    <th key={h} className="px-4 py-2 text-left text-caption text-ink-secondary border-b border-border font-bold uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {ruleTriggers.slice(0, 8).map(row => (
                  <tr key={row.rule_id} className="hover:bg-surface-2 transition-colors">
                    <td className="px-4 py-2.5 font-medium text-ink-primary truncate max-w-[180px]">{row.rule_name}</td>
                    <td className="px-4 py-2.5 text-ink-secondary capitalize">{row.category.replace('_', ' ')}</td>
                    <td className="px-4 py-2.5 tabular text-ink-secondary">{row.trigger_count}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase ${
                        row.is_mandatory
                          ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                      }`}>
                        {row.is_mandatory ? 'Mandatory' : 'Advisory'}
                      </span>
                    </td>
                  </tr>
                ))}
                {ruleTriggers.length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-6 text-center text-ink-muted text-small">No rule trigger data.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Additional stats */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="card px-5 py-4">
            <div className="text-xl font-bold tabular text-ink-primary">
              {summary.avg_processing_days != null ? `${summary.avg_processing_days.toFixed(1)} days` : '—'}
            </div>
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted mt-1">Avg Processing Time</div>
          </div>
          <div className="card px-5 py-4">
            <div className="text-xl font-bold tabular text-ink-primary">
              {summary.avg_loan_amount_requested != null ? fmtRM(summary.avg_loan_amount_requested) : '—'}
            </div>
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted mt-1">Avg Loan Requested</div>
          </div>
          <div className="card px-5 py-4">
            <div className={`text-xl font-bold tabular ${summary.models_trained ? 'text-green-700 dark:text-green-400' : 'text-amber-700 dark:text-amber-400'}`}>
              {summary.models_trained ? 'Trained' : 'Not trained'}
            </div>
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted mt-1">ML Model Status</div>
          </div>
        </div>
      )}
    </div>
  )
}
