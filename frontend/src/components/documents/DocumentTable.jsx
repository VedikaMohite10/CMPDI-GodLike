import { useMemo } from 'react'
import { Link } from 'react-router-dom'

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}

function MoreIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
      <circle cx="12" cy="5" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="12" cy="19" r="1" />
    </svg>
  )
}

export default function DocumentTable({ documents, selectedDocId, onSelectDoc, onDownload }) {
  const getStatusClass = (status) => {
    switch (status) {
      case 'Verified':
        return 'doc-pill-status--verified'
      case 'Processed':
        return 'doc-pill-status--processed'
      case 'Pending':
        return 'doc-pill-status--pending'
      case 'Under Review':
        return 'doc-pill-status--review'
      case 'Failed':
        return 'doc-pill-status--failed'
      default:
        return 'doc-pill-status--processed'
    }
  }

  return (
    <div className="doc-table-wrapper">
      <table className="doc-table">
        <thead>
          <tr>
            <th>DOCUMENT NAME</th>
            <th>TYPE</th>
            <th>SUBSIDIARY</th>
            <th>UPLOAD DATE</th>
            <th>STATUS</th>
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => {
            const isPdf = (doc.fileType || 'pdf') === 'pdf'
            const isSelected = doc.id === selectedDocId

            return (
              <tr
                key={doc.id}
                className={isSelected ? 'is-selected' : ''}
                onClick={() => onSelectDoc && onSelectDoc(doc)}
              >
                <td>
                  <div className="doc-name-cell">
                    <div className={`doc-type-badge-icon ${isPdf ? 'doc-type-badge-icon--pdf' : 'doc-type-badge-icon--doc'}`}>
                      {isPdf ? 'PDF' : 'DOC'}
                    </div>
                    <div className="doc-title-text">
                      <strong>{doc.title}</strong>
                      <span>{doc.id}</span>
                    </div>
                  </div>
                </td>
                <td>{doc.type}</td>
                <td>
                  <strong style={{ color: 'var(--navy-900)', fontSize: '12px' }}>{doc.subsidiary}</strong>
                </td>
                <td>
                  {new Date(doc.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                </td>
                <td>
                  <span className={`doc-pill-status ${getStatusClass(doc.status)}`}>
                    {doc.status}
                  </span>
                </td>
                <td>
                  <div className="doc-action-btns" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="doc-icon-btn"
                      title="Preview Document"
                      onClick={() => onSelectDoc && onSelectDoc(doc)}
                    >
                      <EyeIcon />
                    </button>
                    <button
                      type="button"
                      className="doc-icon-btn"
                      title="Download Document"
                      onClick={() => onDownload && onDownload(doc)}
                    >
                      <DownloadIcon />
                    </button>
                    <Link
                      to={`/documents/${doc.id}`}
                      className="doc-icon-btn"
                      title="Inspect Workspace"
                    >
                      <MoreIcon />
                    </Link>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
