import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle, X, ChevronDown, AlertCircle } from 'lucide-react'
import { listConflicts } from '../../api/entities'
import { resolveConflict } from '../../api/review'
import { IndustrialCard, LoadingSkeleton, EmptyState, StatusBadge, MetricStrip } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'
import { useAuthStore } from '../../stores/authStore'

export default function ConflictsPage() {
  const qc = useQueryClient()
  const { user, hasRole } = useAuthStore()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('open')
  const [resolveId, setResolveId] = useState<string | null>(null)
  const [resolution, setResolution] = useState('value_a_correct')
  const [resolveNote, setResolveNote] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [...QUERY_KEYS.conflicts, page, statusFilter],
    queryFn: () => listConflicts({ status: statusFilter || undefined, page, page_size: 20 }),
  })

  const resolveMutation = useMutation({
    mutationFn: ({ id }: { id: string }) => resolveConflict(id, {
      resolution, reviewer: user?.username || 'unknown', note: resolveNote
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.conflicts })
      setResolveId(null)
      setResolveNote('')
    },
  })

  const totalPages = data ? Math.ceil(data.total / 20) : 1
  const canResolve = hasRole('reviewer')

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">DATA INTEGRITY</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <AlertTriangle size={16} className="text-amber-500" />
          Conflict Detection
          {data && <span className="text-coal-400 font-normal text-sm ml-1">({data.total.toLocaleString()})</span>}
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Filters */}
        <div className="flex items-center gap-3">
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="industrial-input w-32 text-xs">
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>

        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={8} /></div>
          ) : error ? (
            <EmptyState title="Unable to load conflicts" message="Failed to retrieve conflict data." icon={<AlertCircle size={32} />} action={<button onClick={() => refetch()} className="btn-secondary text-xs">Retry</button>} />
          ) : !data?.items.length ? (
            <EmptyState
              title={statusFilter === 'open' ? 'No open conflicts' : 'No conflicts found'}
              message="Conflicts are detected automatically when multiple sources disagree."
              icon={<CheckCircle size={32} className="text-status-operational" />}
            />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr>
                  <th>Entity</th>
                  <th>Metric</th>
                  <th>Period</th>
                  <th>Value A</th>
                  <th>Value B</th>
                  <th>Delta</th>
                  <th>Status</th>
                  {canResolve && <th className="w-16">Action</th>}
                </tr>
              </thead>
              <tbody>
                {data.items.map((conflict) => (
                  <React.Fragment key={conflict.id}>
                    <tr>
                      <td className="font-semibold text-white max-w-[140px]">
                        <span className="truncate block">{conflict.canonical_entity_name || '—'}</span>
                      </td>
                      <td>
                        <span className="text-amber-400 font-mono text-xs">{conflict.metric}</span>
                      </td>
                      <td className="text-coal-400 font-mono text-xs">{conflict.period_label || '—'}</td>
                      <td>
                        <div className="flex flex-col">
                          <span className="text-white font-mono font-bold">{conflict.value_a?.toLocaleString()}</span>
                          <span className="text-[10px] text-coal-500 truncate max-w-[80px]">{conflict.document_a_filename}</span>
                        </div>
                      </td>
                      <td>
                        <div className="flex flex-col">
                          <span className="text-white font-mono font-bold">{conflict.value_b?.toLocaleString()}</span>
                          <span className="text-[10px] text-coal-500 truncate max-w-[80px]">{conflict.document_b_filename}</span>
                        </div>
                      </td>
                      <td>
                        {conflict.delta_pct != null ? (
                          <span className={`font-mono font-bold text-sm ${Math.abs(conflict.delta_pct) > 20 ? 'text-status-offline' : 'text-amber-400'}`}>
                            {Math.abs(conflict.delta_pct).toFixed(1)}%
                          </span>
                        ) : '—'}
                      </td>
                      <td><StatusBadge status={conflict.status} /></td>
                      {canResolve && (
                        <td>
                          {conflict.status === 'open' && (
                            <button
                              onClick={() => setResolveId(conflict.id)}
                              className="text-xs text-amber-500 hover:text-amber-400 font-medium transition-colors"
                            >
                              Resolve
                            </button>
                          )}
                        </td>
                      )}
                    </tr>

                    {/* Resolve form (inline) */}
                    {resolveId === conflict.id && (
                      <tr>
                        <td colSpan={canResolve ? 8 : 7} className="p-0">
                          <div className="bg-coal-850 border border-amber-500/20 p-4 m-2 rounded-sm space-y-3">
                            <div className="section-label">RESOLVE CONFLICT</div>
                            <div className="flex flex-wrap items-end gap-3">
                              <div>
                                <label className="section-label block mb-1">Resolution</label>
                                <select value={resolution} onChange={(e) => setResolution(e.target.value)} className="industrial-input w-48 text-xs">
                                  {conflict.valid_resolutions.map((r) => (
                                    <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
                                  ))}
                                </select>
                              </div>
                              <div className="flex-1">
                                <label className="section-label block mb-1">Note</label>
                                <input type="text" value={resolveNote} onChange={(e) => setResolveNote(e.target.value)} placeholder="Add resolution note..." className="industrial-input text-xs" />
                              </div>
                              <button
                                onClick={() => resolveMutation.mutate({ id: conflict.id })}
                                disabled={resolveMutation.isPending}
                                className="btn-primary text-xs"
                              >
                                <CheckCircle size={12} />
                                {resolveMutation.isPending ? 'Resolving...' : 'Confirm'}
                              </button>
                              <button onClick={() => setResolveId(null)} className="text-coal-400 hover:text-white"><X size={14} /></button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>

        {data && data.total > 20 && (
          <div className="flex items-center justify-between text-xs font-mono text-coal-400">
            <span>{data.total} conflicts</span>
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
