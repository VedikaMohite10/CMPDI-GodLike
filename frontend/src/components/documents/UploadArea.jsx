import { useRef, useState } from 'react'

function ArrowRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" width="14" height="14" aria-hidden="true">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}

export default function UploadArea({ compact = false }) {
  const fileInputRef = useRef(null)
  const [files, setFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [status, setStatus] = useState('Ready for ingest')

  const queueFiles = (incomingFiles = []) => {
    const nextFiles = Array.from(incomingFiles).map((file) => ({
      name: file.name,
      size: file.size,
      type: file.type || 'Unknown file',
    }))

    if (!nextFiles.length) return

    setFiles((previous) => [...previous, ...nextFiles])
    setStatus(`${nextFiles.length} file${nextFiles.length > 1 ? 's' : ''} queued`)
    window.setTimeout(() => setStatus('Ready for ingest'), 2000)
  }

  if (compact) {
    return (
      <div
        className={`doc-upload-single ${isDragging ? 'is-dragging' : ''}`}
        onDragEnter={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          setIsDragging(false)
        }}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          queueFiles(event.dataTransfer.files)
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          onChange={(event) => {
            queueFiles(event.target.files)
            event.target.value = ''
          }}
        />

        <button
          type="button"
          className="doc-upload-button-primary"
          onClick={() => fileInputRef.current?.click()}
        >
          <span>UPLOAD DOCUMENTS</span>
          <ArrowRightIcon />
        </button>

        <span className="doc-upload-subtext">
          {status !== 'Ready for ingest' ? status : files.length > 0 ? `${files.length} file(s) queued` : 'PDF, JPG, PNG (Max 50MB)'}
        </span>
      </div>
    )
  }

  return (
    <div
      className={`upload-area ${isDragging ? 'upload-area--dragging' : ''}`}
      onDragEnter={(event) => {
        event.preventDefault()
        setIsDragging(true)
      }}
      onDragOver={(event) => {
        event.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={(event) => {
        event.preventDefault()
        setIsDragging(false)
      }}
      onDrop={(event) => {
        event.preventDefault()
        setIsDragging(false)
        queueFiles(event.dataTransfer.files)
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        hidden
        onChange={(event) => {
          queueFiles(event.target.files)
          event.target.value = ''
        }}
      />

      <button
        type="button"
        className="doc-upload-button-primary"
        onClick={() => fileInputRef.current?.click()}
      >
        <span>UPLOAD DOCUMENTS</span>
        <ArrowRightIcon />
      </button>

      {files.length > 0 && (
        <div className="upload-area__queue" aria-live="polite">
          {files.slice(-3).map((file) => (
            <div key={`${file.name}-${file.size}`} className="upload-area__queue-item">
              <span>{file.name}</span>
              <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
            </div>
          ))}
        </div>
      )}

      <div className="upload-area__status" aria-live="polite">
        {status !== 'Ready for ingest' ? status : 'PDF, JPG, PNG (Max 50MB)'}
      </div>
    </div>
  )
}
