import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageSquare, Send, CheckCircle, X, AlertTriangle, Info } from 'lucide-react'
import { useForm } from 'react-hook-form'
import {
  listParliamentaryQueries, submitParliamentaryQuery,
  approveParliamentaryQuery, rejectParliamentaryQuery,
  getParliamentaryQuery,
} from '../../api/queries'
import { IndustrialCard, LoadingSkeleton, EmptyState, StatusBadge } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'
import { useAuthStore } from '../../stores/authStore'
import type { ParliamentaryQueryOut } from '../../types'

export default function ParliamentaryPage() {
  const qc = useQueryClient()
  const { hasRole } = useAuthStore()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [approveNote, setApproveNote] = useState('')
  const [rejectNote, setRejectNote] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [submitOk, setSubmitOk] = useState(false)

  const { register, handleSubmit, reset } = useForm<{ question: string }>()

  const { data, isLoading, refetch } = useQuery({
    queryKey: [...QUERY_KEYS.parliamentary, page, statusFilter],
    queryFn: () => listParliamentaryQueries({ status: statusFilter || undefined, page, page_size: 10 }),
  })

  const { data: selected, isLoading: detailLoading } = useQuery({
    queryKey: ['parl-detail', selectedId],
    queryFn: () => getParliamentaryQuery(selectedId!),
    enabled: !!selectedId,
  })

  const submitMutation = useMutation({
    mutationFn: (question: string) => submitParliamentaryQuery(question),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.parliamentary })
      reset()
      setSubmitOk(true)
      setTimeout(() => setSubmitOk(false), 4000)
    },
  })

  const approveMutation = useMutation({
    mutationFn: () => approveParliamentaryQuery(selectedId!, approveNote),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.parliamentary })
      qc.invalidateQueries({ queryKey: ['parl-detail', selectedId] })
      setApproveNote('')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectParliamentaryQuery(selectedId!, rejectNote),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.parliamentary })
      qc.invalidateQueries({ queryKey: ['parl-detail', selectedId] })
      setRejectNote('')
      setShowRejectForm(false)
    },
  })

  const canReview = hasRole('reviewer')
  const items = (data?.items ?? []) as ParliamentaryQueryOut[]
  const total  = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / 10))

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">PARLIAMENTARY QUERY LIFECYCLE</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <MessageSquare size={16} className="text-amber-500" />
          Parliamentary Copilot
        </h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Submit form */}
        <IndustrialCard className="p-4">
          <div className="section-label mb-3">SUBMIT PARLIAMENTARY QUERY</div>
          <form
            onSubmit={handleSubmit(d => submitMutation.mutate(d.question))}
            className="flex gap-3"
          >
            <input
              {...register('question', { required: true, minLength: 10 })}
              placeholder="Enter parliamentary question (min 10 characters)…"
              className="industrial-input flex-1"
            />
            <button type="submit" disabled={submitMutation.isPending} className="btn-primary text-xs shrink-0">
              <Send size={12} />
              {submitMutation.isPending ? 'Submitting…' : 'Submit'}
            </button>
          </form>
          {submitOk && (
            <p className="mt-2 text-xs text-status-operational flex items-center gap-1">
              <CheckCircle size={11} /> Query submitted. AI is drafting an answer — pending reviewer approval.
            </p>
          )}
          {submitMutation.isError && (
            <p className="mt-2 text-xs text-red-300">Submission failed. Please try again.</p>
          )}
        </IndustrialCard>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Query list */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex gap-2">
              <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
                className="industrial-input text-xs flex-1">
                <option value="">All Statuses</option>
                <option value="pending_review">Pending Review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            {isLoading ? <LoadingSkeleton lines={5} /> : (
              <div className="space-y-2">
                {items.map(q => (
                  <button
                    key={String(q.id)}
                    onClick={() => setSelectedId(String(q.id))}
                    className={`w-full text-left p-3 rounded-sm border transition-all ${
                      selectedId === String(q.id)
                        ? 'bg-coal-800 border-amber-500/30'
                        : 'bg-coal-900 border-white/[0.06] hover:border-amber-500/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <StatusBadge status={String(q.status)} size="sm" />
                      {q.has_open_conflicts && (
                        <AlertTriangle size={11} className="text-amber-500" />
                      )}
                    </div>
                    <p className="text-xs text-white leading-snug line-clamp-2">{String(q.question)}</p>
                    <p className="text-[10px] text-coal-500 mt-1 font-mono">
                      {q.created_at ? new Date(String(q.created_at)).toLocaleDateString() : ''}
                    </p>
                  </button>
                ))}
                {items.length === 0 && !isLoading && (
                  <EmptyState title="No queries" message="Submit a parliamentary question above." icon={<MessageSquare size={24} />} />
                )}
              </div>
            )}

            {total > 10 && (
              <div className="flex items-center justify-between text-xs font-mono text-coal-400">
                <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-2 py-1 bg-coal-800 rounded-sm disabled:opacity-40">←</button>
                <span>{page}/{totalPages}</span>
                <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="px-2 py-1 bg-coal-800 rounded-sm disabled:opacity-40">→</button>
              </div>
            )}
          </div>

          {/* Query detail */}
          <div className="lg:col-span-3">
            {!selectedId ? (
              <IndustrialCard className="p-12">
                <EmptyState title="Select a query" message="Click a query to view its AI draft, evidence, and review actions." icon={<MessageSquare size={32} />} />
              </IndustrialCard>
            ) : detailLoading ? (
              <IndustrialCard className="p-6"><LoadingSkeleton lines={8} /></IndustrialCard>
            ) : selected ? (
              <div className="space-y-3">
                {/* Question */}
                <IndustrialCard className="p-4">
                  <div className="section-label mb-2">QUESTION</div>
                  <p className="text-white text-sm leading-relaxed">{String(selected.question || '')}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <StatusBadge status={String(selected.status || '')} />
                    {selected.has_open_conflicts && (
                      <span className="flex items-center gap-1 text-amber-500 text-xs">
                        <AlertTriangle size={11} /> Conflicts disclosed
                      </span>
                    )}
                    {selected.evidence_count != null && (
                      <span className="text-[10px] font-mono text-coal-500 ml-auto">
                        {String(selected.evidence_count)} evidence sources
                      </span>
                    )}
                  </div>
                </IndustrialCard>

                {/* AI Draft */}
                {selected.draft_answer_for_review && (
                  <IndustrialCard className="p-4 border-amber-500/10">
                    <div className="section-label mb-2 flex items-center gap-2">
                      <Info size={11} className="text-amber-500" />
                      AI DRAFT — PENDING HUMAN REVIEW
                    </div>
                    <p className="text-coal-200 text-sm leading-relaxed italic">
                      {String(selected.draft_answer_for_review)}
                    </p>
                  </IndustrialCard>
                )}

                {/* Final answer */}
                {selected.status === 'approved' && selected.final_answer && (
                  <IndustrialCard className="p-4 border-green-500/20">
                    <div className="section-label mb-2 text-status-operational">✓ APPROVED FINAL ANSWER</div>
                    <p className="text-white text-sm leading-relaxed">{String(selected.final_answer)}</p>
                  </IndustrialCard>
                )}

                {/* Evidence */}
                {Array.isArray(selected.evidence) && (selected.evidence as unknown[]).length > 0 && (
                  <IndustrialCard className="p-4">
                    <div className="section-label mb-3">EVIDENCE SOURCES</div>
                    {(selected.evidence as Array<{ document_filename?: string; excerpt?: string }>).slice(0, 3).map((e, i) => (
                      <div key={i} className="mb-2 bg-coal-950 border border-amber-500/10 rounded-sm p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] text-amber-500 font-mono">SRC {i + 1}</span>
                          {e.document_filename && (
                            <span className="text-[10px] text-coal-400 font-mono truncate">{e.document_filename}</span>
                          )}
                        </div>
                        {e.excerpt && <p className="text-xs text-coal-200 italic">"{e.excerpt}"</p>}
                      </div>
                    ))}
                  </IndustrialCard>
                )}

                {/* Review actions (reviewer/admin only) */}
                {selected.status === 'pending_review' && canReview && (
                  <IndustrialCard className="p-4">
                    <div className="section-label mb-3">REVIEWER ACTIONS</div>
                    {/* Approve */}
                    <div className="flex items-end gap-3 mb-3">
                      <input value={approveNote} onChange={e => setApproveNote(e.target.value)}
                        placeholder="Approval note (optional)" className="industrial-input flex-1 text-xs" />
                      <button onClick={() => approveMutation.mutate()}
                        disabled={approveMutation.isPending}
                        className="btn-primary text-xs shrink-0">
                        <CheckCircle size={12} />
                        {approveMutation.isPending ? 'Approving…' : 'Approve & Publish'}
                      </button>
                    </div>
                    {/* Reject */}
                    {!showRejectForm ? (
                      <button onClick={() => setShowRejectForm(true)} className="btn-danger text-xs">
                        <X size={12} /> Reject
                      </button>
                    ) : (
                      <div className="flex items-end gap-3">
                        <input value={rejectNote} onChange={e => setRejectNote(e.target.value)}
                          placeholder="Rejection reason (required)" className="industrial-input flex-1 text-xs" />
                        <button
                          onClick={() => rejectMutation.mutate()}
                          disabled={!rejectNote || rejectMutation.isPending}
                          className="btn-danger text-xs shrink-0"
                        >
                          Confirm Reject
                        </button>
                        <button onClick={() => setShowRejectForm(false)} className="text-coal-400 hover:text-white">
                          <X size={14} />
                        </button>
                      </div>
                    )}
                  </IndustrialCard>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
