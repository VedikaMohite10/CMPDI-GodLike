import React, { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, AlertTriangle, Zap, BookOpen, Info } from 'lucide-react'
import { submitQuery } from '../../api/queries'
import { IndustrialCard } from '../../components/ui/DesignSystem'
import { useNavigate } from 'react-router-dom'
import type { ExplainableAIResponse, EvidenceItem } from '../../types'

const SUGGESTED = [
  'Compare coal production trends across all mines',
  'What are the major conflicts in production data for 2023?',
  'Show dispatch figures for the most recent year',
  'Which entities have the highest data confidence?',
  'Explain the change in overburden removal data',
]

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  response?: ExplainableAIResponse
  error?: string
  loading?: boolean
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end mb-4">
      <div className="flex items-start gap-2 max-w-2xl">
        <div className="bg-coal-800 border border-white/[0.08] rounded-sm px-4 py-2.5 text-sm text-white leading-relaxed">
          {content}
        </div>
        <div className="w-6 h-6 rounded-sm bg-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
          <User size={12} className="text-amber-500" />
        </div>
      </div>
    </div>
  )
}

function AIBubble({ response, error, loading }: { response?: ExplainableAIResponse; error?: string; loading?: boolean }) {
  const navigate = useNavigate()

  if (loading) return (
    <div className="flex items-start gap-3 mb-4">
      <div className="w-6 h-6 rounded-sm bg-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
        <Zap size={12} className="text-amber-500 animate-pulse" />
      </div>
      <IndustrialCard className="flex-1 max-w-3xl p-4">
        <div className="flex items-center gap-2 text-amber-500 text-xs font-mono">
          <div className="w-3 h-3 rounded-full border border-amber-500 border-t-transparent animate-spin" />
          Retrieving intelligence from indexed documents…
        </div>
      </IndustrialCard>
    </div>
  )

  if (error) return (
    <div className="flex items-start gap-3 mb-4">
      <div className="w-6 h-6 rounded-sm bg-red-500/20 flex items-center justify-center shrink-0 mt-0.5">
        <AlertTriangle size={12} className="text-red-400" />
      </div>
      <IndustrialCard className="flex-1 max-w-3xl p-4 border-red-500/20">
        <p className="text-sm text-red-300">{error}</p>
      </IndustrialCard>
    </div>
  )

  if (!response) return null

  const noEvidence = !response.evidence || response.evidence.length === 0
  const confidencePct = response.confidence != null ? Math.round(response.confidence * 100) : null

  return (
    <div className="flex items-start gap-3 mb-4">
      <div className="w-6 h-6 rounded-sm bg-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
        <Bot size={12} className="text-amber-500" />
      </div>
      <div className="flex-1 max-w-3xl space-y-3">
        {/* Main answer */}
        <IndustrialCard className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="section-label flex items-center gap-2">
              <span className="amber-dot" /> AI RESPONSE
            </div>
            <div className="flex items-center gap-3">
              {response.reasoning_type && (
                <span className="text-[10px] font-mono text-coal-400 uppercase">{response.reasoning_type}</span>
              )}
              {confidencePct != null && (
                <span className={`text-xs font-mono font-bold ${
                  confidencePct >= 70 ? 'text-status-operational' :
                  confidencePct >= 40 ? 'text-amber-400' : 'text-status-offline'
                }`}>{confidencePct}% confidence</span>
              )}
            </div>
          </div>
          <p className="text-sm text-white leading-relaxed">{response.answer}</p>
          {response.calculation && (
            <div className="mt-3 font-mono text-xs text-amber-500 bg-coal-950 rounded-sm px-3 py-2 border border-amber-500/10">
              {response.calculation}
            </div>
          )}
        </IndustrialCard>

        {/* No evidence info banner */}
        {noEvidence && (
          <div className="flex items-start gap-2 bg-amber-500/5 border border-amber-500/20 rounded-sm p-3">
            <Info size={13} className="text-amber-500 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-300 leading-relaxed">
              No indexed documents were found to ground this answer. Upload and process documents via the <strong>Documents</strong> section, then run Phase 2 fact extraction to enable evidence-backed responses.
            </p>
          </div>
        )}

        {/* Evidence */}
        {response.evidence && response.evidence.length > 0 && (
          <IndustrialCard className="p-4">
            <div className="section-label mb-3 flex items-center gap-2">
              <BookOpen size={11} /> EVIDENCE ({response.evidence.length} sources)
            </div>
            {response.evidence.slice(0, 5).map((e: EvidenceItem, i: number) => (
              <div key={i} className="mb-3 last:mb-0 bg-coal-950 border border-amber-500/10 rounded-sm p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono text-amber-500">SRC {i + 1}</span>
                  {e.document_filename && (
                    <button
                      onClick={() => e.document_id && navigate(`/documents/${e.document_id}`)}
                      className="text-[10px] text-coal-300 hover:text-white transition-colors font-mono truncate max-w-[200px]"
                    >
                      {e.document_filename}
                    </button>
                  )}
                  {e.page_number && <span className="text-[10px] text-coal-500 font-mono">p.{e.page_number}</span>}
                  {e.score != null && (
                    <span className="ml-auto text-[10px] font-mono font-bold text-coal-400">
                      {Math.round(e.score * 100)}%
                    </span>
                  )}
                </div>
                {e.excerpt && (
                  <p className="text-xs text-coal-200 italic leading-relaxed">"{e.excerpt}"</p>
                )}
              </div>
            ))}
          </IndustrialCard>
        )}

        {/* Conflicts */}
        {response.conflicts_surfaced && response.conflicts_surfaced.length > 0 && (
          <IndustrialCard className="p-4 border-amber-500/20">
            <div className="section-label flex items-center gap-2 mb-3">
              <AlertTriangle size={11} className="text-amber-500" /> CONFLICTS DETECTED
            </div>
            {response.conflicts_surfaced.map((c, i: number) => (
              <div key={i} className="bg-coal-950 rounded-sm p-3 mb-2 border border-amber-500/10">
                <div className="text-xs font-semibold text-amber-400 mb-1">{c.entity_name} · {c.metric}</div>
                <div className="flex items-center gap-4 text-xs font-mono">
                  <span>A: <span className="text-white font-bold">{c.value_a ?? '—'}</span></span>
                  <span className="text-coal-400">vs</span>
                  <span>B: <span className="text-white font-bold">{c.value_b ?? '—'}</span></span>
                  {c.delta_pct != null && <span className="text-status-warning font-bold">Δ {c.delta_pct.toFixed(1)}%</span>}
                </div>
              </div>
            ))}
          </IndustrialCard>
        )}
      </div>
    </div>
  )
}

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const mutation = useMutation({ mutationFn: submitQuery })

  const handleSend = async (question: string) => {
    const q = question.trim()
    if (!q || mutation.isPending) return
    setInput('')

    const userId   = `${Date.now()}_u`
    const loadId   = `${Date.now()}_a`
    setMessages(prev => [
      ...prev,
      { id: userId, role: 'user', content: q },
      { id: loadId, role: 'assistant', content: '', loading: true },
    ])

    try {
      const res = await mutation.mutateAsync({ question: q, top_k_semantic: 10 })
      setMessages(prev => prev.map(m =>
        m.id === loadId ? { ...m, loading: false, response: res } : m
      ))
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setMessages(prev => prev.map(m =>
        m.id === loadId ? { ...m, loading: false, error: detail || 'Query failed. Please try again.' } : m
      ))
    }
  }

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(input) }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <div className="section-label mb-0.5">EVIDENCE-GROUNDED AI</div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              <Bot size={16} className="text-amber-500" />
              AI Mining Copilot
            </h1>
          </div>
          <div className="text-[10px] text-coal-400 font-mono text-right">
            <div>Every answer grounded in indexed documents</div>
            <div>No fabrication · Conflicts surfaced</div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto px-6 py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <Bot size={40} className="text-amber-500/30 mb-4" />
            <h2 className="text-lg font-semibold text-white mb-1">AI Mining Copilot</h2>
            <p className="text-coal-400 text-sm max-w-md mb-2 leading-relaxed">
              Ask questions about CMPDI data, documents, entities, production,
              conflicts and reports. All answers are grounded in indexed documents.
            </p>
            <div className="flex items-start gap-2 bg-amber-500/5 border border-amber-500/10 rounded-sm p-3 max-w-md mb-6">
              <Info size={12} className="text-amber-500 shrink-0 mt-0.5" />
              <p className="text-xs text-coal-300 text-left">
                For best results, first upload documents, then run Phase 2 fact extraction from the Documents section.
              </p>
            </div>
            <div className="flex flex-col gap-2 w-full max-w-lg">
              <div className="section-label mb-1">SUGGESTED QUERIES</div>
              {SUGGESTED.map(q => (
                <button key={q} onClick={() => handleSend(q)}
                  className="text-left px-4 py-2.5 bg-coal-900 hover:bg-coal-800 border border-white/[0.06] hover:border-amber-500/20 rounded-sm text-xs text-coal-200 hover:text-white transition-all">
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            <AnimatePresence mode="popLayout">
              {messages.map(msg => (
                <motion.div key={msg.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                  {msg.role === 'user'
                    ? <UserBubble content={msg.content} />
                    : <AIBubble response={msg.response} error={msg.error} loading={msg.loading} />
                  }
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-white/[0.06] px-6 py-4 shrink-0">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3 bg-coal-900 border border-white/[0.08] rounded-sm p-3 focus-within:border-amber-500/30 transition-colors">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about CMPDI data, documents, production trends, conflicts…"
              rows={1}
              disabled={mutation.isPending}
              className="flex-1 bg-transparent text-sm text-white placeholder-coal-400 outline-none resize-none font-sans leading-relaxed disabled:opacity-50"
              style={{ minHeight: '24px', maxHeight: '120px' }}
            />
            <button
              onClick={() => handleSend(input)}
              disabled={!input.trim() || mutation.isPending}
              className="btn-primary py-1.5 px-3 shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send size={13} />
            </button>
          </div>
          <div className="flex items-center justify-between mt-1.5">
            <span className="text-[10px] text-coal-600 font-mono">Enter to send · Shift+Enter for new line</span>
            <span className="text-[10px] text-coal-600 font-mono">Grounded LLM · Evidence-backed</span>
          </div>
        </div>
      </div>
    </div>
  )
}
