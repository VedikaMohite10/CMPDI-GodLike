import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Database, AlertCircle, Filter } from 'lucide-react'
import { listFacts } from '../../api/entities'
import { IndustrialCard, LoadingSkeleton, EmptyState, ConfidenceIndicator, StatusBadge } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'
import { useSearchParams } from 'react-router-dom'

export default function FactsPage() {
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [metric, setMetric] = useState('')

  const documentId = searchParams.get('document_id') || undefined

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [...QUERY_KEYS.facts, page, metric, documentId],
    queryFn: () => listFacts({ page, page_size: 30, document_id: documentId, metric: metric || undefined }),
  })

  const totalPages = data ? Math.ceil(data.total / 30) : 1

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div>
          <div className="section-label mb-0.5">NORMALIZED KNOWLEDGE</div>
          <h1 className="text-base font-bold text-white flex items-center gap-2">
            <Database size={16} className="text-amber-500" />
            Extracted Facts
            {data && <span className="text-coal-400 font-normal text-sm ml-1">({data.total.toLocaleString()})</span>}
          </h1>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        <div className="flex items-center gap-3">
          <input
            value={metric}
            onChange={(e) => { setMetric(e.target.value); setPage(1) }}
            placeholder="Filter by metric (e.g. coal_production)"
            className="industrial-input w-72 text-xs"
          />
        </div>

        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={10} /></div>
          ) : error ? (
            <EmptyState title="Unable to load facts" message="Failed to retrieve facts from server." icon={<AlertCircle size={32} />} action={<button onClick={() => refetch()} className="btn-secondary text-xs">Retry</button>} />
          ) : !data?.items.length ? (
            <EmptyState title="No facts found" message="Run Phase 2 fact extraction on processed documents." icon={<Database size={32} />} />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Value</th>
                  <th>Unit</th>
                  <th>Period</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((fact) => (
                  <tr key={fact.id}>
                    <td>
                      <span className="font-mono text-xs text-amber-400">{fact.metric}</span>
                    </td>
                    <td>
                      <span className="font-mono font-bold text-white">
                        {fact.normalized_value?.toLocaleString() ?? '—'}
                      </span>
                    </td>
                    <td className="text-coal-300 font-mono text-xs">{fact.normalized_unit || '—'}</td>
                    <td className="text-coal-400 font-mono text-xs">
                      {fact.period_start ? new Date(fact.period_start).getFullYear() : '—'}
                      {fact.period_end && fact.period_end !== fact.period_start
                        ? ` – ${new Date(fact.period_end).getFullYear()}`
                        : ''}
                    </td>
                    <td>
                      <div className="flex items-center gap-1">
                        {fact.is_flagged && <StatusBadge status="open" size="sm" />}
                        {fact.has_conflict && <span className="text-[10px] text-amber-500 font-mono">CONFLICT</span>}
                        {!fact.is_flagged && !fact.has_conflict && <span className="text-[10px] text-status-operational font-mono">CLEAN</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>

        {data && data.total > 30 && (
          <div className="flex items-center justify-between text-xs font-mono text-coal-400">
            <span>{data.total} facts</span>
            <div className="flex items-center gap-2">
              <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-2 py-1 bg-coal-800 rounded-sm disabled:opacity-40">←</button>
              <span>Page {page} of {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="px-2 py-1 bg-coal-800 rounded-sm disabled:opacity-40">→</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
