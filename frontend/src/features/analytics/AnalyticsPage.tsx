import React, { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { BarChart3, AlertCircle, TrendingUp, Play, Info } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { listEntities, type CanonicalEntity } from '../../api/entities'
import { analyticsTrend } from '../../api/analytics'
import { IndustrialCard, LoadingSkeleton, EmptyState, MetricStrip } from '../../components/ui/DesignSystem'
import type { TrendDataPoint } from '../../types'

const METRICS = [
  { value: 'coal_production',       label: 'Coal Production' },
  { value: 'coal_dispatch',         label: 'Coal Dispatch' },
  { value: 'overburden_removal',    label: 'Overburden Removal' },
  { value: 'manpower',              label: 'Manpower' },
]
const CURRENT_YEAR = new Date().getFullYear()

export default function AnalyticsPage() {
  const [entityId, setEntityId] = useState('')
  const [metric, setMetric]     = useState('coal_production')
  const [startYear, setStartYear] = useState(CURRENT_YEAR - 5)
  const [endYear, setEndYear]     = useState(CURRENT_YEAR)

  const { data: entities, isLoading: entLoading } = useQuery({
    queryKey: ['entities-select'],
    queryFn: () => listEntities({ page_size: 100 }),
  })

  const trendMutation = useMutation({
    mutationFn: () => analyticsTrend({
      entity_id: entityId,
      metric,
      period_start_year: startYear,
      period_end_year: endYear,
    }),
  })

  const chartData = (trendMutation.data?.series || []).map((dp: TrendDataPoint) => ({
    name:         dp.period_label,
    value:        dp.value,
    has_conflict: dp.has_conflict,
  }))

  const canRun = entityId.length > 0

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">DETERMINISTIC INTELLIGENCE</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <BarChart3 size={16} className="text-amber-500" />
          Analytics Engine
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Controls */}
        <IndustrialCard className="p-4">
          <div className="section-label mb-3">QUERY PARAMETERS</div>
          <div className="flex flex-wrap items-end gap-3">

            {/* Entity — required */}
            <div>
              <label className="section-label block mb-1">
                Entity <span className="text-red-400">*</span>
              </label>
              {entLoading ? (
                <div className="text-xs text-coal-400 font-mono w-56 h-9 flex items-center">Loading entities…</div>
              ) : (
                <select
                  value={entityId}
                  onChange={(e) => setEntityId(e.target.value)}
                  className="industrial-input w-56 text-xs"
                >
                  <option value="">— Select an entity —</option>
                  {entities?.items?.map((e: CanonicalEntity) => (
                    <option key={e.id} value={e.id}>{e.canonical_name}</option>
                  ))}
                </select>
              )}
            </div>

            {/* Metric */}
            <div>
              <label className="section-label block mb-1">Metric</label>
              <select value={metric} onChange={(e) => setMetric(e.target.value)} className="industrial-input w-44 text-xs">
                {METRICS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>

            {/* Years */}
            <div>
              <label className="section-label block mb-1">From Year</label>
              <input type="number" value={startYear} onChange={(e) => setStartYear(+e.target.value)}
                className="industrial-input w-24 text-xs" min={2000} max={CURRENT_YEAR} />
            </div>
            <div>
              <label className="section-label block mb-1">To Year</label>
              <input type="number" value={endYear} onChange={(e) => setEndYear(+e.target.value)}
                className="industrial-input w-24 text-xs" min={2000} max={CURRENT_YEAR + 5} />
            </div>

            <button
              onClick={() => trendMutation.mutate()}
              disabled={!canRun || trendMutation.isPending}
              className="btn-primary text-xs disabled:opacity-40"
            >
              <Play size={12} />
              {trendMutation.isPending ? 'Fetching…' : 'Run Analysis'}
            </button>
          </div>

          {!canRun && (
            <p className="mt-2 text-xs text-amber-500 flex items-center gap-1">
              <Info size={11} /> Select an entity to enable analysis
            </p>
          )}
        </IndustrialCard>

        {/* Loading */}
        {trendMutation.isPending && <IndustrialCard className="p-6"><LoadingSkeleton lines={6} /></IndustrialCard>}

        {/* Error / no data */}
        {trendMutation.isError && (
          <IndustrialCard className="p-6">
            <EmptyState
              title="No data available"
              message="No facts found for this entity / metric / period. Ensure documents have been ingested and Phase 2 fact extraction has run."
              icon={<AlertCircle size={28} />}
              action={<button onClick={() => trendMutation.mutate()} className="btn-secondary text-xs">Retry</button>}
            />
          </IndustrialCard>
        )}

        {/* Results */}
        {trendMutation.data && !trendMutation.isPending && (
          <>
            {/* KPI strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <IndustrialCard className="p-4">
                <MetricStrip label="Entity"      value={trendMutation.data.entity_name || '—'} size="sm" />
              </IndustrialCard>
              <IndustrialCard className="p-4">
                <MetricStrip label="Data Points" value={trendMutation.data.series?.length ?? 0} size="sm" />
              </IndustrialCard>
              <IndustrialCard className="p-4">
                <MetricStrip label="Unit"        value={trendMutation.data.unit || '—'} size="sm" />
              </IndustrialCard>
              <IndustrialCard className="p-4">
                <MetricStrip label="Source Facts" value={trendMutation.data.all_fact_ids?.length ?? 0} size="sm" />
              </IndustrialCard>
            </div>

            {/* Chart */}
            <IndustrialCard className="p-4">
              <div className="section-label mb-4">
                {METRICS.find(m => m.value === metric)?.label?.toUpperCase()} TREND · {trendMutation.data.entity_name}
              </div>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#F2A900" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#F2A900" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="name" tick={{ fill: '#9BB0A8', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#9BB0A8', fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ background: '#1A2220', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '2px' }}
                      labelStyle={{ color: '#F2A900', fontSize: 11 }}
                      itemStyle={{ color: '#FFF', fontSize: 11 }}
                    />
                    <Area type="monotone" dataKey="value" stroke="#F2A900" strokeWidth={2}
                      fill="url(#areaGrad)"
                      dot={(props) => {
                        const { cx, cy, payload } = props
                        return payload?.has_conflict
                          ? <circle key={`dot-${cx}`} cx={cx} cy={cy} r={5} fill="#F97316" stroke="#0B0F0E" strokeWidth={2} />
                          : <circle key={`dot-${cx}`} cx={cx} cy={cy} r={3} fill="#F2A900" stroke="#0B0F0E" strokeWidth={1} />
                      }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState title="No chart data" message="The selected entity/metric returned no data points." icon={<BarChart3 size={28} />} />
              )}
              {chartData.some(d => d.has_conflict) && (
                <p className="mt-2 text-xs text-amber-500 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-orange-500 inline-block" />
                  Orange dots = conflicting sources — review recommended
                </p>
              )}
            </IndustrialCard>
          </>
        )}

        {/* Idle state */}
        {!trendMutation.data && !trendMutation.isPending && !trendMutation.isError && (
          <IndustrialCard className="p-12">
            <EmptyState
              title="Select an entity to begin"
              message="Choose an entity, metric, and time period above, then click Run Analysis."
              icon={<TrendingUp size={32} />}
            />
          </IndustrialCard>
        )}
      </div>
    </div>
  )
}
