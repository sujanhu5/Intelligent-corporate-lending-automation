import { useEffect, useState } from 'react'
import { predictionsApi } from '@/api/predictions'
import type { ModelStatus } from '@/types'
import PageHeader from '@/components/ui/PageHeader'
import Button from '@/components/ui/Button'
import StatCard from '@/components/ui/StatCard'
import { PageLoader } from '@/components/ui/Spinner'
import { useToast } from '@/components/ui/Toast'
import { extractError } from '@/api/client'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, Legend,
} from 'recharts'

export default function MLModels() {
  const [status, setStatus] = useState<ModelStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [training, setTraining] = useState(false)
  const { success, error } = useToast()

  const load = () => {
    setLoading(true)
    predictionsApi.modelStatus().then(setStatus).catch(err => error(extractError(err))).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleTrain = async () => {
    setTraining(true)
    try {
      const res = await predictionsApi.train()
      success(`Models trained on ${res.training_samples.toLocaleString()} samples.`)
      load()
    } catch (err) {
      error(extractError(err))
    } finally {
      setTraining(false)
    }
  }

  if (loading) return <PageLoader />

  const metrics = status?.model_metrics ?? null
  const modelNames = metrics ? Object.keys(metrics) : []
  const friendlyName = (n: string) => n.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  const barData = modelNames.map(n => {
    const m = metrics![n]
    return {
      name: friendlyName(n),
      'Accuracy': +(m.accuracy * 100).toFixed(2),
      'ROC-AUC':  +(m.roc_auc  * 100).toFixed(2),
      'CV Mean':  +(m.cv_roc_auc_mean * 100).toFixed(2),
    }
  })

  const radarData = ['Accuracy', 'ROC-AUC', 'CV Mean'].map(metric => ({
    metric,
    ...Object.fromEntries(modelNames.map(n => {
      const m = metrics![n]
      const val = metric === 'Accuracy' ? m.accuracy : metric === 'ROC-AUC' ? m.roc_auc : m.cv_roc_auc_mean
      return [friendlyName(n), +(val * 100).toFixed(2)]
    })),
  }))

  const COLORS = ['var(--cr-500)', 'var(--cr-300)', '#F4A300']

  return (
    <div>
      <PageHeader
        title="ML Models"
        subtitle="Train and monitor risk prediction models on the bankruptcy dataset."
        actions={
          <Button onClick={handleTrain} loading={training}>
            {training ? 'Training…' : 'Retrain Models'}
          </Button>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Model Status" value={status?.models_trained ? 'Trained' : 'Not Trained'}
          icon={status?.models_trained ? '✓' : '○'} />
        <StatCard title="Feature Count" value={status?.selected_feature_count ?? '—'} icon="🔢" />
        <StatCard title="Training Samples" value={status?.total_training_samples?.toLocaleString() ?? '—'} icon="📊" />
        <StatCard
          title="Last Trained"
          value={status?.trained_at ? new Date(status.trained_at).toLocaleDateString() : '—'}
          icon="🕐"
        />
      </div>

      {!status?.models_trained ? (
        <div className="card flex flex-col items-center justify-center py-20 gap-4">
          <span className="text-4xl">🤖</span>
          <p className="text-h4 text-ink-primary">No models trained yet</p>
          <p className="text-small text-ink-secondary">Click "Retrain Models" to train on the bankruptcy dataset.</p>
          <Button onClick={handleTrain} loading={training}>Train Now</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bar comparison */}
          <div className="card p-5">
            <h3 className="text-h4 mb-4">Model Comparison</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={barData} barGap={4}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis domain={[50, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip formatter={(v: number) => [`${v}%`]} />
                <Legend iconType="circle" iconSize={8} />
                {['Accuracy', 'ROC-AUC', 'CV Mean'].map((k, i) => (
                  <Bar key={k} dataKey={k} fill={COLORS[i]} radius={[3, 3, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Radar */}
          <div className="card p-5">
            <h3 className="text-h4 mb-4">Performance Radar</h3>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[60, 100]} tick={{ fontSize: 10 }} />
                {modelNames.map((n, i) => (
                  <Radar key={n} name={friendlyName(n)} dataKey={friendlyName(n)}
                    stroke={COLORS[i]} fill={COLORS[i]} fillOpacity={0.15} />
                ))}
                <Tooltip formatter={(v: number) => [`${v}%`]} />
                <Legend iconType="circle" iconSize={8} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Per-model detail */}
          {modelNames.map(n => {
            const m = metrics![n]
            const isBest = status?.best_model === n
            return (
              <div key={n} className={`card p-5 ${isBest ? 'ring-2 ring-primary/40' : ''}`}>
                <h3 className="text-h4 mb-3 flex items-center gap-2">
                  {friendlyName(n)}
                  {isBest && (
                    <span className="gradient-orange text-white text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full font-mono">★ Best</span>
                  )}
                </h3>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Accuracy',  value: `${(m.accuracy * 100).toFixed(2)}%` },
                    { label: 'ROC-AUC',   value: `${(m.roc_auc  * 100).toFixed(2)}%` },
                    { label: 'CV Mean',   value: `${(m.cv_roc_auc_mean * 100).toFixed(2)}%` },
                    { label: 'Precision', value: `${(m.precision * 100).toFixed(2)}%` },
                    { label: 'Recall',    value: `${(m.recall * 100).toFixed(2)}%` },
                    { label: 'F1 Score',  value: `${(m.f1 * 100).toFixed(2)}%` },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-surface-2 rounded-lg p-3 text-center border border-border-subtle">
                      <div className="text-lg font-extrabold tabular text-ink-primary font-mono leading-none">{value}</div>
                      <div className="text-[9px] font-bold uppercase tracking-wider text-ink-muted mt-1.5 font-mono">{label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
