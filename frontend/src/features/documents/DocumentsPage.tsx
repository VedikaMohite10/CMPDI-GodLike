import React, { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload, FileText, Filter, Search, RefreshCw, ChevronRight,
  Download, Cpu, AlertCircle, CheckCircle, Clock, X,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { listDocuments, uploadDocuments, type DocumentSummary } from '../../api/documents'
import {
  IndustrialCard, StatusBadge, LoadingSkeleton, EmptyState, PipelineProgress
} from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'
import { formatDistanceToNow } from 'date-fns'

// File type badge
function FileTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    pdf:   'text-red-400 bg-red-900/30 border-red-500/20',
    docx:  'text-blue-400 bg-blue-900/30 border-blue-500/20',
    xlsx:  'text-green-400 bg-green-900/30 border-green-500/20',
    xls:   'text-green-400 bg-green-900/30 border-green-500/20',
  }
  const cls = colors[type.toLowerCase()] || 'text-coal-300 bg-coal-800 border-coal-700'
  return (
    <span className={`inline-block text-[10px] font-bold uppercase px-1.5 py-0.5 rounded-sm border font-mono ${cls}`}>
      {type}
    </span>
  )
}

// Upload zone
function UploadZone({ onUpload }: { onUpload: (files: File[]) => void }) {
  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length) onUpload(accepted)
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
  })

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-sm p-8 text-center cursor-pointer transition-all duration-200
        ${isDragActive
          ? 'border-amber-500 bg-amber-500/5'
          : 'border-white/[0.1] hover:border-amber-500/40 hover:bg-coal-800/30'
        }`}
    >
      <input {...getInputProps()} />
      <Upload size={28} className={`mx-auto mb-3 ${isDragActive ? 'text-amber-500' : 'text-coal-400'}`} />
      <div className="text-sm font-medium text-white mb-1">
        {isDragActive ? 'Drop files here...' : 'Drop documents or click to browse'}
      </div>
      <div className="text-xs text-coal-400 mb-3">PDF · DOCX · XLSX · XLS</div>
      <div className="flex justify-center gap-2 text-[10px] font-mono text-coal-500">
        {['UPLOAD', '→', 'PARSE', '→', 'OCR', '→', 'EXTRACT', '→', 'EMBED', '→', 'INDEX'].map((s, i) => (
          <span key={i} className={s === '→' ? 'text-coal-700' : 'text-coal-500'}>{s}</span>
        ))}
      </div>
    </div>
  )
}

export default function DocumentsPage() {
  const qc = useQueryClient()
  const [showUpload, setShowUpload] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [page, setPage] = useState(1)
  const [uploadStatus, setUploadStatus] = useState<{ success?: string; error?: string } | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [...QUERY_KEYS.documents, page, statusFilter, typeFilter],
    queryFn: () => listDocuments({ page, page_size: 20, status: statusFilter || undefined, file_type: typeFilter || undefined }),
  })

  const uploadMutation = useMutation({
    mutationFn: uploadDocuments,
    onSuccess: (res) => {
      setUploadStatus({ success: `${res.documents.length} document(s) queued for processing.` })
      qc.invalidateQueries({ queryKey: QUERY_KEYS.documents })
      setShowUpload(false)
    },
    onError: () => setUploadStatus({ error: 'Upload failed. Please check file types and try again.' }),
  })

  const totalPages = data ? Math.ceil(data.total / 20) : 1

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <div className="section-label mb-0.5">AI DOCUMENT PROCESSING</div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              <FileText size={16} className="text-amber-500" />
              Document Intelligence
              {data && <span className="text-coal-400 font-normal text-sm ml-1">({data.total.toLocaleString()})</span>}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => refetch()} className="text-coal-400 hover:text-white transition-colors p-1">
              <RefreshCw size={14} />
            </button>
            <button onClick={() => setShowUpload(!showUpload)} className="btn-primary text-xs">
              <Upload size={13} />
              Upload Documents
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* Upload panel */}
        <AnimatePresence>
          {showUpload && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <IndustrialCard className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="section-label">INGEST DOCUMENTS</div>
                  <button onClick={() => setShowUpload(false)} className="text-coal-400 hover:text-white">
                    <X size={14} />
                  </button>
                </div>
                <UploadZone onUpload={(files) => uploadMutation.mutate(files)} />
                {uploadMutation.isPending && (
                  <div className="mt-3 flex items-center gap-2 text-amber-500 text-xs font-mono">
                    <div className="w-3 h-3 rounded-full border border-amber-500 border-t-transparent animate-spin" />
                    Uploading and queuing for processing...
                  </div>
                )}
              </IndustrialCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Status message */}
        {uploadStatus && (
          <div className={`flex items-center gap-2 p-3 rounded-sm text-xs ${
            uploadStatus.success
              ? 'bg-green-900/20 border border-green-500/20 text-green-300'
              : 'bg-red-900/20 border border-red-500/20 text-red-300'
          }`}>
            {uploadStatus.success ? <CheckCircle size={13} /> : <AlertCircle size={13} />}
            {uploadStatus.success || uploadStatus.error}
            <button onClick={() => setUploadStatus(null)} className="ml-auto"><X size={12} /></button>
          </div>
        )}

        {/* Filters */}
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="industrial-input w-40 text-xs"
          >
            <option value="">All Statuses</option>
            <option value="done">Processed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
            className="industrial-input w-32 text-xs"
          >
            <option value="">All Types</option>
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
            <option value="xlsx">XLSX</option>
          </select>
        </div>

        {/* Table */}
        <IndustrialCard>
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton lines={8} /></div>
          ) : error ? (
            <EmptyState
              title="Unable to load documents"
              message="Failed to retrieve document list from the server."
              icon={<AlertCircle size={32} />}
              action={<button onClick={() => refetch()} className="btn-secondary text-xs">Retry</button>}
            />
          ) : !data?.items.length ? (
            <EmptyState
              title="No documents indexed"
              message="Upload your first document to begin intelligence extraction."
              icon={<FileText size={32} />}
              action={
                <button onClick={() => setShowUpload(true)} className="btn-primary text-xs">
                  <Upload size={12} /> Upload Document
                </button>
              }
            />
          ) : (
            <table className="data-table w-full">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Uploaded</th>
                  <th>Status</th>
                  <th className="w-8"></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((doc: DocumentSummary) => (
                  <tr key={doc.id} className="group">
                    <td>
                      <div className="flex items-center gap-2">
                        <FileText size={12} className="text-coal-400 shrink-0" />
                        <span className="truncate max-w-xs" title={doc.original_filename}>
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td><FileTypeBadge type={doc.file_type} /></td>
                    <td className="text-coal-400">
                      {(doc.file_size_bytes / 1024).toFixed(0)} KB
                    </td>
                    <td className="text-coal-400">
                      {formatDistanceToNow(new Date(doc.upload_date), { addSuffix: true })}
                    </td>
                    <td><StatusBadge status={doc.processing_status} /></td>
                    <td>
                      <Link
                        to={`/documents/${doc.id}`}
                        className="text-coal-400 hover:text-amber-500 transition-colors"
                      >
                        <ChevronRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </IndustrialCard>

        {/* Pagination */}
        {data && data.total > 20 && (
          <div className="flex items-center justify-between text-xs font-mono text-coal-400">
            <span>{data.total} total documents</span>
            <div className="flex items-center gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                className="px-2 py-1 bg-coal-800 rounded-sm disabled:opacity-40"
              >←</button>
              <span>Page {page} of {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
                className="px-2 py-1 bg-coal-800 rounded-sm disabled:opacity-40"
              >→</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
