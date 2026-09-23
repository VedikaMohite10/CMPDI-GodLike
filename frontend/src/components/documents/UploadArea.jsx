/**
 * UploadArea — real file upload wired to POST /documents/upload.
 *
 * Flow:
 *  1. User selects / drops files
 *  2. Immediately POST multipart to backend → get [{id, processing_status}]
 *  3. Poll GET /documents/{id}/status every 2s per document
 *  4. Show per-file status (queued / uploading / processing / done / failed)
 *  5. On done: auto-trigger Phase 2 (fact extraction)
 */
import { useCallback, useRef, useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { uploadDocuments, getDocumentStatus, triggerPhase2 } from '../../api/documents'
import { ApiError } from '../../api/client'

const POLL_INTERVAL_MS = 2000

function ArrowRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" width="14" height="14" aria-hidden="true">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}

/** Map backend processing_status to a human label + CSS modifier */
function statusLabel(status) {
  const map = {
    pending:    { text: 'Queued',     mod: 'pending' },
    processing: { text: 'Processing', mod: 'processing' },
    done:       { text: 'Done',       mod: 'done' },
    failed:     { text: 'Failed',     mod: 'failed' },
    uploading:  { text: 'Uploading',  mod: 'pending' },
  }
  return map[status] ?? { text: status, mod: 'pending' }
}

export default function UploadArea({ compact = false, onUploadComplete }) {
  const { token } = useAuth()
  const fileInputRef = useRef(null)
  const pollRefs    = useRef({})   // docId → intervalId
  const [files, setFiles]       = useState([])   // [{name, size, status, docId, error}]
  const [isDragging, setIsDragging] = useState(false)

  // --- Polling ---
  const startPolling = useCallback((docId) => {
    if (pollRefs.current[docId]) return

    const intervalId = window.setInterval(async () => {
      try {
        const { processing_status } = await getDocumentStatus(token, docId)

        setFiles((prev) =>
          prev.map((f) => f.docId === docId ? { ...f, status: processing_status } : f),
        )

        if (processing_status === 'done' || processing_status === 'failed') {
          window.clearInterval(pollRefs.current[docId])
          delete pollRefs.current[docId]

          // Auto-trigger Phase 2 when extraction is done
          if (processing_status === 'done') {
            await triggerPhase2(token, docId).catch(() => {/* non-fatal */})
            onUploadComplete?.()
          }
        }
      } catch {
        // polling error — keep trying
      }
    }, POLL_INTERVAL_MS)

    pollRefs.current[docId] = intervalId
  }, [token, onUploadComplete])

  // --- Upload ---
  const queueFiles = useCallback(async (incomingFiles = []) => {
    const list = Array.from(incomingFiles)
    if (!list.length) return

    // Immediately show files as "uploading"
    const stubs = list.map((f) => ({
      name: f.name,
      size: f.size,
      status: 'uploading',
      docId: null,
      error: null,
    }))
    setFiles((prev) => [...prev, ...stubs])

    try {
      const { documents } = await uploadDocuments(token, list)

      // Replace stubs with real doc IDs + initial status
      setFiles((prev) => {
        const updated = [...prev]
        stubs.forEach((stub, i) => {
          const idx = updated.findIndex((f) => f === stub)
          if (idx !== -1 && documents[i]) {
            updated[idx] = {
              ...stub,
              docId: documents[i].id,
              status: documents[i].processing_status,
            }
          }
        })
        return updated
      })

      // Start polling for each uploaded doc
      documents.forEach((doc) => startPolling(doc.id))
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : 'Upload failed'
      setFiles((prev) =>
        prev.map((f) =>
          stubs.includes(f) ? { ...f, status: 'failed', error: msg } : f,
        ),
      )
    }
  }, [token, startPolling])

  // --- Drag handlers ---
  const onDragEnter = (e) => { e.preventDefault(); setIsDragging(true) }
  const onDragOver  = (e) => { e.preventDefault(); setIsDragging(true) }
  const onDragLeave = (e) => { e.preventDefault(); setIsDragging(false) }
  const onDrop      = (e) => {
    e.preventDefault()
    setIsDragging(false)
    queueFiles(e.dataTransfer.files)
  }
  const onFileChange = (e) => {
    queueFiles(e.target.files)
    e.target.value = ''
  }

  // Summary for the status line
  const uploading  = files.filter((f) => f.status === 'uploading' || f.status === 'pending').length
  const processing = files.filter((f) => f.status === 'processing').length
  const done       = files.filter((f) => f.status === 'done').length
  const failed     = files.filter((f) => f.status === 'failed').length
  const total      = files.length

  const summaryText =
    total === 0 ? 'PDF, JPG, PNG (Max 100 MB)' :
    uploading  ? `Uploading ${uploading} file${uploading > 1 ? 's' : ''}…` :
    processing ? `Processing ${processing} file${processing > 1 ? 's' : ''}…` :
    failed     ? `${failed} failed · ${done} done` :
    `${done} / ${total} done`

  const dragProps = { onDragEnter, onDragOver, onDragLeave, onDrop }

  if (compact) {
    return (
      <div className={`doc-upload-single ${isDragging ? 'is-dragging' : ''}`} {...dragProps}>
        <input ref={fileInputRef} type="file" multiple hidden onChange={onFileChange} />
        <button type="button" className="doc-upload-button-primary" onClick={() => fileInputRef.current?.click()}>
          <span>UPLOAD DOCUMENTS</span>
          <ArrowRightIcon />
        </button>
        <span className="doc-upload-subtext">{summaryText}</span>
      </div>
    )
  }

  return (
    <div className={`upload-area ${isDragging ? 'upload-area--dragging' : ''}`} {...dragProps}>
      <input ref={fileInputRef} type="file" multiple hidden onChange={onFileChange} />

      <button type="button" className="doc-upload-button-primary" onClick={() => fileInputRef.current?.click()}>
        <span>UPLOAD DOCUMENTS</span>
        <ArrowRightIcon />
      </button>

      {/* Per-file status list */}
      {files.length > 0 && (
        <div className="upload-area__queue" aria-live="polite">
          {files.slice(-5).map((f, i) => {
            const { text, mod } = statusLabel(f.status)
            return (
              <div
                key={`${f.name}-${i}`}
                className="upload-area__queue-item"
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {f.name}
                </span>
                <span style={{
                  fontSize: '11px', fontWeight: 700, padding: '2px 8px',
                  borderRadius: '20px', flexShrink: 0,
                  background:
                    mod === 'done'       ? 'rgba(22,163,74,0.15)' :
                    mod === 'failed'     ? 'rgba(220,38,38,0.15)' :
                    mod === 'processing' ? 'rgba(234,179,8,0.15)'  :
                    'rgba(148,163,184,0.15)',
                  color:
                    mod === 'done'       ? '#16a34a' :
                    mod === 'failed'     ? '#dc2626' :
                    mod === 'processing' ? '#ca8a04'  :
                    '#94a3b8',
                }}>
                  {text}
                </span>
              </div>
            )
          })}
          {files.length > 5 && (
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', paddingTop: '4px' }}>
              + {files.length - 5} more
            </div>
          )}
        </div>
      )}

      <div className="upload-area__status" aria-live="polite">{summaryText}</div>
    </div>
  )
}
