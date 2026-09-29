import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Copy, AlertCircle } from 'lucide-react'
import { listDuplicates } from '../../api/entities'
import { IndustrialCard, LoadingSkeleton, EmptyState, StatusBadge } from '../../components/ui/DesignSystem'

export default function DuplicatesPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error } = useQuery({
    queryKey: ['duplicates', page],
    queryFn: () => listDuplicates({ page, page_size: 20 }),
  })
  const totalPages = data ? Math.ceil(data.total / 20) : 1

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">DATA DEDUPLICATION</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <Copy size={16} className="text-amber-500" />
          Duplicate Detection
          {data && <span className="text-coal-400 font-normal text-sm ml-1">({data.total.toLocaleString()})</span>}
        </h1>
      </div>
      <div className="flex-1 overflow-auto p-6 space-y-4">
        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={8} /></div>
          ) : error ? (
            <EmptyState title="Unable to load duplicates" message="Failed to retrieve duplicate data." icon={<AlertCircle size={32} />} />
          ) : !data?.items.length ? (
            <EmptyState title="No duplicates detected" message="The system has not found any duplicate documents." icon={<Copy size={32} />} />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr>
                  <th>Document A</th>
                  <th>Document B</th>
                  <th>Similarity</th>
                  <th>Status</th>
                  <th>Detected</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((dup) => (
                  <tr key={dup.id}>
                    <td className="font-mono text-xs text-coal-300 truncate max-w-[120px]">{dup.document_id_a}</td>
                    <td className="font-mono text-xs text-coal-300 truncate max-w-[120px]">{dup.document_id_b}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-coal-800 rounded-full overflow-hidden">
                          <div className="h-full bg-amber-500 rounded-full" style={{ width: `${dup.similarity * 100}%` }} />
                        </div>
                        <span className="text-white font-mono text-xs">{(dup.similarity * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td><StatusBadge status={dup.status} /></td>
                    <td className="text-coal-400 font-mono text-xs">{new Date(dup.detected_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>

        {data && data.total > 20 && (
          <div className="flex items-center justify-between text-xs font-mono text-coal-400">
            <span>{data.total} duplicates</span>
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
