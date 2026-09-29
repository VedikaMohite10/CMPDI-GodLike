import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ClipboardList, CheckCircle, X, AlertCircle, Filter } from 'lucide-react'
import { listFlags } from '../../api/entities'
import { acceptFlag, rejectFlag, correctFlag } from '../../api/review'
import { IndustrialCard, LoadingSkeleton, EmptyState, StatusBadge, ConfidenceIndicator } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'
import { useAuthStore } from '../../stores/authStore'

type ReviewAction = 'accept' | 'reject' | 'correct' | null

export default function ReviewPage() {
  const qc = useQueryClient()
  const { user } = useAuthStore()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('open')
  const [sevFilter, setSevFilter] = useState('')
  const [actionFor, setActionFor] = useState<{ id: string; action: ReviewAction } | null>(null)
  const [note, setNote] = useState('')
  const [correctedValue, setCorrectedValue] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [...QUERY_KEYS.flags, page, statusFilter, sevFilter],
    queryFn: () => listFlags({ status: statusFilter || undefined, severity: sevFilter || undefined, page, page_size: 20 }),
  })

  const mutationOptions = {
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.flags })
      setActionFor(null)
      setNote('')
      setCorrectedValue('')
    },
  }

  const acceptMutation  = useMutation({ mutationFn: (id: string) => acceptFlag(id, { reviewer: user?.username || 'system', note }), ...mutationOptions })
  const rejectMutation  = useMutation({ mutationFn: (id: string) => rejectFlag(id, { reviewer: user?.username || 'system', note }), ...mutationOptions })
  const correctMutation = useMutation({
    mutationFn: (id: string) => correctFlag(id, { corrected_value: Number(correctedValue), reviewer: user?.username || 'system', note }),
    ...mutationOptions
  })

  const totalPages = data ? Math.ceil(data.total / 20) : 1

  const SEVERITY_COLOR: Record<string, string> = {
    critical: 'text-status-offline',
    high:     'text-status-warning',
    medium:   'text-amber-400',
    low:      'text-coal-300',
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">HUMAN VERIFICATION CONSOLE</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <ClipboardList size={16} className="text-amber-500" />
          Review Queue
          {data && <span className="text-coal-400 font-normal text-sm ml-1">({data.total.toLocaleString()})</span>}
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        <div className="flex items-center gap-3">
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }} className="industrial-input w-32 text-xs">
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
            <option value="corrected">Corrected</option>
          </select>
          <select value={sevFilter} onChange={(e) => { setSevFilter(e.target.value); setPage(1) }} className="industrial-input w-32 text-xs">
            <option value="">All Severity</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={8} /></div>
          ) : error ? (
            <EmptyState title="Unable to load review queue" message="Failed to retrieve flags." icon={<AlertCircle size={32} />} action={<button onClick={() => refetch()} className="btn-secondary text-xs">Retry</button>} />
          ) : !data?.items.length ? (
            <EmptyState title="Queue empty" message="No items require human review at this time." icon={<CheckCircle size={32} className="text-status-operational" />} />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr>
                  <th>Flag Type</th>
                  <th>Severity</th>
                  <th>Entity</th>
                  <th>Metric</th>
                  <th>Value</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((flag) => (
                  <React.Fragment key={flag.id}>
                    <tr>
                      <td className="text-xs font-mono text-coal-200">{flag.flag_type}</td>
                      <td>
                        <span className={`text-xs font-bold uppercase font-mono ${SEVERITY_COLOR[flag.severity] || 'text-coal-300'}`}>
                          {flag.severity}
                        </span>
                      </td>
                      <td className="text-white text-xs max-w-[100px]">
                        <span className="truncate block">{flag.entity_name || '—'}</span>
                      </td>
                      <td className="text-amber-400 font-mono text-xs">{flag.metric || '—'}</td>
                      <td className="font-mono font-bold text-white text-sm">
                        {flag.normalized_value?.toLocaleString() ?? '—'}
                        {flag.normalized_unit && <span className="text-coal-400 font-normal text-xs ml-1">{flag.normalized_unit}</span>}
                      </td>
                      <td><StatusBadge status={flag.status} /></td>
                      <td>
                        {flag.status === 'open' && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => setActionFor({ id: flag.id, action: 'accept' })}
                              className="text-[10px] text-status-operational hover:text-green-300 font-mono uppercase"
                            >Accept</button>
                            <span className="text-coal-600">·</span>
                            <button
                              onClick={() => setActionFor({ id: flag.id, action: 'correct' })}
                              className="text-[10px] text-amber-500 hover:text-amber-300 font-mono uppercase"
                            >Correct</button>
                            <span className="text-coal-600">·</span>
                            <button
                              onClick={() => setActionFor({ id: flag.id, action: 'reject' })}
                              className="text-[10px] text-status-offline hover:text-red-300 font-mono uppercase"
                            >Reject</button>
                          </div>
                        )}
                      </td>
                    </tr>

                    {/* Action form */}
                    {actionFor?.id === flag.id && (
                      <tr>
                        <td colSpan={7} className="p-0">
                          <div className="bg-coal-850 border border-amber-500/20 p-4 m-2 rounded-sm space-y-3">
                            <div className="section-label capitalize">{actionFor.action} FLAG</div>
                            <div className="flex items-end gap-3 flex-wrap">
                              {actionFor.action === 'correct' && (
                                <div>
                                  <label className="section-label block mb-1">Corrected Value</label>
                                  <input
                                    type="number"
                                    value={correctedValue}
                                    onChange={(e) => setCorrectedValue(e.target.value)}
                                    className="industrial-input w-32 text-xs"
                                    placeholder="Value"
                                  />
                                </div>
                              )}
                              <div className="flex-1">
                                <label className="section-label block mb-1">Note {actionFor.action === 'reject' ? '(required)' : '(optional)'}</label>
                                <input type="text" value={note} onChange={(e) => setNote(e.target.value)} className="industrial-input text-xs" placeholder="Add reviewer note..." />
                              </div>
                              <button
                                onClick={() => {
                                  if (actionFor.action === 'accept')  acceptMutation.mutate(flag.id)
                                  if (actionFor.action === 'reject')  rejectMutation.mutate(flag.id)
                                  if (actionFor.action === 'correct') correctMutation.mutate(flag.id)
                                }}
                                disabled={acceptMutation.isPending || rejectMutation.isPending || correctMutation.isPending}
                                className={`btn-${actionFor.action === 'reject' ? 'danger' : 'primary'} text-xs`}
                              >
                                <CheckCircle size={12} />
                                Confirm
                              </button>
                              <button onClick={() => { setActionFor(null); setNote('') }} className="text-coal-400 hover:text-white"><X size={14} /></button>
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
            <span>{data.total} flags</span>
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
