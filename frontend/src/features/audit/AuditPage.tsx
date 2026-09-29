import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Shield, AlertCircle, Filter } from 'lucide-react'
import { getAuditLog } from '../../api/review'
import { IndustrialCard, LoadingSkeleton, EmptyState } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'
import { formatDistanceToNow } from 'date-fns'

const ACTION_COLOR: Record<string, string> = {
  accept:                  'text-status-operational',
  correct:                 'text-earth-cyan',
  reject:                  'text-status-offline',
  resolve_conflict:        'text-amber-400',
  document_uploaded:       'text-blue-400',
  report_generated:        'text-purple-400',
  parliamentary_submitted: 'text-coal-200',
  parliamentary_approved:  'text-status-operational',
  parliamentary_rejected:  'text-status-offline',
}

export default function AuditPage() {
  const [page, setPage] = useState(1)
  const [actionFilter, setActionFilter] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [...QUERY_KEYS.auditLog, page, actionFilter],
    queryFn: () => getAuditLog({ action_type: actionFilter || undefined, page, page_size: 25 }),
  })

  const totalPages = data ? Math.ceil(data.total / 25) : 1

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">IMMUTABLE AUDIT TRAIL</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <Shield size={16} className="text-amber-500" />
          Audit Log
          {data && <span className="text-coal-400 font-normal text-sm ml-1">({data.total.toLocaleString()} entries)</span>}
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        <div className="flex items-center gap-3">
          <select
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value); setPage(1) }}
            className="industrial-input w-56 text-xs"
          >
            <option value="">All Actions</option>
            <option value="accept">Accept</option>
            <option value="correct">Correct</option>
            <option value="reject">Reject</option>
            <option value="resolve_conflict">Resolve Conflict</option>
            <option value="document_uploaded">Document Upload</option>
            <option value="report_generated">Report Generated</option>
            <option value="parliamentary_approved">Parliamentary Approved</option>
            <option value="parliamentary_rejected">Parliamentary Rejected</option>
          </select>
        </div>

        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={10} /></div>
          ) : error ? (
            <EmptyState title="Unable to load audit log" message="Failed to retrieve audit entries." icon={<AlertCircle size={32} />} action={<button onClick={() => refetch()} className="btn-secondary text-xs">Retry</button>} />
          ) : !data?.items.length ? (
            <EmptyState title="No audit entries" message="Review actions will appear here as an immutable log." icon={<Shield size={32} />} />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Reviewer</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((entry) => (
                  <tr key={entry.id}>
                    <td className="text-coal-400 font-mono text-xs">
                      {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                    </td>
                    <td className="text-white font-semibold text-xs">{entry.reviewer}</td>
                    <td>
                      <span className={`text-xs font-mono font-bold uppercase ${ACTION_COLOR[entry.action_type] || 'text-coal-300'}`}>
                        {entry.action_type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="text-coal-400 font-mono text-xs">
                      <span className="text-coal-500">{entry.target_table}</span>
                      <span className="text-coal-600"> · </span>
                      <span className="truncate max-w-[80px] block">{entry.target_id}</span>
                    </td>
                    <td className="text-coal-300 text-xs italic">{entry.note || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>

        {data && data.total > 25 && (
          <div className="flex items-center justify-between text-xs font-mono text-coal-400">
            <span>{data.total} entries (immutable)</span>
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
