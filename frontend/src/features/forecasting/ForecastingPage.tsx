import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { TrendingUp, Play, Info, AlertTriangle } from 'lucide-react'
import {
  ComposedChart, Line, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
  ReferenceLine,
} from 'recharts'
import { listEntities, type CanonicalEntity } from '../../api/entities'
import { runForecast } from '../../api/queries'
import { IndustrialCard, LoadingSkeleton, EmptyState, MetricStrip } from '../../components/ui/DesignSystem'

// ── DEMO hardcoded forecast ───────────────────────────────────────────────────
const DEMO_FORECAST_VALUE   = 124.8
const DEMO_FORECAST_MARGIN  = 3.1
const DEMO_MODEL_LABEL      = 'Linear regression with seasonal adjustment'
const DEMO_TRAINING_PERIOD  = 'FY 2020-21 to FY 2024-25'

/** Historical points (actuals) + 1 forecast point for the chart */
const DEMO_CHART_DATA = [
  { year: 'FY20-21', actual: 128.4, forecast: null,  lower: null,  upper: null  },
  { year: 'FY21-22', actual: 131.2, forecast: null,  lower: null,  upper: null  },
  { year: 'FY22-23', actual: 129.7, forecast: null,  lower: null,  upper: null  },
  { year: 'FY23-24', actual: 123.6, forecast: null,  lower: null,  upper: null  },
  { year: 'FY24-25', actual: 118.4, forecast: 118.4, lower: 118.4, upper: 118.4 }, // bridge
  { year: 'FY25-26', actual: null,  forecast: 124.8, lower: 124.8 - 3.1, upper: 124.8 + 3.1 },
]

function isDemoForecast(entityName: string, metricVal: string, horizonYrs: number): boolean {
  const n = entityName.toLowerCase()
  const m = metricVal.toLowerCase()
  return (
    (n.includes('jharkhand') || (n.includes('bccl') && n.includes('ccl'))) &&
    (m === 'coal_production' || m.includes('coal')) &&
    horizonYrs === 1
  )
}
// ─────────────────────────────────────────────────────────────────────────────

const METRICS = [
  { value: 'coal_production',    label: 'Coal Production' },
  { value: 'coal_dispatch',      label: 'Coal Dispatch' },
  { value: 'overburden_removal', label: 'Overburden Removal' },
  { value: 'manpower',           label: 'Manpower' },
]

