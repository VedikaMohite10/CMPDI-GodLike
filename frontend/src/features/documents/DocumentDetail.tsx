import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Download, Cpu, RefreshCw, FileText, Database } from 'lucide-react'
import {
  getDocument, getFactProcessingStatus, processDocumentFacts, getDocumentDownloadUrl,
} from '../../api/documents'
import {
  IndustrialCard, StatusBadge, LoadingSkeleton, MetricStrip, EmptyState, PipelineProgress
} from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'

const STAGE_MAP: Record<string, 'done' | 'running' | 'pending' | 'error'> = {
  done:       'done',
  processing: 'running',
  pending:    'pending',
  failed:     'error',
}

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()

  const { data: doc, isLoading } = useQuery({
    queryKey: QUERY_KEYS.document(id!),
    queryFn: () => getDocument(id!),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.processing_status === 'processing' ? 3000 : false,
  })

  const { data: factStatus, refetch: refetchFact } = useQuery({
    queryKey: ['factStatus', id],
    queryFn: () => getFactProcessingStatus(id!),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === 'running' ? 3000 : false,
  })

  const processMutation = useMutation({
    mutationFn: (force: boolean) => processDocumentFacts(id!, force),
    onSuccess: () => {
      refetchFact()
      qc.invalidateQueries({ queryKey: QUERY_KEYS.document(id!) })
    },
  })

  if (isLoading) return <div className="p-6"><LoadingSkeleton lines={8} /></div>
  if (!doc) return <EmptyState title="Document not found" message="This document may have been deleted." />

  const phase1 = STAGE_MAP[doc.processing_status] || 'pending'
  const phase2 = factStatus ? (STAGE_MAP[factStatus.status] || 'pending') : 'pending'

  const pipelineSteps = [
    { label: 'UPLOAD',  status: 'done' as const },
    { label: 'PARSE',   status: phase1 },
    { label: 'OCR',     status: doc.ocr_required ? phase1 : ('done' as const) },
    { label: 'EMBED',   status: phase1 },
    { label: 'FACTS',   status: phase2 },
    { label: 'INDEXED', status: phase2 === 'done' ? ('done' as const) : 'pending' as const },
  ]

  const factsDone   = factStatus?.status === 'done'
  const factsRunning = factStatus?.status === 'running'

  return (
    <div className="flex flex-col h-full overflow-auto">
      {/* Header */}
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="flex items-center gap-3 mb-3">
          <Link to="/documents" className="text-coal-400 hover:text-white transition-colors">
            <ArrowLeft size={16} />
          </Link>
          <div className="section-label">DOCUMENT INTELLIGENCE</div>
        </div>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              <FileText size={16} className="text-amber-500" />
              {doc.original_filename}
            </h1>
            <div className="flex items-center gap-3 mt-1">
              <StatusBadge status={doc.processing_status} />
              <span className="text-xs text-coal-400 font-mono uppercase">{doc.file_type}</span>
              <span className="text-xs text-coal-400 font-mono">{(doc.file_size_bytes / 1024).toFixed(0)} KB</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Phase 2 extraction button */}
            {doc.processing_status === 'done' && !factsRunning && (
              <button
                onClick={() => processMutation.mutate(factsDone)}
                disabled={processMutation.isPending}
                className="btn-secondary text-xs"
                title={factsDone ? 'Re-run Phase 2 extraction (force)' : 'Start Phase 2 extraction'}
              >
                <Cpu size={12} />
                {processMutation.isPending ? 'Queuing…' : factsDone ? 'Re-run Extraction' : 'Extract Facts'}
              </button>
            )}
            {factsRunning && (
              <div className="flex items-center gap-2 text-amber-500 text-xs font-mono">
                <RefreshCw size={12} className="animate-spin" />
                Extracting facts…
              </div>
            )}
            <a
              href={getDocumentDownloadUrl(doc.id)}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-xs"
            >
              <Download size={12} /> Download Original
            </a>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-4">
        {/* Pipeline */}
        <IndustrialCard className="p-4">
          <div className="section-label mb-3">PROCESSING PIPELINE</div>
          <PipelineProgress steps={pipelineSteps} />
        </IndustrialCard>

        {/* Metadata + Extraction */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <IndustrialCard className="p-4">
            <div className="section-label mb-3">DOCUMENT METADATA</div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: 'File Type',    value: doc.file_type.toUpperCase() },
                { label: 'MIME Type',    value: doc.mime_type },
                { label: 'Size',         value: `${(doc.file_size_bytes / 1024).toFixed(1)} KB` },
                { label: 'OCR Required', value: doc.ocr_required ? 'Yes' : 'No' },
                { label: 'Upload Date',  value: new Date(doc.upload_date).toLocaleDateString() },
                { label: 'Report Date',  value: doc.report_date ? new Date(doc.report_date).toLocaleDateString() : '—' },
              ].map(({ label, value }) => (
                <div key={label}>
                  <span className="section-label block mb-0.5">{label}</span>
                  <span className="text-sm text-white font-mono">{value}</span>
                </div>
              ))}
            </div>
          </IndustrialCard>

          <IndustrialCard className="p-4">
            <div className="section-label mb-3">EXTRACTION SUMMARY</div>
            {doc.extraction_summary ? (
              <div className="grid grid-cols-2 gap-4">
                <MetricStrip label="Text Blocks"     value={doc.extraction_summary.total_text_blocks ?? '—'}     size="sm" />
                <MetricStrip label="Tables"          value={doc.extraction_summary.total_tables ?? '—'}          size="sm" />
                <MetricStrip label="Images"          value={doc.extraction_summary.total_images ?? '—'}          size="sm" />
                <MetricStrip label="Vectors Indexed" value={doc.extraction_summary.total_vectors_indexed ?? '—'} size="sm" />
              </div>
            ) : (
              <p className="text-coal-400 text-xs">
                {doc.processing_status === 'done'
                  ? 'Extraction data not available — metadata may be missing.'
                  : 'Available after document processing completes.'}
              </p>
            )}
          </IndustrialCard>
        </div>

        {/* Phase 2 fact status */}
        {factStatus && (
          <IndustrialCard className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="section-label">PHASE 2 — FACT EXTRACTION STATUS</div>
              <StatusBadge status={factStatus.status} />
            </div>
            {factStatus.status === 'not_started' ? (
              <p className="text-coal-400 text-xs">
                Phase 2 has not been run. Click "Extract Facts" above to start extraction.
              </p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <MetricStrip label="Facts Extracted"  value={factStatus.facts_extracted}  size="sm" />
                <MetricStrip label="Facts Normalized" value={factStatus.facts_normalized} size="sm" />
                <MetricStrip label="Facts Flagged"    value={factStatus.facts_flagged}    size="sm" />
                <MetricStrip label="Conflicts Found"  value={factStatus.conflicts_found}  size="sm" />
              </div>
            )}
            {factStatus.error && (
              <div className="mt-3 text-xs text-red-300 bg-red-900/20 border border-red-500/20 rounded-sm p-2">
                Error: {factStatus.error}
              </div>
            )}
          </IndustrialCard>
        )}

        {/* Related intelligence links */}
        <IndustrialCard className="p-4">
          <div className="section-label mb-3">RELATED INTELLIGENCE</div>
          <div className="flex flex-wrap gap-2">
            <Link to={`/facts?document_id=${doc.id}`} className="btn-secondary text-xs">
              <Database size={12} /> View Extracted Facts
            </Link>
            <Link to={`/conflicts?document_id=${doc.id}`} className="btn-secondary text-xs">
              View Conflicts
            </Link>
            <Link to={`/search?q=${encodeURIComponent(doc.original_filename)}`} className="btn-secondary text-xs">
              Semantic Search
            </Link>
          </div>
        </IndustrialCard>
      </div>
    </div>
  )
}
