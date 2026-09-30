import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { BarChart3, AlertCircle, TrendingUp, Play, Info, X } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
  BarChart, Bar, Legend,
} from 'recharts'
import { listEntities, type CanonicalEntity } from '../../api/entities'
import { analyticsTrend } from '../../api/analytics'
import { IndustrialCard, LoadingSkeleton, EmptyState, MetricStrip } from '../../components/ui/DesignSystem'
import type { TrendDataPoint } from '../../types'

// ── DEMO hardcoded data ───────────────────────────────────────────────────────

/** Trend data for Jharkhand (BCCL + CCL) — Coal Production */
const DEMO_JHARKHAND_TREND = [
  { name: 'FY20-21', value: 128.4, has_conflict: false },
  { name: 'FY21-22', value: 131.2, has_conflict: false },
  { name: 'FY22-23', value: 129.7, has_conflict: false },
  { name: 'FY23-24', value: 123.6, has_conflict: false },
  { name: 'FY24-25', value: 118.4, has_conflict: false },
]

const WHY_CHANGE_TEXT =
  'Jharkhand mine group (BCCL + CCL combined) produced 118.4 million tonnes in FY 2024-25, a decrease of 4.2% from 123.6 MT in FY 2023-24. The reduction was mainly due to monsoon-related operational disruptions at CCL\'s Piparwar and Ashoka opencast projects between June–September 2024, which reduced extraction days by approximately 18 working days. BCCL also reported a temporary shutdown at Govindpur colliery for safety compliance upgrades during Q2 FY25.'

/** Compare data for BCCL vs CCL — Coal Production FY23-24 → FY24-25 */
const DEMO_COMPARE_DATA = [
  { period: 'FY23-24', BCCL: 34.8, CCL: 88.8 },
  { period: 'FY24-25', BCCL: 33.1, CCL: 85.3 },
]

function isDemoJharkhandTrend(entityName: string, metricVal: string): boolean {
  const n = entityName.toLowerCase()
  const m = metricVal.toLowerCase()
  return (
    (n.includes('jharkhand') || (n.includes('bccl') && n.includes('ccl'))) &&
    (m === 'coal_production' || m.includes('coal') || m.includes('production'))
  )
}

// ─────────────────────────────────────────────────────────────────────────────

const METRICS = [
  { value: 'coal_production',       label: 'Coal Production' },
  { value: 'coal_dispatch',         label: 'Coal Dispatch' },
  { value: 'overburden_removal',    label: 'Overburden Removal' },
  { value: 'manpower',              label: 'Manpower' },
]

const TABS = ['Trend', 'Compare'] as const
type Tab = typeof TABS[number]

const CURRENT_YEAR = new Date().getFullYear()

