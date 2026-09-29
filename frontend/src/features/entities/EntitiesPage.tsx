import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Search, AlertCircle } from 'lucide-react'
import { listEntities } from '../../api/entities'
import { IndustrialCard, LoadingSkeleton, EmptyState, StatusBadge } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'

export default function EntitiesPage() {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [...QUERY_KEYS.entities, page, q],
    queryFn: () => listEntities({ page, page_size: 30, q: q || undefined }),
  })

  const totalPages = data ? Math.ceil(data.total / 30) : 1

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <div className="section-label mb-0.5">KNOWLEDGE GRAPH</div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              <BookOpen size={16} className="text-amber-500" />
              Canonical Entities
              {data && <span className="text-coal-400 font-normal text-sm ml-1">({data.total.toLocaleString()})</span>}
            </h1>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Search */}
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-coal-400" />
          <input
            type="text"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1) }}
            placeholder="Search entities by name..."
            className="industrial-input pl-9"
          />
        </div>

        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={10} /></div>
          ) : error ? (
            <EmptyState title="Unable to load entities" message="Failed to retrieve entity list." icon={<AlertCircle size={32} />} action={<button onClick={() => refetch()} className="btn-secondary text-xs">Retry</button>} />
          ) : !data?.items.length ? (
            <EmptyState title="No entities found" message="Process documents with Phase 2 to extract canonical entities." icon={<BookOpen size={32} />} />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr>
                  <th>Entity Name</th>
                  <th>Type</th>
                  <th>Aliases</th>
                  <th>Indexed</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((entity) => (
                  <tr key={entity.id} className="group">
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="amber-dot shrink-0" />
                        <span className="font-semibold text-white">{entity.canonical_name}</span>
                      </div>
                    </td>
                    <td>
                      <span className="text-[10px] font-mono uppercase text-coal-300 bg-coal-800 px-2 py-0.5 rounded-sm">
                        {entity.entity_type}
                      </span>
                    </td>
                    <td className="text-coal-400 text-xs">
                      {entity.aliases?.slice(0, 3).join(', ') || '—'}
                      {entity.aliases?.length > 3 && ` +${entity.aliases.length - 3}`}
                    </td>
                    <td className="text-coal-400 text-xs font-mono">
                      {new Date(entity.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>

        {/* Pagination */}
        {data && data.total > 30 && (
          <div className="flex items-center justify-between text-xs font-mono text-coal-400">
            <span>{data.total} entities</span>
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