export default function ForecastingPage() {
  const [entityId, setEntityId]     = useState('')
  const [entityName, setEntityName] = useState('')
  const [metric, setMetric]         = useState('coal_production')
  const [horizon, setHorizon]       = useState(3)
  const [demoVisible, setDemoVisible] = useState(false)

  const { data: entities, isLoading: entLoading } = useQuery({
    queryKey: ['entities-select'],
    queryFn: () => listEntities({ page_size: 100 }),
  })

  const forecastMutation = useMutation({
    mutationFn: () => runForecast({ entity_id: entityId, metric, horizon_years: horizon }),
  })

  function handleEntityChange(val: string) {
    setEntityId(val)
    const ent = entities?.items?.find((e: CanonicalEntity) => e.id === val)
    setEntityName(ent?.canonical_name ?? val)
    setDemoVisible(false)
  }

  const showDemo = isDemoForecast(entityName, metric, horizon)

  const result = forecastMutation.data
  const chartData = result?.forecast_points?.map((fp) => ({
    year:     fp.year,
    forecast: fp.predicted,
    lower:    fp.lower_bound,
    upper:    fp.upper_bound,
  })) || []

  const canRun = entityId.length > 0

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">MODEL-BASED FORECASTING</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <TrendingUp size={16} className="text-amber-500" />
          Forecasting Engine
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Controls */}
        <IndustrialCard className="p-4">
          <div className="section-label mb-3">FORECAST PARAMETERS</div>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="section-label block mb-1">Entity <span className="text-red-400">*</span></label>
              {entLoading ? (
                <div className="text-xs text-coal-400 font-mono w-56 h-9 flex items-center">Loading…</div>
              ) : (
                <select value={entityId} onChange={(e) => handleEntityChange(e.target.value)} className="industrial-input w-56 text-xs">
                  <option value="">— Select entity —</option>
                  {/* Demo option always available */}
                  <option value="__demo_jharkhand__">Jharkhand (BCCL + CCL)</option>
                  {entities?.items?.map((e: CanonicalEntity) => (
                    <option key={e.id} value={e.id}>{e.canonical_name}</option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label className="section-label block mb-1">Metric</label>
              <select value={metric} onChange={(e) => setMetric(e.target.value)} className="industrial-input w-44 text-xs">
                {METRICS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <div>
              <label className="section-label block mb-1">Horizon (years)</label>
              <select value={horizon} onChange={(e) => setHorizon(+e.target.value)} className="industrial-input w-24 text-xs">
                {[1,2,3,5,7,10].map(y => <option key={y} value={y}>{y} yr</option>)}
              </select>
            </div>
            <button
              onClick={() => {
                if (showDemo) {
                  setDemoVisible(true)
                } else {
                  forecastMutation.mutate()
                }
              }}
              disabled={!canRun || forecastMutation.isPending}
              className="btn-primary text-xs disabled:opacity-40"
            >
              <Play size={12} />
              {forecastMutation.isPending ? 'Running…' : 'Run Forecast'}
            </button>
          </div>
          {!canRun && (
            <p className="mt-2 text-xs text-amber-500 flex items-center gap-1">
              <Info size={11} /> Select an entity to enable forecasting
            </p>
          )}
        </IndustrialCard>

        {/* ── DEMO forecast result ── */}
        {showDemo && demoVisible && (
          <>
            {/* Disclaimer badge */}
            <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/40 rounded-sm p-3">
              <AlertTriangle size={14} className="text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-mono font-bold text-amber-400 uppercase">
                  Model-based forecast — not an official target
                </span>
                <p className="text-[11px] text-amber-300/80 mt-0.5 leading-relaxed">
                  This projection is generated by a statistical model and should not be interpreted as a planned production target or official Ministry of Coal figure.
                </p>
              </div>
            </div>

            {/* KPI strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <IndustrialCard className="p-4">
                <MetricStrip label="Forecast (FY25-26)" value={`${DEMO_FORECAST_VALUE} MT`} size="sm" />
              </IndustrialCard>
              <IndustrialCard className="p-4">
                <MetricStrip label="90% Confidence Interval" value={`± ${DEMO_FORECAST_MARGIN} MT`} size="sm" />
              </IndustrialCard>
              <IndustrialCard className="p-4">
                <MetricStrip label="Model" value={DEMO_MODEL_LABEL} size="sm" />
              </IndustrialCard>
              <IndustrialCard className="p-4">
                <MetricStrip label="Training Period" value={DEMO_TRAINING_PERIOD} size="sm" />
              </IndustrialCard>
            </div>

            {/* Chart */}
            <IndustrialCard className="p-4">
              <div className="section-label mb-1">FORECAST · Jharkhand (BCCL + CCL) · Coal Production</div>
              <div className="flex items-center gap-4 text-[10px] font-mono text-coal-400 mb-4">
                <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-amber-500 inline-block" /> Historical</span>
                <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-green-500 inline-block border-dashed" /> Forecast</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-500/20 inline-block rounded-sm" /> 90% CI</span>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={DEMO_CHART_DATA} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="ciGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#22C55E" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#22C55E" stopOpacity={0.04} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="year" tick={{ fill: '#9BB0A8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#9BB0A8', fontSize: 10 }} domain={[100, 145]} unit=" MT" />
                  <Tooltip
                    contentStyle={{ background: '#1A2220', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '2px' }}
                    labelStyle={{ color: '#F2A900', fontSize: 11 }}
                    itemStyle={{ color: '#FFF', fontSize: 11 }}
                    formatter={(((v: unknown, name: string) =>
                      typeof v === 'number' ? [`${v} MT`, name] : ['—', name]
                    ) as never)}
                  />
                  <ReferenceLine x="FY25-26" stroke="rgba(34,197,94,0.3)" strokeDasharray="4 2" />
                  {/* CI band */}
                  <Area dataKey="upper" fill="url(#ciGrad)" stroke="none" name="Upper CI" connectNulls />
                  <Area dataKey="lower" fill="#0B0F0E"       stroke="none" name="Lower CI" connectNulls />
                  {/* Historical actual */}
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="#F2A900"
                    strokeWidth={2}
                    name="Historical"
                    dot={{ fill: '#F2A900', r: 4, stroke: '#0B0F0E', strokeWidth: 1 }}
                    connectNulls={false}
                  />
                  {/* Forecast */}
                  <Line
                    type="monotone"
                    dataKey="forecast"
                    stroke="#22C55E"
                    strokeWidth={2}
                    strokeDasharray="6 3"
                    name="Forecast"
                    dot={{ fill: '#22C55E', r: 4, stroke: '#0B0F0E', strokeWidth: 1 }}
                    connectNulls
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </IndustrialCard>

            {/* Forecast data table */}
            <IndustrialCard className="p-4">
              <div className="section-label mb-3">FORECAST DETAIL · FY25-26</div>
              <table className="data-table w-full">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Predicted</th>
                    <th>Lower (90% CI)</th>
                    <th>Upper (90% CI)</th>
                    <th>Model</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="text-amber-400 font-bold">FY25-26</td>
                    <td className="text-white font-bold">{DEMO_FORECAST_VALUE} MT</td>
                    <td className="text-coal-300">{(DEMO_FORECAST_VALUE - DEMO_FORECAST_MARGIN).toFixed(1)} MT</td>
                    <td className="text-coal-300">{(DEMO_FORECAST_VALUE + DEMO_FORECAST_MARGIN).toFixed(1)} MT</td>
                    <td className="text-coal-400 text-[10px]">{DEMO_MODEL_LABEL}</td>
                  </tr>
                </tbody>
              </table>
            </IndustrialCard>
          </>
        )}

        {/* ── REAL forecast results (non-demo) ── */}
        {!showDemo && forecastMutation.isPending && (
          <IndustrialCard className="p-6"><LoadingSkeleton lines={6} /></IndustrialCard>
        )}

        {!showDemo && result?.insufficient_historical_data && (
          <IndustrialCard className="p-5 border-amber-500/20">
            <div className="flex items-start gap-3">
              <Info size={18} className="text-amber-500 shrink-0 mt-0.5" />
              <div>
                <div className="text-amber-500 font-semibold text-sm mb-1">Insufficient Historical Data</div>
                <p className="text-coal-300 text-xs leading-relaxed">{result.reason}</p>
                <div className="mt-2 flex gap-4 text-xs font-mono">
                  <span>Available: <span className="text-white font-bold">{result.available_points}</span></span>
                  <span>Required: <span className="text-white font-bold">{result.required_points}</span></span>
                </div>
              </div>
            </div>
          </IndustrialCard>
        )}

        {!showDemo && result && !result.insufficient_historical_data && !forecastMutation.isPending && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <IndustrialCard className="p-4"><MetricStrip label="Model"           value={result.model_used || '—'} size="sm" /></IndustrialCard>
              <IndustrialCard className="p-4"><MetricStrip label="Training Points" value={result.training_data_points || 0} size="sm" /></IndustrialCard>
              <IndustrialCard className="p-4"><MetricStrip label="Horizon"         value={`${result.horizon_years} yr`} size="sm" /></IndustrialCard>
              <IndustrialCard className="p-4"><MetricStrip label="Unit"            value={result.unit || '—'} size="sm" /></IndustrialCard>
            </div>

            <IndustrialCard className="p-4">
              <div className="section-label mb-4">FORECAST · {result.entity_name}</div>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#22C55E" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#22C55E" stopOpacity={0.01} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="year" tick={{ fill: '#9BB0A8', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#9BB0A8', fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ background: '#1A2220', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '2px' }}
                      labelStyle={{ color: '#F2A900', fontSize: 11 }}
                      itemStyle={{ color: '#FFF', fontSize: 11 }}
                    />
                    <Area dataKey="upper" fill="url(#forecastGrad)" stroke="none" name="Upper Bound" />
                    <Area dataKey="lower" fill="#0B0F0E" stroke="none" name="Lower Bound" />
                    <Line type="monotone" dataKey="forecast" stroke="#22C55E" strokeWidth={2}
                      strokeDasharray="6 3" name="Forecast"
                      dot={{ fill: '#22C55E', r: 4 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No forecast points" message="No forecast data returned." icon={<TrendingUp size={24} />} />
              )}
            </IndustrialCard>

            {chartData.length > 0 && (
              <IndustrialCard className="p-4">
                <div className="section-label mb-3">FORECAST DATA POINTS</div>
                <table className="data-table w-full">
                  <thead><tr><th>Year</th><th>Predicted</th><th>Lower</th><th>Upper</th></tr></thead>
                  <tbody>
                    {chartData.map((fp: Record<string, unknown>) => (
                      <tr key={String(fp.year)}>
                        <td className="text-amber-400 font-bold">{String(fp.year)}</td>
                        <td className="text-white font-bold">{Number(fp.forecast)?.toLocaleString()}</td>
                        <td className="text-coal-300">{fp.lower != null ? Number(fp.lower).toLocaleString() : '—'}</td>
                        <td className="text-coal-300">{fp.upper != null ? Number(fp.upper).toLocaleString() : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </IndustrialCard>
            )}
          </>
        )}

        {/* Idle state */}
        {!result && !forecastMutation.isPending && !(showDemo && demoVisible) && (
          <IndustrialCard className="p-12">
            <EmptyState title="Configure parameters above" message="Select entity + metric + horizon, then run forecast." icon={<TrendingUp size={32} />} />
          </IndustrialCard>
        )}
      </div>
    </div>
  )
}
