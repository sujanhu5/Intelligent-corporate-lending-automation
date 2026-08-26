import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import { applicationsApi } from '@/api/applications'
import { predictionsApi } from '@/api/predictions'
import type { DashboardStats, ModelStatus } from '@/types'
import StatCard from '@/components/ui/StatCard'
import PageHeader from '@/components/ui/PageHeader'
import { PageLoader } from '@/components/ui/Spinner'
import Button from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'

const PIE_COLORS = ['#12A150', '#E5484D', '#F4A300', '#EF6C1A', '#C9C0B4']

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null)
  const [training, setTraining] = useState(false)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { success, error } = useToast()

  useEffect(() => {
    Promise.all([applicationsApi.dashboardStats(), predictionsApi.modelStatus()])
      .then(([s, m]) => { setStats(s); setModelStatus(m) })
      .finally(() => setLoading(false))
  }, [])

  const handleTrain = async () => {
    setTraining(true)
    try {
      await predictionsApi.train()
      const m = await predictionsApi.modelStatus()
      setModelStatus(m)
      success('Models retrained successfully.')
    } catch (err) {
      error(extractError(err))
    } finally {
      setTraining(false)
    }
  }

  if (loading) return <PageLoader />

  const pieData = stats ? [
    { name: 'Approved',      value: stats.approved },
    { name: 'Rejected',      value: stats.rejected },
    { name: 'Manual Review', value: stats.manual_review },
    { name: 'In Pipeline',   value: stats.in_pipeline },
    { name: 'Draft',         value: stats.draft },
  ].filter(d => d.value > 0) : []

  const barData = modelStatus?.model_metrics
    ? Object.entries(modelStatus.model_metrics).map(([name, m]) => ({
        name: name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        'Accuracy': +(m.accuracy * 100).toFixed(1),
        'ROC-AUC':  +(m.roc_auc  * 100).toFixed(1),
      }))
    : []

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Real-time overview of the lending pipeline."
        actions={
          <Button onClick={() => navigate('/applications/new')}>
            + New Application
          </Button>
        }
      />

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Total Applications" value={stats?.total ?? 0} icon="📋" />
        <StatCard title="Approved" value={stats?.approved ?? 0} icon="✓"
          change={`${stats?.total ? Math.round((stats.approved / stats.total) * 100) : 0}% approval rate`}
          changeType="up" />
        <StatCard title="Pending Review" value={(stats?.submitted ?? 0) + (stats?.in_pipeline ?? 0)} icon="⏳" />
        <StatCard
          title="Avg Risk Score"
          value={stats?.avg_risk_score != null ? stats.avg_risk_score.toFixed(1) : '—'}
          icon="📊"
          subtitle="Composite 0–100"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Pie chart */}
        <div className="card p-5">
          <h3 className="text-h4 text-ink-primary mb-4">Application Status Mix</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={82} innerRadius={48} paddingAngle={2} stroke="none">
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v: number) => [v, 'Applications']} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-ink-muted text-small">
              No applications yet.
            </div>
          )}
        </div>

        {/* Model metrics */}
        <div className="card p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-h4 text-ink-primary">ML Model Performance</h3>
              {modelStatus?.trained_at && (
                <p className="text-[11px] text-ink-muted mt-0.5">
                  Last trained {new Date(modelStatus.trained_at).toLocaleDateString()}
                </p>
              )}
            </div>
            <Button variant="secondary" size="sm" onClick={handleTrain} loading={training}>
              Retrain
            </Button>
          </div>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData} barGap={4}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis domain={[50, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip formatter={(v: number) => [`${v}%`]} />
                <Bar dataKey="Accuracy" fill="var(--cr-500)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="ROC-AUC"  fill="var(--cr-300)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex flex-col items-center justify-center h-[200px] gap-3">
              <p className="text-ink-muted text-small">Models not trained yet.</p>
              <Button size="sm" onClick={handleTrain} loading={training}>Train Now</Button>
            </div>
          )}
        </div>
      </div>

      {/* Quick stats row */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: 'Draft',          value: stats?.draft ?? 0 },
          { label: 'Submitted',      value: stats?.submitted ?? 0 },
          { label: 'In Pipeline',    value: stats?.in_pipeline ?? 0 },
          { label: 'Manual Review',  value: stats?.manual_review ?? 0 },
          { label: 'Approved',       value: stats?.approved ?? 0 },
          { label: 'Rejected',       value: stats?.rejected ?? 0 },
        ].map(item => (
          <div
            key={item.label}
            className="card card-hover px-4 py-3.5 text-center cursor-pointer"
            onClick={() => navigate(`/applications?status=${item.label.toLowerCase().replace(' ', '_')}`)}
          >
            <div className="text-2xl font-extrabold text-ink-primary tabular font-mono leading-none">{item.value}</div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-ink-muted mt-1.5 font-mono">{item.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
