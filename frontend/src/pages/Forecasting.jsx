import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Card from '../components/ui/Card'
import StatCard from '../components/ui/StatCard'
import { forecastingMock } from '../data/forecastingMock'
import { useAuth } from '../context/AuthContext'
import { listEntities, runForecast, listForecasts } from '../api/intelligence'

const metricOptions = [
  { label: 'Production', value: 'production' },
  { label: 'Dispatch', value: 'dispatch' },
]

export default function ForecastingPage({ hideHeader = false }) {
  const { token } = useAuth()

  // --- Entity list (subsidiaries from backend, fallback to forecastingMock keys) ---
  const [entities, setEntities] = useState(
    Object.keys(forecastingMock).map((k) => ({ id: k, name: k }))
  )
  const [selectedEntityId, setSelectedEntityId] = useState('CCL')
  const [selectedMetric, setSelectedMetric] = useState('production')
  const [forecastRunning, setForecastRunning] = useState(false)
  const [forecastToast, setForecastToast] = useState('')

  // Load real entity list on mount
  useEffect(() => {
    if (!token) return
    listEntities(token, { entityType: 'subsidiary', pageSize: 50 })
      .then((r) => {
        const items = r.items ?? []
        if (items.length > 0) {
          setEntities(items.map((e) => ({ id: e.id, name: e.name ?? e.short_name ?? e.id })))
          setSelectedEntityId(items[0].id)
        }
      })
      .catch(() => { /* keep mock entity list */ })
  }, [token])

  // Chart data — use mock until a real forecast is run
  const mockSubsidiary = Object.keys(forecastingMock)[0]
  const [chartData, setChartData] = useState(
    forecastingMock[mockSubsidiary]?.[selectedMetric]?.points?.map((p) => ({
      ...p,
      lower: p.lower ?? p.lowerBound ?? null,
      upper: p.upper ?? p.upperBound ?? null,
    })) ?? []
  )

  const handleRunForecast = useCallback(async () => {
    if (!token || !selectedEntityId) return
    setForecastRunning(true)
    setForecastToast('Running forecast…')
    try {
      const result = await runForecast(token, { entityId: selectedEntityId, metric: selectedMetric, horizonYears: 3 })
      const points = (result.forecast_data ?? []).map((d) => ({
        month: d.period_label ?? d.year,
        actual: d.actual_value ?? null,
        forecast: d.predicted_value,
        lower: d.lower_bound ?? null,
        upper: d.upper_bound ?? null,
      }))
      if (points.length > 0) setChartData(points)
      setForecastToast('Forecast complete!')
    } catch (err) {
      setForecastToast(`Forecast failed: ${err.message ?? 'Unknown error'}`)
    } finally {
      setForecastRunning(false)
      window.setTimeout(() => setForecastToast(''), 3000)
    }
  }, [token, selectedEntityId, selectedMetric])

  const latestPoint = chartData[chartData.length - 1]
  const previousPoint = chartData[chartData.length - 2] || chartData[chartData.length - 1]
  const lastForecast = latestPoint?.forecast ?? latestPoint?.actual ?? 0
  const priorForecast = previousPoint?.forecast ?? previousPoint?.actual ?? 0
  const delta = priorForecast === 0 ? 0 : ((lastForecast - priorForecast) / priorForecast) * 100
  const confidence = latestPoint?.lower && latestPoint?.upper ? Math.round(((lastForecast - latestPoint.lower) / (latestPoint.upper - latestPoint.lower)) * 100) : 88

  return (
    <div className="forecasting-page">
      {!hideHeader && (
        <div className="page-header">
          <div>
            <p className="eyebrow">Forecasting engine</p>
            <h1>Operational forecast outlook</h1>
          </div>
        </div>
      )}

      <Card className="forecasting-card">
        <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <p className="eyebrow">Scenario control</p>
            <h2>Forecast assumptions</h2>
          </div>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 700,
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--purple-100)',
              color: 'var(--purple-500)',
              border: '1px solid var(--tone-ai-border)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            🤖 Model-based forecast
          </span>
        </div>

        <div className="forecasting-controls">
          <div className="ui-field">
            <label className="ui-field__label" htmlFor="subsidiary-select">
              Subsidiary / Entity
            </label>
            <select
              id="subsidiary-select"
              className="ui-select"
              value={selectedEntityId}
              onChange={(event) => setSelectedEntityId(event.target.value)}
            >
              {entities.map((entity) => (
                <option key={entity.id} value={entity.id}>
                  {entity.name}
                </option>
              ))}
            </select>
          </div>

          <div className="ui-field">
            <label className="ui-field__label" htmlFor="metric-select">
              Metric
            </label>
            <select
              id="metric-select"
              className="ui-select"
              value={selectedMetric}
              onChange={(event) => setSelectedMetric(event.target.value)}
            >
              {metricOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="ui-field" style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              type="button"
              className="ui-button ui-button--primary"
              onClick={handleRunForecast}
              disabled={forecastRunning}
              style={{
                padding: '9px 20px', borderRadius: 'var(--radius-sm)', border: 'none',
                background: forecastRunning ? 'rgba(18,58,62,0.4)' : '#123a3e',
                color: '#fff', fontSize: '13px', fontWeight: 700, cursor: forecastRunning ? 'not-allowed' : 'pointer',
              }}
            >
              {forecastRunning ? 'Running…' : 'Run Forecast'}
            </button>
          </div>
        </div>
        {forecastToast && (
          <div style={{ marginTop: '10px', fontSize: '12px', color: forecastToast.startsWith('Forecast failed') ? '#dc2626' : '#16a34a', fontWeight: 600 }}>
            {forecastToast}
          </div>
        )}
      </Card>

      <div className="forecasting-layout">
        <Card className="forecasting-card forecasting-card--chart">
          <div className="section-header">
            <div>
              <p className="eyebrow">Forecast trend</p>
              <h2>{entities.find(e => e.id === selectedEntityId)?.name ?? selectedEntityId} {selectedMetric === 'production' ? 'production' : 'dispatch'} outlook</h2>
            </div>
          </div>

          <div className="forecasting-chart">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="forecastBandGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#3ab7d0" stopOpacity={0.24} />
                    <stop offset="100%" stopColor="#3ab7d0" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#d7e0ea" />
                <XAxis dataKey="period" tickLine={false} axisLine={false} tick={{ fill: '#53657b', fontSize: 11 }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fill: '#53657b', fontSize: 11 }} />
                <Tooltip
                  formatter={(value) => [`${Number(value).toFixed(1)}`, '']}
                  contentStyle={{
                    borderRadius: 12,
                    border: '1px solid #d7e0ea',
                    boxShadow: '0 8px 24px rgba(16, 31, 52, 0.08)',
                  }}
                />
                <Area type="monotone" dataKey="lower" stackId="band" fill="url(#forecastBandGradient)" stroke="none" fillOpacity={1} />
                <Area type="monotone" dataKey="upper" stackId="band" fill="url(#forecastBandGradient)" stroke="none" fillOpacity={0.8} />
                <Line type="monotone" dataKey="actual" stroke="#295d8a" strokeWidth={2.5} dot={false} />
                <Line type="monotone" dataKey="forecast" stroke="#3ab7d0" strokeWidth={2.5} dot={false} />
                <Line type="monotone" dataKey="lower" stroke="#7a5cf4" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                <Line type="monotone" dataKey="upper" stroke="#7a5cf4" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="forecasting-card forecasting-card--drivers">
          <div className="section-header">
            <div>
              <p className="eyebrow">Key drivers</p>
              <h2>Forecast assumptions</h2>
            </div>
          </div>

          <ul className="forecasting-driver-list">
            {(chartData?.[0]?.drivers ?? []).map((driver) => (
              <li key={driver}>{driver}</li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="forecasting-stats">
        <StatCard
          label="Projected next quarter"
          value={`${lastForecast.toFixed(1)} MT`}
          change={`${delta >= 0 ? '+' : ''}${delta.toFixed(1)}% vs last forecast`}
          tone="success"
          trend={delta >= 0 ? 'up' : 'down'}
          icon="gauge"
        />
        <StatCard
          label="Confidence"
          value={`${confidence}%`}
          change="Band width within scenario range"
          tone="cyan"
          trend="up"
          icon="check"
        />
        <StatCard
          label="Upper bound"
          value={`${latestPoint?.upper?.toFixed(1) ?? '--'} MT`}
          change="Optimistic case"
          tone="purple"
          trend="up"
          icon="alert"
        />
        <StatCard
          label="Lower bound"
          value={`${latestPoint?.lower?.toFixed(1) ?? '--'} MT`}
          change="Conservative case"
          tone="warning"
          trend="down"
          icon="clock"
        />
      </div>
    </div>
  )
}