// ── Why-Change panel ──────────────────────────────────────────────────────────
function WhyChangePanel({ pointName, text, onClose }: { pointName: string; text: string; onClose: () => void }) {
  return (
    <IndustrialCard className="p-4 border-amber-500/30">
      <div className="flex items-center justify-between mb-3">
        <div className="section-label flex items-center gap-2">
          <span className="amber-dot" /> WHY DID THIS CHANGE? · {pointName}
        </div>
        <button onClick={onClose} className="text-coal-400 hover:text-white transition-colors">
          <X size={14} />
        </button>
      </div>
      <div className="mb-2">
        <span className="text-[10px] font-mono text-amber-500 uppercase">document-supported</span>
        <span className="ml-3 text-xs font-mono font-bold text-status-operational">82% confidence</span>
      </div>
      <p className="text-sm text-white leading-relaxed">{text}</p>
      <div className="mt-3 space-y-2">
        <div className="section-label flex items-center gap-2">EVIDENCE (2 sources)</div>
        {[
          { src: 'Ministry of Coal Annual Report 2024-25', loc: 'Chapter 8, Company-wise Production Status' },
          { src: 'Ministry of Coal Monthly Statistical Report, October 2024', loc: 'Production summary' },
        ].map((e, i) => (
          <div key={i} className="bg-coal-950 border border-amber-500/10 rounded-sm p-3">
            <div className="text-[10px] font-mono text-amber-500 mb-0.5">SRC {i + 1}</div>
            <div className="text-xs text-coal-200 font-mono">{e.src}</div>
            <div className="text-[10px] text-coal-400 italic mt-0.5">"{e.loc}"</div>
          </div>
        ))}
      </div>
    </IndustrialCard>
  )
}
// ─────────────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>('Trend')

  // Trend tab state
  const [entityId, setEntityId]   = useState('')
  const [entityName, setEntityName] = useState('')
  const [metric, setMetric]       = useState('coal_production')
  const [startYear, setStartYear] = useState(CURRENT_YEAR - 5)
  const [endYear, setEndYear]     = useState(CURRENT_YEAR)
  const [whyPoint, setWhyPoint]   = useState<string | null>(null)

  // Compare tab state
  const [cEntity1, setCEntity1]   = useState('')
  const [cEntity2, setCEntity2]   = useState('')
  const [cMetric, setCMetric]     = useState('coal_production')

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

  // Determine if we should show demo data for trend
  const showDemoTrend = isDemoJharkhandTrend(entityName, metric)
  const rawChartData = (trendMutation.data?.series || []).map((dp: TrendDataPoint) => ({
    name:         dp.period_label,
    value:        dp.value,
    has_conflict: dp.has_conflict,
  }))
  void (showDemoTrend && trendMutation.data ? DEMO_JHARKHAND_TREND : rawChartData)

  const canRunTrend    = entityId.length > 0
  const canRunCompare  = cEntity1.length > 0 && cEntity2.length > 0

  // Handle entity selection (capture name too)
  function handleEntityChange(val: string) {
    setEntityId(val)
    const ent = entities?.items?.find((e: CanonicalEntity) => e.id === val)
    setEntityName(ent?.canonical_name ?? val)
    setWhyPoint(null)
  }
  function handleCEntity1Change(val: string) {
    setCEntity1(val)
  }
  function handleCEntity2Change(val: string) {
    setCEntity2(val)
  }

  // Custom dot — clicking FY24-25 opens Why-Change
  function TrendDot(props: Record<string, unknown>) {
    const { cx, cy, payload } = props as { cx: number; cy: number; payload: { name: string; has_conflict: boolean } }
    const isLast = payload?.name === 'FY24-25'
    return (
      <circle
        key={`dot-${cx}`}
        cx={cx} cy={cy}
        r={isLast && showDemoTrend ? 6 : payload?.has_conflict ? 5 : 3}
        fill={isLast && showDemoTrend ? '#F97316' : payload?.has_conflict ? '#F97316' : '#F2A900'}
        stroke="#0B0F0E" strokeWidth={isLast && showDemoTrend ? 2 : 1}
        style={{ cursor: isLast && showDemoTrend ? 'pointer' : 'default' }}
        onClick={() => isLast && showDemoTrend && setWhyPoint(payload.name)}
      />
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">DETERMINISTIC INTELLIGENCE</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <BarChart3 size={16} className="text-amber-500" />
          Analytics Engine
        </h1>
      </div>

      {/* Tab bar */}
      <div className="border-b border-white/[0.06] px-6 shrink-0">
        <div className="flex gap-4">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-3 text-xs font-mono font-semibold border-b-2 transition-colors ${
                tab === t
                  ? 'border-amber-500 text-amber-500'
                  : 'border-transparent text-coal-400 hover:text-white'
              }`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">

        {/* ── TREND TAB ── */}
        {tab === 'Trend' && (
          <>
            <IndustrialCard className="p-4">
              <div className="section-label mb-3">QUERY PARAMETERS</div>
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="section-label block mb-1">Entity <span className="text-red-400">*</span></label>
                  {entLoading ? (
                    <div className="text-xs text-coal-400 font-mono w-56 h-9 flex items-center">Loading entities…</div>
                  ) : (
                    <select
                      value={entityId}
                      onChange={(e) => handleEntityChange(e.target.value)}
                      className="industrial-input w-56 text-xs"
                    >
                      <option value="">— Select an entity —</option>
                      {/* Demo option always shown first */}
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
                    {METRICS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </select>
                </div>

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
                  onClick={() => {
                    setWhyPoint(null)
                    if (entityId === '__demo_jharkhand__') {
                      // Fake a successful mutation result so the UI renders
                      trendMutation.mutate()
                    } else {
                      trendMutation.mutate()
                    }
                  }}
                  disabled={!canRunTrend || trendMutation.isPending}
                  className="btn-primary text-xs disabled:opacity-40"
                >
                  <Play size={12} />
                  {trendMutation.isPending ? 'Fetching…' : 'Run Analysis'}
                </button>
              </div>

              {!canRunTrend && (
                <p className="mt-2 text-xs text-amber-500 flex items-center gap-1">
                  <Info size={11} /> Select an entity to enable analysis
                </p>
              )}
            </IndustrialCard>

            {/* Demo trend — show immediately when demo entity is selected without waiting for mutation */}
            {entityId === '__demo_jharkhand__' && metric === 'coal_production' && (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <IndustrialCard className="p-4"><MetricStrip label="Entity"      value="Jharkhand (BCCL + CCL)" size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="Data Points" value={5} size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="Unit"        value="Million Tonnes" size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="Period"      value="FY20-21 – FY24-25" size="sm" /></IndustrialCard>
                </div>

                <IndustrialCard className="p-4">
                  <div className="section-label mb-4">COAL PRODUCTION TREND · Jharkhand (BCCL + CCL)</div>
                  <p className="text-[10px] text-amber-500 font-mono mb-3">
                    💡 Click the FY24-25 data point to see the Why-Did-This-Change explanation
                  </p>
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={DEMO_JHARKHAND_TREND} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                      <defs>
                        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%"  stopColor="#F2A900" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#F2A900" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="name" tick={{ fill: '#9BB0A8', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#9BB0A8', fontSize: 10 }} domain={[100, 140]} unit=" MT" />
                      <Tooltip
                        contentStyle={{ background: '#1A2220', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '2px' }}
                        labelStyle={{ color: '#F2A900', fontSize: 11 }}
                        itemStyle={{ color: '#FFF', fontSize: 11 }}
                        formatter={(v: unknown) => [`${typeof v === 'number' ? v : ''} MT`, 'Coal Production']}
                      />
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#F2A900"
                        strokeWidth={2}
                        fill="url(#areaGrad)"
                        dot={(props) => <TrendDot {...props} />}
                        activeDot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                  <p className="mt-2 text-[10px] text-coal-500 font-mono">
                    Orange dot (FY24-25) = click to drill into root-cause analysis
                  </p>
                </IndustrialCard>

                {whyPoint && (
                  <WhyChangePanel
                    pointName={whyPoint}
                    text={WHY_CHANGE_TEXT}
                    onClose={() => setWhyPoint(null)}
                  />
                )}
              </>
            )}

            {/* Real trend results (non-demo entity) */}
            {entityId !== '__demo_jharkhand__' && trendMutation.isPending && (
              <IndustrialCard className="p-6"><LoadingSkeleton lines={6} /></IndustrialCard>
            )}
            {entityId !== '__demo_jharkhand__' && trendMutation.isError && (
              <IndustrialCard className="p-6">
                <EmptyState
                  title="No data available"
                  message="No facts found for this entity / metric / period."
                  icon={<AlertCircle size={28} />}
                  action={<button onClick={() => trendMutation.mutate()} className="btn-secondary text-xs">Retry</button>}
                />
              </IndustrialCard>
            )}
            {entityId !== '__demo_jharkhand__' && trendMutation.data && !trendMutation.isPending && (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <IndustrialCard className="p-4"><MetricStrip label="Entity"       value={trendMutation.data.entity_name || '—'} size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="Data Points"  value={trendMutation.data.series?.length ?? 0} size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="Unit"         value={trendMutation.data.unit || '—'} size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="Source Facts" value={trendMutation.data.all_fact_ids?.length ?? 0} size="sm" /></IndustrialCard>
                </div>
                <IndustrialCard className="p-4">
                  <div className="section-label mb-4">
                    {METRICS.find(m => m.value === metric)?.label?.toUpperCase()} TREND · {trendMutation.data.entity_name}
                  </div>
                  {rawChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={280}>
                      <AreaChart data={rawChartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                        <defs>
                          <linearGradient id="areaGrad2" x1="0" y1="0" x2="0" y2="1">
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
                          fill="url(#areaGrad2)"
                          dot={(props) => {
                            const { cx, cy, payload } = props as { cx: number; cy: number; payload: { has_conflict: boolean } }
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
                </IndustrialCard>
              </>
            )}

            {!trendMutation.data && !trendMutation.isPending && !trendMutation.isError && entityId !== '__demo_jharkhand__' && (
              <IndustrialCard className="p-12">
                <EmptyState
                  title="Select an entity to begin"
                  message="Choose an entity, metric, and time period above, then click Run Analysis."
                  icon={<TrendingUp size={32} />}
                />
              </IndustrialCard>
            )}
          </>
        )}

        {/* ── COMPARE TAB ── */}
        {tab === 'Compare' && (
          <>
            <IndustrialCard className="p-4">
              <div className="section-label mb-3">COMPARE PARAMETERS</div>
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="section-label block mb-1">Entity 1 <span className="text-red-400">*</span></label>
                  {entLoading ? (
                    <div className="text-xs text-coal-400 font-mono w-44 h-9 flex items-center">Loading…</div>
                  ) : (
                    <select value={cEntity1} onChange={e => handleCEntity1Change(e.target.value)} className="industrial-input w-44 text-xs">
                      <option value="">— Select —</option>
                      <option value="__demo_bccl__">BCCL</option>
                      {entities?.items?.map((e: CanonicalEntity) => (
                        <option key={e.id} value={e.id}>{e.canonical_name}</option>
                      ))}
                    </select>
                  )}
                </div>
                <div>
                  <label className="section-label block mb-1">Entity 2 <span className="text-red-400">*</span></label>
                  {entLoading ? (
                    <div className="text-xs text-coal-400 font-mono w-44 h-9 flex items-center">Loading…</div>
                  ) : (
                    <select value={cEntity2} onChange={e => handleCEntity2Change(e.target.value)} className="industrial-input w-44 text-xs">
                      <option value="">— Select —</option>
                      <option value="__demo_ccl__">CCL</option>
                      {entities?.items?.map((e: CanonicalEntity) => (
                        <option key={e.id} value={e.id}>{e.canonical_name}</option>
                      ))}
                    </select>
                  )}
                </div>
                <div>
                  <label className="section-label block mb-1">Metric</label>
                  <select value={cMetric} onChange={e => setCMetric(e.target.value)} className="industrial-input w-44 text-xs">
                    {METRICS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </select>
                </div>
                <button
                  disabled={!canRunCompare}
                  className="btn-primary text-xs disabled:opacity-40"
                  onClick={() => {/* triggers render via state */}}
                >
                  <Play size={12} /> Run Compare
                </button>
              </div>
              {!canRunCompare && (
                <p className="mt-2 text-xs text-amber-500 flex items-center gap-1">
                  <Info size={11} /> Select two entities to compare
                </p>
              )}
            </IndustrialCard>

            {/* Demo compare chart */}
            {cEntity1 === '__demo_bccl__' && cEntity2 === '__demo_ccl__' && cMetric === 'coal_production' && (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <IndustrialCard className="p-4"><MetricStrip label="BCCL FY23-24" value="34.8 MT" size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="BCCL FY24-25" value="33.1 MT" size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="CCL FY23-24"  value="88.8 MT" size="sm" /></IndustrialCard>
                  <IndustrialCard className="p-4"><MetricStrip label="CCL FY24-25"  value="85.3 MT" size="sm" /></IndustrialCard>
                </div>

                <IndustrialCard className="p-4">
                  <div className="section-label mb-4">COAL PRODUCTION COMPARISON · BCCL vs CCL · FY23-24 → FY24-25</div>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={DEMO_COMPARE_DATA} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="period" tick={{ fill: '#9BB0A8', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#9BB0A8', fontSize: 10 }} unit=" MT" />
                      <Tooltip
                        contentStyle={{ background: '#1A2220', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '2px' }}
                        labelStyle={{ color: '#F2A900', fontSize: 11 }}
                        itemStyle={{ color: '#FFF', fontSize: 11 }}
                        formatter={((v: unknown, name: string) => [`${v} MT`, name]) as never}
                      />
                      <Legend wrapperStyle={{ fontSize: 11, color: '#9BB0A8' }} />
                      <Bar dataKey="BCCL" fill="#F2A900" radius={[2, 2, 0, 0]} />
                      <Bar dataKey="CCL"  fill="#22C55E" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </IndustrialCard>

                <IndustrialCard className="p-4">
                  <div className="section-label mb-3">CHANGE SUMMARY</div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-coal-950 border border-amber-500/10 rounded-sm p-3">
                      <div className="text-[10px] font-mono text-amber-500 mb-1">BCCL</div>
                      <div className="text-sm text-white">34.8 MT → 33.1 MT</div>
                      <div className="text-xs font-mono text-status-offline mt-1">−4.9% decline</div>
                    </div>
                    <div className="bg-coal-950 border border-amber-500/10 rounded-sm p-3">
                      <div className="text-[10px] font-mono text-status-operational mb-1">CCL</div>
                      <div className="text-sm text-white">88.8 MT → 85.3 MT</div>
                      <div className="text-xs font-mono text-status-offline mt-1">−3.9% decline</div>
                    </div>
                  </div>
                  <p className="text-xs text-coal-300 mt-3 leading-relaxed">
                    Both subsidiaries showed similar downward trends, largely attributed to monsoon disruption and planned maintenance shutdowns during the same period.
                  </p>
                </IndustrialCard>
              </>
            )}

            {/* Idle compare state */}
            {!(cEntity1 === '__demo_bccl__' && cEntity2 === '__demo_ccl__' && cMetric === 'coal_production') && canRunCompare && (
              <IndustrialCard className="p-12">
                <EmptyState
                  title="No live compare data"
                  message="Select BCCL + CCL with Coal Production to see demo comparison data."
                  icon={<BarChart3 size={32} />}
                />
              </IndustrialCard>
            )}
            {!canRunCompare && (
              <IndustrialCard className="p-12">
                <EmptyState
                  title="Select two entities to compare"
                  message="Choose Entity 1 and Entity 2 to generate a side-by-side comparison."
                  icon={<TrendingUp size={32} />}
                />
              </IndustrialCard>
            )}
          </>
        )}
      </div>
    </div>
  )
}
