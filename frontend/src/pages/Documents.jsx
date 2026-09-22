import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import DocumentTable from '../components/documents/DocumentTable'
import UploadArea from '../components/documents/UploadArea'
import { documentTypes, documentsMock, statuses, subsidiaries } from '../data/documentsMock'
import '../styles/DocumentsPage.css'

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  )
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

const ITEMS_PER_PAGE = 8

export default function DocumentsPage() {
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('All Document Types')
  const [subsidiaryFilter, setSubsidiaryFilter] = useState('All Subsidiaries')
  const [statusFilter, setStatusFilter] = useState('All Status')
  const [activeTab, setActiveTab] = useState('All')
  const [page, setPage] = useState(1)
  const [toast, setToast] = useState('')
  const [selectedDoc, setSelectedDoc] = useState(documentsMock[0])
  const [isPreviewOpen, setIsPreviewOpen] = useState(true)

  const filtered = useMemo(() => {
    return documentsMock.filter((doc) => {
      const matchesSearch =
        !search ||
        [doc.title, doc.id, doc.subsidiary, doc.type]
          .join(' ')
          .toLowerCase()
          .includes(search.toLowerCase())

      const matchesType = typeFilter === 'All Document Types' || doc.type === typeFilter
      const matchesSub = subsidiaryFilter === 'All Subsidiaries' || doc.subsidiary === subsidiaryFilter

      let matchesStatus = true
      if (statusFilter !== 'All Status') {
        matchesStatus = doc.status === statusFilter
      }

      let matchesTab = true
      if (activeTab === 'Processed') matchesTab = doc.status === 'Processed'
      if (activeTab === 'Pending') matchesTab = doc.status === 'Pending' || doc.status === 'Under Review'
      if (activeTab === 'Failed') matchesTab = doc.status === 'Failed'
      if (activeTab === 'Verified') matchesTab = doc.status === 'Verified'

      return matchesSearch && matchesType && matchesSub && matchesStatus && matchesTab
    })
  }, [search, typeFilter, subsidiaryFilter, statusFilter, activeTab])

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE))
  const currentPage = Math.min(page, totalPages)
  const paginated = filtered.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)

  const handleResetFilters = () => {
    setSearch('')
    setTypeFilter('All Document Types')
    setSubsidiaryFilter('All Subsidiaries')
    setStatusFilter('All Status')
    setActiveTab('All')
    setPage(1)
  }

  const handleSelectDoc = (doc) => {
    setSelectedDoc(doc)
    setIsPreviewOpen(true)
  }

  const handleDownloadDoc = (doc) => {
    setToast(`Downloading ${doc.title}...`)
    window.setTimeout(() => setToast(''), 2200)
  }

  return (
    <div className="documents-redesign">
      {toast && (
        <div style={{
          position: 'fixed',
          top: '100px',
          right: '32px',
          background: '#123a3e',
          color: '#ffffff',
          padding: '12px 20px',
          borderRadius: '4px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          zIndex: 100,
          fontSize: '13px',
          fontWeight: 600,
        }}>
          {toast}
        </div>
      )}

      <main className="documents-shell">
        {/* Document Introduction & Metrics Banner */}
        <section className="doc-intro-row">
          <div className="doc-intro-copy">
            <p className="doc-kicker">DOCUMENT INTELLIGENCE</p>
            <h1>Documents &amp; Records</h1>
            <p>
              Centralized document ingestion, processing, classification, and verification across CIL subsidiaries, enabling traceable and compliant mining operations.
            </p>
          </div>

          <div className="doc-metrics-grid">
            <div className="doc-metric-card">
              <div className="doc-metric-card__val">1,48,640</div>
              <div className="doc-metric-card__label">Total Documents</div>
              <div className="doc-metric-card__sub doc-metric-card__sub--green">+18.2% vs last month</div>
            </div>

            <div className="doc-metric-card">
              <div className="doc-metric-card__val">1,12,430</div>
              <div className="doc-metric-card__label">Processed</div>
              <div className="doc-metric-card__sub doc-metric-card__sub--green">75.7% of total</div>
            </div>

            <div className="doc-metric-card">
              <div className="doc-metric-card__val">9,860</div>
              <div className="doc-metric-card__label">Pending Review</div>
              <div className="doc-metric-card__sub doc-metric-card__sub--orange">6.6% of total</div>
            </div>

            <div className="doc-metric-card">
              <div className="doc-metric-card__val">1,24,320</div>
              <div className="doc-metric-card__label">Verified</div>
              <div className="doc-metric-card__sub doc-metric-card__sub--green">83.7% of total</div>
            </div>
          </div>
        </section>

        {/* Operational Control Bar */}
        <section className="doc-control-bar">
          <UploadArea compact />

          <div className="doc-filters-row">
            <div className="doc-search-box">
              <SearchIcon />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(1)
                }}
                placeholder="Search documents by title, type, subsidiary, or keyword..."
              />
            </div>

            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value)
                setPage(1)
              }}
              className="doc-select-filter"
            >
              {documentTypes.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>

            <select
              value={subsidiaryFilter}
              onChange={(e) => {
                setSubsidiaryFilter(e.target.value)
                setPage(1)
              }}
              className="doc-select-filter"
            >
              {subsidiaries.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              className="doc-select-filter"
            >
              {statuses.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>

            <button
              type="button"
              className="doc-reset-btn"
              onClick={handleResetFilters}
            >
              Reset
            </button>
          </div>
        </section>

        {/* Main Document Split Grid */}
        <section className={`doc-main-split ${isPreviewOpen && selectedDoc ? 'has-preview' : ''}`}>
          <div className="doc-register-card">
            {/* Status Tabs Strip */}
            <div className="doc-status-tabs">
              <button
                type="button"
                className={`doc-status-tab ${activeTab === 'All' ? 'is-active' : ''}`}
                onClick={() => { setActiveTab('All'); setPage(1); }}
              >
                All Documents (1,48,640)
              </button>
              <button
                type="button"
                className={`doc-status-tab ${activeTab === 'Processed' ? 'is-active' : ''}`}
                onClick={() => { setActiveTab('Processed'); setPage(1); }}
              >
                Processed (1,12,430)
              </button>
              <button
                type="button"
                className={`doc-status-tab ${activeTab === 'Pending' ? 'is-active' : ''}`}
                onClick={() => { setActiveTab('Pending'); setPage(1); }}
              >
                Pending (9,860)
              </button>
              <button
                type="button"
                className={`doc-status-tab ${activeTab === 'Failed' ? 'is-active' : ''}`}
                onClick={() => { setActiveTab('Failed'); setPage(1); }}
              >
                Failed (4,900)
              </button>
              <button
                type="button"
                className={`doc-status-tab ${activeTab === 'Verified' ? 'is-active' : ''}`}
                onClick={() => { setActiveTab('Verified'); setPage(1); }}
              >
                Verified (1,24,320)
              </button>
            </div>

            {/* Document Table */}
            {filtered.length === 0 ? (
              <div style={{ padding: '48px 20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                <p style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>No documents match the active search or filters.</p>
                <p style={{ margin: '6px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>Try resetting the filters or modifying your search query.</p>
              </div>
            ) : (
              <DocumentTable
                documents={paginated}
                selectedDocId={selectedDoc?.id}
                onSelectDoc={handleSelectDoc}
                onDownload={handleDownloadDoc}
              />
            )}

            {/* Pagination Footer */}
            <div className="doc-pagination">
              <div>
                Showing {filtered.length === 0 ? 0 : (currentPage - 1) * ITEMS_PER_PAGE + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, filtered.length)} of {filtered.length} documents
              </div>

              <div className="doc-pagination-controls">
                <button
                  type="button"
                  className="doc-page-btn"
                  disabled={currentPage === 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  &lt;
                </button>
                <button
                  type="button"
                  className={`doc-page-btn ${currentPage === 1 ? 'is-current' : ''}`}
                  onClick={() => setPage(1)}
                >
                  1
                </button>
                {totalPages > 1 && (
                  <button
                    type="button"
                    className={`doc-page-btn ${currentPage === 2 ? 'is-current' : ''}`}
                    onClick={() => setPage(2)}
                  >
                    2
                  </button>
                )}
                {totalPages > 2 && (
                  <button
                    type="button"
                    className={`doc-page-btn ${currentPage === 3 ? 'is-current' : ''}`}
                    onClick={() => setPage(3)}
                  >
                    3
                  </button>
                )}
                {totalPages > 3 && (
                  <span style={{ padding: '0 4px', color: 'var(--text-muted)' }}>...</span>
                )}
                {totalPages > 3 && (
                  <button
                    type="button"
                    className={`doc-page-btn ${currentPage === totalPages ? 'is-current' : ''}`}
                    onClick={() => setPage(totalPages)}
                  >
                    {totalPages}
                  </button>
                )}
                <button
                  type="button"
                  className="doc-page-btn"
                  disabled={currentPage === totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  &gt;
                </button>
              </div>
            </div>
          </div>

          {/* Right Live Preview Panel */}
          {isPreviewOpen && selectedDoc && (
            <div className="doc-preview-panel">
              <div className="doc-preview-header">
                <h3>Document Preview</h3>
                <button
                  type="button"
                  className="doc-preview-close"
                  onClick={() => setIsPreviewOpen(false)}
                  title="Close preview"
                >
                  <CloseIcon />
                </button>
              </div>

              <div className="doc-preview-canvas">
                <div className="doc-preview-toolbar">
                  <div className="doc-preview-toolbar__left">
                    <span>≡</span>
                    <span>1 / {selectedDoc.pages || 12}</span>
                    <span>−</span>
                    <span>100%</span>
                    <span>+</span>
                  </div>
                  <div className="doc-preview-toolbar__right">
                    <span>⬇</span>
                    <span>🖨</span>
                    <span>⋮</span>
                  </div>
                </div>

                <div className="doc-preview-page-mock">
                  <div className="doc-pdf-header-banner">
                    <div className="doc-pdf-logo-mark">
                      <div className="doc-pdf-logo-box">CIL</div>
                      <div>
                        <strong style={{ display: 'block', fontSize: '10px', lineHeight: 1 }}>कोल इण्डिया लिमिटेड</strong>
                        <span style={{ fontSize: '9px', color: '#4a4c50' }}>Coal India Limited</span>
                      </div>
                    </div>

                    <div style={{ textAlign: 'right', fontSize: '11px', fontWeight: 800, color: '#123a3e' }}>
                      cmpdi
                    </div>
                  </div>

                  <div className="doc-pdf-doc-title">
                    <h4>{selectedDoc.title}</h4>
                    <p>{selectedDoc.subsidiary} Subsidiary • FY 2025-26</p>
                  </div>

                  <div className="doc-pdf-image-box">
                    <DocIcon />
                    <span>INSTITUTIONAL MINING EVIDENCE</span>
                    <small style={{ marginTop: '4px', opacity: 0.8, fontSize: '9px' }}>
                      ID: {selectedDoc.id} • Verified Ingestion Log
                    </small>
                  </div>

                  <div style={{ fontSize: '10px', color: '#4a4c50', lineHeight: 1.5, borderTop: '1px solid #e8e4dc', paddingTop: '10px' }}>
                    <strong>Extraction Summary:</strong>
                    <ul style={{ margin: '4px 0 0', paddingLeft: '14px' }}>
                      <li>OCR Validation Status: {selectedDoc.ocrStatus}</li>
                      <li>Validation Gate: {selectedDoc.validationStatus}</li>
                      <li>Document Classification: {selectedDoc.type}</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="doc-preview-meta">
                <div className="doc-preview-meta-row">
                  <span>Document Name</span>
                  <strong>{selectedDoc.title}</strong>
                </div>
                <div className="doc-preview-meta-row">
                  <span>Type</span>
                  <strong>{selectedDoc.type}</strong>
                </div>
                <div className="doc-preview-meta-row">
                  <span>Subsidiary</span>
                  <strong>{selectedDoc.subsidiary}</strong>
                </div>
                <div className="doc-preview-meta-row">
                  <span>Upload Date</span>
                  <strong>{new Date(selectedDoc.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</strong>
                </div>
                <div className="doc-preview-meta-row">
                  <span>Status</span>
                  <span className={`doc-pill-status doc-pill-status--${selectedDoc.status === 'Verified' ? 'verified' : selectedDoc.status === 'Processed' ? 'processed' : selectedDoc.status === 'Failed' ? 'failed' : 'pending'}`}>
                    {selectedDoc.status}
                  </span>
                </div>

                <div className="doc-preview-actions">
                  <Link to={`/documents/${selectedDoc.id}`} className="doc-inspect-btn">
                    Inspect Workspace &rarr;
                  </Link>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
