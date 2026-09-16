import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  AreaChart, Area, CartesianGrid,
} from 'recharts'
import { applicationsApi } from '@/api/applications'
import { predictionsApi } from '@/api/predictions'
import { analyticsApi } from '@/api/analytics'
import type {
  DashboardStats, ModelStatus, AnalyticsSummary,
  ApplicationTrend, RiskDistribution, IndustryBreakdown,
  LoanPurposeBreakdown, PipelineFunnelStage, PipelineMetrics,
} from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import { PageLoader } from '@/components/ui/Spinner'
import Button from '@/components/ui/Button'
import { useAuthStore } from '@/store/auth'

const PIE_COLORS = ['#12A150', '#E5484D', '#F4A300', '#EF6C1A', '#C9C0B4']
const TREND_COLORS = { submitted: '#3B82F6', approved: '#12A150', rejected: '#E5484D' }
const RISK_COLORS: Record<string, string> = {
  very_low: '#12A150', low: '#34D399', medium: '#F4A300', high: '#EF6C1A', very_high: '#E5484D',
}

function MetricCard({ label, value, subtitle, severity }: {
  label: string; value: string | number; subtitle?: string; severity?: 'good' | 'warn' | 'critical' | 'neutral'
}) {
  const dot = { good: 'bg-green-500', warn: 'bg-amber-500', critical: 'bg-red-500', neutral: 'bg-ink-muted' }[severity ?? 'neutral']
  return (
    <div className="card p-4 flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${dot} flex-shrink-0`} />
        <span className="text-[10px] font-bold uppercase tracking-wider text-ink-muted font-mono truncate">{label}</span>
      </div>
      <div className="text-2xl font-extrabold text-ink-primary tabular font-mono leading-none">{value}</div>
      {subtitle && <div className="text-[11px] text-ink-secondary font-mono">{subtitle}</div>}
    </div>
  )
}

