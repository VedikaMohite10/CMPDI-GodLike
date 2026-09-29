import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Tag, AlertCircle } from 'lucide-react'
import { listTopics } from '../../api/analytics'
import { IndustrialCard, LoadingSkeleton, EmptyState } from '../../components/ui/DesignSystem'

export default function TopicsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error } = useQuery({
    queryKey: ['topics', page],
    queryFn: () => listTopics({ page, page_size: 30 }),
  })

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">KNOWLEDGE TAXONOMY</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <Tag size={16} className="text-amber-500" />
          Topics
        </h1>
      </div>
      <div className="flex-1 overflow-auto p-6">
        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={8} /></div>
          ) : error ? (
            <EmptyState title="Unable to load topics" message="Failed to retrieve topics." icon={<AlertCircle size={32} />} />
          ) : !data?.items?.length ? (
            <EmptyState title="No topics found" message="Topics are extracted during document processing." icon={<Tag size={32} />} />
          ) : (
            <table className="data-table w-full">
              <thead><tr><th>Topic</th><th>Documents</th><th>Facts</th></tr></thead>
              <tbody>
                {data.items.map((t: Record<string, unknown>, i: number) => (
                  <tr key={i}>
                    <td className="font-semibold text-white">{String(t.name || t.topic || '—')}</td>
                    <td className="font-mono">{String(t.document_count ?? '—')}</td>
                    <td className="font-mono">{String(t.fact_count ?? '—')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>
      </div>
    </div>
  )
}
