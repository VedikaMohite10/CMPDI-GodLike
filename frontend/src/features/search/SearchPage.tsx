import React, { useState, useEffect } from 'react'
import { Search as SearchIcon, FileText, BookOpen, AlertCircle, X, Info } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { semanticSearch } from '../../api/analytics'
import { IndustrialCard, LoadingSkeleton } from '../../components/ui/DesignSystem'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type { SearchHit } from '../../types'

export default function SearchPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 500)
    return () => clearTimeout(t)
  }, [query])

  const searchMutation = useMutation({
    mutationFn: (q: string) => semanticSearch(q, 20),
  })

  useEffect(() => {
    if (debouncedQuery.trim().length >= 2) {
      searchMutation.mutate(debouncedQuery)
    }
  }, [debouncedQuery])

  // Also trigger if URL has a q param on mount
  useEffect(() => {
    const q = searchParams.get('q')
    if (q && q.length >= 2) searchMutation.mutate(q)
  }, [])

  const results = searchMutation.data?.results || []

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">SEMANTIC INTELLIGENCE SEARCH</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <SearchIcon size={16} className="text-amber-500" />
          Global Search
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Search bar */}
        <div className="relative max-w-2xl">
          <SearchIcon size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-amber-500" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Semantic search across all indexed documents and facts…"
            className="industrial-input pl-10 pr-10 py-3 text-sm"
            autoFocus
          />
          {query && (
            <button onClick={() => { setQuery(''); setDebouncedQuery('') }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-coal-400 hover:text-white">
              <X size={14} />
            </button>
          )}
        </div>

        {/* Status */}
        {debouncedQuery && (
          <div className="text-xs font-mono text-coal-400">
            {searchMutation.isPending
              ? <span className="text-amber-500">Searching intelligence…</span>
              : results.length > 0
                ? <span>{results.length} results for "<span className="text-white">{debouncedQuery}</span>"</span>
                : <span>No results for "{debouncedQuery}"</span>
            }
          </div>
        )}

        {searchMutation.isPending && <LoadingSkeleton lines={6} />}

        {/* No results hint */}
        {!searchMutation.isPending && debouncedQuery && results.length === 0 && !searchMutation.isPending && (
          <div className="flex items-start gap-2 bg-amber-500/5 border border-amber-500/10 rounded-sm p-3 max-w-xl">
            <Info size={13} className="text-amber-500 shrink-0 mt-0.5" />
            <p className="text-xs text-coal-300">
              No indexed content found. Upload documents and run Phase 2 fact extraction to enable semantic search.
            </p>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-2 max-w-3xl">
            {results.map((hit: SearchHit, i: number) => (
              <IndustrialCard
                key={i}
                className="p-4 hover:border-amber-500/20 transition-colors cursor-pointer"
                onClick={() => hit.document_id && navigate(`/documents/${hit.document_id}`)}
              >
                <div className="flex items-start gap-3">
                  <FileText size={14} className="text-amber-500 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1.5 flex-wrap">
                      {hit.document_filename && (
                        <span className="text-[10px] bg-coal-800 border border-white/[0.06] rounded-sm px-2 py-0.5 font-mono text-coal-300 truncate max-w-[200px]">
                          {hit.document_filename}
                        </span>
                      )}
                      <span className="text-[10px] font-mono text-coal-400">p.{hit.page_number}</span>
                      <span className={`ml-auto text-xs font-mono font-bold ${
                        hit.score >= 0.7 ? 'text-status-operational' :
                        hit.score >= 0.4 ? 'text-amber-400' : 'text-coal-400'
                      }`}>{Math.round(hit.score * 100)}%</span>
                    </div>
                    {hit.text_excerpt && (
                      <p className="text-sm text-coal-200 leading-relaxed italic">
                        "…{hit.text_excerpt}…"
                      </p>
                    )}
                    <div className="flex items-center gap-1 mt-1.5">
                      <BookOpen size={10} className="text-coal-500" />
                      <span className="text-[10px] text-coal-500 font-mono">{hit.block_type}</span>
                    </div>
                  </div>
                </div>
              </IndustrialCard>
            ))}
          </div>
        )}

        {/* Idle */}
        {!query && (
          <div className="text-center py-16">
            <SearchIcon size={44} className="text-coal-700 mx-auto mb-4" />
            <p className="text-coal-400 text-sm">Type to search across all indexed documents and facts</p>
            <p className="text-coal-600 text-xs mt-1">Powered by vector semantic search · Min 2 characters</p>
          </div>
        )}
      </div>
    </div>
  )
}
