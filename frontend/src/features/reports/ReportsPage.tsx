import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileBarChart, Play, Download, RefreshCw, AlertCircle } from 'lucide-react'
import { listReports, generateReport, getReportExportUrl } from '../../api/queries'
import { listEntities, type CanonicalEntity } from '../../api/entities'
import { IndustrialCard, LoadingSkeleton, EmptyState } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'
import { formatDistanceToNow } from 'date-fns'

const REPORT_METRICS = ['coal_production', 'coal_dispatch', 'overburden_removal', 'manpower']
const CURRENT_YEAR = new Date().getFullYear()

export default function ReportsPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [label, setLabel] = useState('')
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['coal_production'])
  const [selectedEntities, setSelectedEntities] = useState<string[]>([])
  // Required date range
  const [periodStart, setPeriodStart] = useState(`${CURRENT_YEAR - 5}-01-01`)
  const [periodEnd, setPeriodEnd]     = useState(`${CURRENT_YEAR}-12-31`)
  const [generationResult, setGenerationResult] = useState<Record<string, unknown> | null>(null)
  const [genError, setGenError] = useState<string | null>(null)

  const { data: reports, isLoading, refetch } = useQuery({
    queryKey: [...QUERY_KEYS.reports, page],
    queryFn: () => listReports({ page, page_size: 10 }),
  })

  const { data: entities } = useQuery({
    queryKey: ['entities-select'],
    queryFn: () => listEntities({ page_size: 100 }),
  })

  const generateMutation = useMutation({
    mutationFn: () => generateReport({
      entity_ids:   selectedEntities.length ? selectedEntities : undefined,
      metrics:      selectedMetrics.length  ? selectedMetrics  : undefined,
      period_start: periodStart,
      period_end:   periodEnd,
      label:        label || undefined,
    }),
    onSuccess: (res) => {
      setGenerationResult(res as unknown as Record<string, unknown>)
      setGenError(null)
      qc.invalidateQueries({ queryKey: QUERY_KEYS.reports })
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string | unknown[] } } })?.response?.data?.detail
      setGenError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    },
  })

  const totalPages = reports ? Math.ceil(reports.total / 10) : 1

  const toggleMetric = (m: string) =>
    setSelectedMetrics(prev => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m])
  const toggleEntity = (id: string) =>
    setSelectedEntities(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">AI-GENERATED REPORTS</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <FileBarChart size={16} className="text-amber-500" />
          Report Generation
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Generator */}
        <IndustrialCard className="p-4">
          <div className="section-label mb-3">GENERATE NEW REPORT</div>
          <div className="space-y-4">
            {/* Label */}
            <div>
              <label className="section-label block mb-1">Report Label (optional)</label>
              <input value={label} onChange={(e) => setLabel(e.target.value)}
                placeholder="e.g. Annual Production Summary 2024"
                className="industrial-input" />
            </div>

            {/* Date range — REQUIRED by backend */}
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="section-label block mb-1">Period Start <span className="text-red-400">*</span></label>
                <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)}
                  className="industrial-input text-xs" />
              </div>
              <div className="flex-1">
                <label className="section-label block mb-1">Period End <span className="text-red-400">*</span></label>
                <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)}
                  className="industrial-input text-xs" />
              </div>
            </div>

            {/* Metrics */}
            <div>
              <label className="section-label block mb-2">Metrics to Include</label>
              <div className="flex flex-wrap gap-2">
                {REPORT_METRICS.map(m => (
                  <button key={m} onClick={() => toggleMetric(m)}
                    className={`text-xs px-3 py-1.5 rounded-sm border transition-all font-mono ${
                      selectedMetrics.includes(m)
                        ? 'bg-amber-500/10 border-amber-500/40 text-amber-400'
                        : 'bg-coal-850 border-white/[0.08] text-coal-300 hover:border-amber-500/20'
                    }`}
                  >{m}</button>
                ))}
              </div>
            </div>

            {/* Entities */}
            <div>
              <label className="section-label block mb-2">
                Entities (leave empty = all entities)
              </label>
              <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
                {entities?.items?.map((e: CanonicalEntity) => (
                  <button key={e.id} onClick={() => toggleEntity(e.id)}
                    className={`text-xs px-2.5 py-1 rounded-sm border transition-all ${
                      selectedEntities.includes(e.id)
                        ? 'bg-amber-500/10 border-amber-500/40 text-amber-400'
                        : 'bg-coal-850 border-white/[0.08] text-coal-300 hover:border-amber-500/20'
                    }`}
                  >{e.canonical_name}</button>
                ))}
              </div>
            </div>

            {genError && (
              <div className="bg-red-900/20 border border-red-500/20 rounded-sm p-3 text-xs text-red-300">
                <AlertCircle size={12} className="inline mr-2" />
                {genError}
              </div>
            )}

            <button
              onClick={() => generateMutation.mutate()}
              disabled={!selectedMetrics.length || !periodStart || !periodEnd || generateMutation.isPending}
              className="btn-primary text-sm disabled:opacity-40"
            >
              <Play size={13} />
              {generateMutation.isPending ? 'Generating Report…' : 'Generate Intelligence Report'}
            </button>
          </div>

          {/* Success */}
          {generationResult && (
            <div className="mt-4 bg-coal-950 border border-status-operational/20 rounded-sm p-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full bg-status-operational" />
                <span className="text-status-operational text-xs font-semibold uppercase font-mono">Report Generated</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
                {[
                  { label: 'Sections',     value: (generationResult.sections as string[] | undefined)?.length ?? '—' },
                  { label: 'Citations',    value: String(generationResult.citation_count ?? '—') },
                  { label: 'DQ Warnings', value: String(generationResult.dq_warning_count ?? '—') },
                  { label: 'Time (s)',     value: String(generationResult.generation_time_seconds ?? '—') },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <div className="section-label">{label}</div>
                    <div className="text-white font-mono font-bold text-lg">{value}</div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                {(['pdf', 'docx', 'xlsx'] as const).map(fmt => (
                  <a key={fmt} href={getReportExportUrl(String(generationResult.report_id || generationResult.id), fmt)}
                    target="_blank" rel="noopener noreferrer" className="btn-secondary text-xs">
                    <Download size={12} /> {fmt.toUpperCase()}
                  </a>
                ))}
              </div>
            </div>
          )}
        </IndustrialCard>

        {/* History */}
        <div className="flex items-center justify-between">
          <div className="section-label">REPORT HISTORY</div>
          <button onClick={() => refetch()} className="text-coal-400 hover:text-white transition-colors"><RefreshCw size={13} /></button>
        </div>

        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={5} /></div>
          ) : !reports?.items?.length ? (
            <EmptyState title="No reports yet" message="Generate your first report above." icon={<FileBarChart size={32} />} />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr><th>Label</th><th>Period</th><th>Citations</th><th>DQ Warns</th><th>Generated</th><th>Export</th></tr>
              </thead>
              <tbody>
                {reports.items.map((r: Record<string, unknown>) => (
                  <tr key={String(r.id)}>
                    <td className="text-white">{String(r.label || '—')}</td>
                    <td className="font-mono text-xs text-coal-400">
                      {String(r.period_start || '').slice(0, 10)} → {String(r.period_end || '').slice(0, 10)}
                    </td>
                    <td className="font-mono font-bold text-white">{String(r.citation_count ?? '—')}</td>
                    <td className={`font-mono font-bold ${Number(r.dq_warning_count) > 0 ? 'text-amber-400' : 'text-status-operational'}`}>
                      {String(r.dq_warning_count ?? '—')}
                    </td>
                    <td className="text-coal-400 text-xs font-mono">
                      {r.created_at ? formatDistanceToNow(new Date(String(r.created_at)), { addSuffix: true }) : '—'}
                    </td>
                    <td>
                      <div className="flex gap-1">
                        {(['pdf', 'docx', 'xlsx'] as const).map(fmt => (
                          <a key={fmt} href={getReportExportUrl(String(r.id), fmt)} target="_blank" rel="noopener noreferrer"
                            className="text-[10px] text-coal-400 hover:text-amber-500 font-mono uppercase transition-colors px-1">
                            {fmt}
                          </a>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>

        {reports && reports.total > 10 && (
          <div className="flex items-center justify-between text-xs font-mono text-coal-400">
            <span>{reports.total} reports</span>
            <div className="flex gap-2">
              <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-2 py-1 bg-coal-800 rounded-sm disabled:opacity-40">←</button>
              <span>{page}/{totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="px-2 py-1 bg-coal-800 rounded-sm disabled:opacity-40">→</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