function ChartCard({ title, subtitle, children, className = '' }: {
  title: string; subtitle?: string; children: React.ReactNode; className?: string
}) {
  return (
    <div className={`card p-5 ${className}`}>
      <div className="mb-4">
        <h3 className="text-sm font-bold text-ink-primary font-mono">{title}</h3>
        {subtitle && <p className="text-[11px] text-ink-muted mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function FunnelBar({ label, count, rate, maxCount }: {
  label: string; count: number; rate: number | null; maxCount: number
}) {
  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0
  return (
    <div className="flex items-center gap-3">
      <div className="w-20 text-[11px] font-mono text-ink-secondary text-right flex-shrink-0">{label}</div>
      <div className="flex-1 h-6 bg-surface-2 rounded-md overflow-hidden relative">
        <div className="h-full gradient-orange rounded-md transition-all" style={{ width: `${pct}%` }} />
        <span className="absolute inset-y-0 left-2 flex items-center text-[10px] font-bold font-mono text-ink-primary">
          {count}
        </span>
      </div>
      {rate != null && (
        <div className="w-12 text-[10px] font-bold font-mono text-ink-muted text-right flex-shrink-0">
          {rate.toFixed(0)}%
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null)
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [trends, setTrends] = useState<ApplicationTrend[]>([])
  const [riskDist, setRiskDist] = useState<RiskDistribution[]>([])
  const [industryData, setIndustryData] = useState<IndustryBreakdown[]>([])
  const [purposeData, setPurposeData] = useState<LoanPurposeBreakdown[]>([])
  const [funnel, setFunnel] = useState<PipelineFunnelStage[]>([])
  const [pipelineMetrics, setPipelineMetrics] = useState<PipelineMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    const fetches: Promise<any>[] = [
      applicationsApi.dashboardStats(),
      isAdmin ? predictionsApi.modelStatus() : Promise.resolve(null),
      analyticsApi.summary(),
      analyticsApi.trends(30),
      analyticsApi.riskDistribution(),
      analyticsApi.industryBreakdown(),
      analyticsApi.loanPurposeBreakdown(),
      analyticsApi.pipelineFunnel(),
      analyticsApi.pipelineMetrics(),
    ]
    Promise.all(fetches)
      .then(([s, m, sum, t, r, ind, purp, f, pm]) => {
        setStats(s); setModelStatus(m); setSummary(sum)
        setTrends(t); setRiskDist(r); setIndustryData(ind)
        setPurposeData(purp); setFunnel(f); setPipelineMetrics(pm)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <PageLoader />

  const approvalRate = stats?.total ? Math.round((stats.approved / stats.total) * 100) : 0
  const rejectionRate = stats?.total ? Math.round((stats.rejected / stats.total) * 100) : 0
  const systemHealth = isAdmin
    ? (modelStatus?.models_trained ? 'Operational' : 'Models Not Trained')
    : 'Online'
  const healthSeverity: 'good' | 'warn' | 'critical' = isAdmin
    ? (modelStatus?.models_trained ? 'good' : 'warn')
    : 'good'

  const pieData = stats ? [
    { name: 'Approved', value: stats.approved },
    { name: 'Rejected', value: stats.rejected },
    { name: 'Manual Review', value: stats.manual_review },
    { name: 'In Pipeline', value: stats.in_pipeline },
    { name: 'Draft', value: stats.draft },
  ].filter(d => d.value > 0) : []

  const funnelMax = funnel.length > 0 ? Math.max(...funnel.map(f => f.count)) : 0

  return (
    <div>
      <PageHeader
        title={user?.role === 'admin' ? 'Admin Command Center' : 'Officer Dashboard'}
        subtitle={`Welcome back, ${user?.full_name ?? 'User'}. ${user?.role === 'admin' ? "Here's your real-time system overview." : "Here's your application overview."}`}
        eyebrow={user?.role === 'admin' ? 'System Administrator' : 'Loan Officer'}
        actions={
          <div className="flex items-center gap-2">
            {user?.role === 'admin' && <Button variant="secondary" size="sm" onClick={() => navigate('/analytics')}>Analytics</Button>}
            <Button onClick={() => navigate('/applications/new')}>+ New Application</Button>
          </div>
        }
      />

      {/* System health bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        <MetricCard label="System Status" value={systemHealth} severity={healthSeverity} />
        <MetricCard label="Total Applications" value={stats?.total ?? 0} severity="neutral" />
        <MetricCard
          label="Approval Rate"
          value={`${approvalRate}%`}
          severity={approvalRate >= 50 ? 'good' : approvalRate >= 30 ? 'warn' : 'critical'}
          subtitle={`${stats?.approved ?? 0} of ${stats?.total ?? 0}`}
        />
        <MetricCard
          label="Rejection Rate"
          value={`${rejectionRate}%`}
          severity={rejectionRate <= 20 ? 'good' : rejectionRate <= 40 ? 'warn' : 'critical'}
          subtitle={`${stats?.rejected ?? 0} rejected`}
        />
        <MetricCard
          label="Avg Risk Score"
          value={stats?.avg_risk_score != null ? stats.avg_risk_score.toFixed(1) : '—'}
          severity={
            stats?.avg_risk_score == null ? 'neutral'
            : stats.avg_risk_score <= 30 ? 'good'
            : stats.avg_risk_score <= 60 ? 'warn'
            : 'critical'
          }
          subtitle="Score 0–100"
        />
        <MetricCard
          label="Loan Volume"
          value={summary?.total_loan_amount_approved
            ? `₹${(summary.total_loan_amount_approved / 1e7).toFixed(1)}Cr`
            : '0'}
          severity="neutral"
          subtitle="Approved amount"
        />
      </div>

      {/* Pipeline status quick strip */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {[
          { label: 'Draft', value: stats?.draft ?? 0 },
          { label: 'Submitted', value: stats?.submitted ?? 0 },
          { label: 'In Pipeline', value: stats?.in_pipeline ?? 0 },
          { label: 'Manual Review', value: stats?.manual_review ?? 0 },
          { label: 'Approved', value: stats?.approved ?? 0 },
          { label: 'Rejected', value: stats?.rejected ?? 0 },
        ].map(item => (
          <div
            key={item.label}
            className="card card-hover px-4 py-3 text-center cursor-pointer"
            onClick={() => navigate(`/applications?status=${item.label.toLowerCase().replace(' ', '_')}`)}
          >
            <div className="text-xl font-extrabold text-ink-primary tabular font-mono leading-none">{item.value}</div>
            <div className="text-[9px] font-bold uppercase tracking-wider text-ink-muted mt-1 font-mono">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Row 1: Trends + Decision Mix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
        <ChartCard title="Application Trends" subtitle="Last 30 days" className="lg:col-span-2">
          {trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trends} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradSubmitted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={TREND_COLORS.submitted} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={TREND_COLORS.submitted} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradApproved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={TREND_COLORS.approved} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={TREND_COLORS.approved} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid var(--border-subtle)' }}
                  labelFormatter={l => `Date: ${l}`}
                />
                <Area type="monotone" dataKey="submitted" stroke={TREND_COLORS.submitted} fill="url(#gradSubmitted)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="approved" stroke={TREND_COLORS.approved} fill="url(#gradApproved)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="rejected" stroke={TREND_COLORS.rejected} fill="none" strokeWidth={2} strokeDasharray="4 3" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-ink-muted text-small">No trend data yet.</div>
          )}
        </ChartCard>

        <ChartCard title="Decision Distribution">
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={230}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%" cy="50%"
                  outerRadius={82}
                  innerRadius={46}
                  paddingAngle={3}
                  stroke="var(--surface-1)"
                  strokeWidth={2}
                  animationDuration={900}
                  label={({ percent }) => percent && percent > 0.06 ? `${(percent * 100).toFixed(0)}%` : ''}
                  labelLine={false}
                >
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--surface-1)', border: '1px solid var(--border-subtle)', borderRadius: 8, fontSize: 11, boxShadow: '0 6px 18px -8px rgba(0,0,0,0.25)' }}
                  formatter={(v: number) => [v, 'Applications']}
                />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 10 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-ink-muted text-small">No data.</div>
          )}
        </ChartCard>
      </div>

      {/* Row 2: Risk Distribution + Pipeline Funnel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
        <ChartCard title="Risk Score Distribution" subtitle="ML-predicted risk levels">
          {riskDist.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={riskDist} margin={{ top: 14, left: -14, right: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-subtle)" strokeOpacity={0.5} vertical={false} />
                <XAxis
                  dataKey="risk_level"
                  tick={{ fontSize: 10, fill: 'var(--ink-muted)' }}
                  tickFormatter={r => r.replace('_', ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--border-subtle)' }}
                />
                <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: 'var(--ink-muted)' }} tickLine={false} axisLine={false} width={28} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--surface-1)', border: '1px solid var(--border-subtle)', borderRadius: 8, fontSize: 11, boxShadow: '0 6px 18px -8px rgba(0,0,0,0.25)' }}
                  cursor={{ fill: 'var(--surface-2)', opacity: 0.5 }}
                  formatter={(v: number, _: unknown, entry: { payload: RiskDistribution }) => [
                    `${v} (${entry.payload.percentage.toFixed(1)}%)`, 'Applications',
                  ]}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} animationDuration={800}>
                  {riskDist.map((d, i) => (
                    <Cell key={i} fill={RISK_COLORS[d.risk_level] ?? '#888'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-ink-muted text-small">No risk data yet.</div>
          )}
        </ChartCard>

        <ChartCard title="Pipeline Funnel" subtitle="Stage-by-stage throughput">
          {funnel.length > 0 ? (
            <div className="flex flex-col gap-2.5">
              {funnel.map(stage => (
                <FunnelBar
                  key={stage.stage}
                  label={stage.label}
                  count={stage.count}
                  rate={stage.conversion_rate}
                  maxCount={funnelMax}
                />
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-ink-muted text-small">No pipeline data.</div>
          )}
        </ChartCard>
      </div>

      {/* Row 3: Industry breakdown + Loan Purpose */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
        <ChartCard title="Industry Breakdown" subtitle="Applications by sector">
          {industryData.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-ink-muted border-b border-border-subtle">
                    <th className="text-left py-2 pr-3">Industry</th>
                    <th className="text-right py-2 px-2">Apps</th>
                    <th className="text-right py-2 px-2">Total Loan (Cr)</th>
                    <th className="text-right py-2 pl-2">Avg Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {industryData.map(row => (
                    <tr key={row.industry} className="border-b border-border-subtle/50 hover:bg-surface-2 transition-colors">
                      <td className="py-2 pr-3 text-ink-primary font-semibold capitalize">{row.industry.replace(/_/g, ' ')}</td>
                      <td className="py-2 px-2 text-right tabular text-ink-secondary">{row.count}</td>
                      <td className="py-2 px-2 text-right tabular text-ink-secondary">
                        ₹{(row.total_loan_amount / 1e7).toFixed(2)}Cr
                      </td>
                      <td className="py-2 pl-2 text-right tabular">
                        {row.avg_risk_score != null ? (
                          <span className={
                            row.avg_risk_score <= 30 ? 'text-green-600'
                            : row.avg_risk_score <= 60 ? 'text-amber-600'
                            : 'text-red-600'
                          }>
                            {row.avg_risk_score.toFixed(1)}
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[160px] text-ink-muted text-small">No industry data.</div>
          )}
        </ChartCard>

        <ChartCard title="Loan Purpose Analysis" subtitle="Breakdown by purpose">
          {purposeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={purposeData.map(d => ({
                name: d.purpose.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                'Approval Rate': +(d.approval_rate * 100).toFixed(1),
                Applications: d.count,
              }))} margin={{ top: 10, left: -14, right: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradPurpose" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="var(--cr-500)" stopOpacity={1} />
                    <stop offset="100%" stopColor="var(--cr-500)" stopOpacity={0.55} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-subtle)" strokeOpacity={0.5} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--ink-muted)' }} angle={-15} textAnchor="end" height={60} tickLine={false} axisLine={{ stroke: 'var(--border-subtle)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--ink-muted)' }} tickLine={false} axisLine={false} width={28} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--surface-1)', border: '1px solid var(--border-subtle)', borderRadius: 8, fontSize: 11, boxShadow: '0 6px 18px -8px rgba(0,0,0,0.25)' }}
                  cursor={{ fill: 'var(--surface-2)', opacity: 0.5 }}
                />
                <Bar dataKey="Applications" fill="url(#gradPurpose)" radius={[6, 6, 0, 0]} animationDuration={800} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-ink-muted text-small">No purpose data.</div>
          )}
        </ChartCard>
      </div>

      {/* Row 4: Pipeline Metrics + Automation Status (admin only) */}
      {isAdmin && <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
        <ChartCard title="Pipeline Stage Metrics" subtitle="Completion rates by stage">
          {pipelineMetrics && Object.keys(pipelineMetrics.stage_completion).length > 0 ? (
            <div className="flex flex-col gap-3">
              {Object.entries(pipelineMetrics.stage_completion).map(([stage, count]) => {
                const convRate = pipelineMetrics.stage_conversion[stage]
                const isBottleneck = pipelineMetrics.bottleneck_stage === stage
                return (
                  <div key={stage} className={`flex items-center gap-3 p-2.5 rounded-lg ${isBottleneck ? 'bg-red-50 border border-red-200' : 'bg-surface-2'}`}>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-ink-primary font-mono capitalize">{stage.replace(/_/g, ' ')}</span>
                        {isBottleneck && (
                          <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-red-100 text-red-700">Bottleneck</span>
                        )}
                      </div>
                      <div className="text-[11px] text-ink-muted font-mono mt-0.5">
                        {count} completed
                        {convRate != null && ` · ${convRate.toFixed(0)}% conversion`}
                      </div>
                    </div>
                    <div className="w-16 text-right">
                      <span className={`text-sm font-bold font-mono tabular ${
                        convRate != null ? (convRate >= 80 ? 'text-green-600' : convRate >= 50 ? 'text-amber-600' : 'text-red-600') : 'text-ink-muted'
                      }`}>
                        {convRate != null ? `${convRate.toFixed(0)}%` : '—'}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-ink-muted text-small">No pipeline metrics.</div>
          )}
        </ChartCard>

        <ChartCard title="Automation Status" subtitle="Credit assessment engine health">
          <div className="flex flex-col gap-3">
            <div className={`flex items-center gap-3 p-3 rounded-lg ${modelStatus?.models_trained ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
              <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${modelStatus?.models_trained ? 'bg-green-500' : 'bg-amber-500'}`} />
              <div className="flex-1">
                <div className="text-xs font-bold text-ink-primary">Risk Scoring Engine</div>
                <div className="text-[11px] text-ink-secondary mt-0.5">
                  {modelStatus?.models_trained ? 'Active — processing applications automatically' : 'Not initialized — contact system admin'}
                </div>
              </div>
            </div>
            {modelStatus?.trained_at && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-2">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500 flex-shrink-0" />
                <div className="flex-1">
                  <div className="text-xs font-bold text-ink-primary">Last Calibrated</div>
                  <div className="text-[11px] text-ink-secondary mt-0.5">
                    {new Date(modelStatus.trained_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                  </div>
                </div>
              </div>
            )}
            {modelStatus?.best_roc_auc != null && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-2">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500 flex-shrink-0" />
                <div className="flex-1">
                  <div className="text-xs font-bold text-ink-primary">Prediction Accuracy</div>
                  <div className="text-[11px] text-ink-secondary mt-0.5">
                    {(modelStatus.best_roc_auc * 100).toFixed(1)}% confidence score
                  </div>
                </div>
              </div>
            )}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-2">
              <span className="w-2.5 h-2.5 rounded-full bg-green-500 flex-shrink-0" />
              <div className="flex-1">
                <div className="text-xs font-bold text-ink-primary">Document OCR</div>
                <div className="text-[11px] text-ink-secondary mt-0.5">Active — extracts financial data from uploaded PDFs</div>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-2">
              <span className="w-2.5 h-2.5 rounded-full bg-green-500 flex-shrink-0" />
              <div className="flex-1">
                <div className="text-xs font-bold text-ink-primary">Rule Engine</div>
                <div className="text-[11px] text-ink-secondary mt-0.5">Active — evaluating credit policies on every application</div>
              </div>
            </div>
          </div>
        </ChartCard>
      </div>}

      {/* Quick actions */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {([
          { label: 'Companies', desc: 'Manage registered companies', icon: '🏢', path: '/companies' },
          { label: 'Applications', desc: 'Review loan applications', icon: '📋', path: '/applications' },
          isAdmin ? { label: 'Rule Engine', desc: 'Configure credit rules', icon: '⚙', path: '/rules' } : null,
          { label: 'Pipeline', desc: 'Run assessment pipeline', icon: '▤', path: '/pipeline' },
        ].filter(Boolean) as { label: string; desc: string; icon: string; path: string }[]).map(item => (
          <div
            key={item.label}
            onClick={() => navigate(item.path)}
            className="card card-hover p-4 cursor-pointer"
          >
            <div className="text-lg mb-2">{item.icon}</div>
            <div className="text-xs font-bold text-ink-primary font-mono">{item.label}</div>
            <div className="text-[11px] text-ink-secondary mt-0.5">{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
