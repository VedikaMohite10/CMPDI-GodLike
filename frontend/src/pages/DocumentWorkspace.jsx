import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import EvidenceExplorer from '../components/evidence/EvidenceExplorer'
import { useAuth } from '../context/AuthContext'
import { getDocument, downloadOriginal, getPhase2Status } from '../api/documents'
import { getFactEvidence } from '../api/review'
import { apiFetch } from '../api/client'

const toneMap = {
  green: 'success',
  yellow: 'warning',
  orange: 'warning',
  red: 'danger',
}

const STATUS_TONE = {
  done: 'success',
  processing: 'warning',
  pending: 'warning',
  failed: 'danger',
}

/** Normalise a backend document record into the shape the UI expects */
function normaliseDoc(d) {
  return {
    id:          d.id,
    title:       d.original_filename ?? d.filename ?? d.id,
    type:        d.file_type ?? 'Unknown',
    subsidiary:  d.subsidiary ?? '—',
    date:        d.created_at ?? d.ingestion_started_at ?? new Date().toISOString(),
    status:      d.processing_status ?? 'pending',
    pages:       d.page_count ?? null,
    extractedFields: d.extracted_fields ?? {},
  }
}

/** Normalise backend facts array into EvidenceExplorer-compatible shape */
function normaliseFacts(facts = []) {
  return facts.map((f) => ({
    id:        f.id,
    label:     f.metric ?? f.fact_type ?? 'Extracted fact',
    value:     f.normalized_value != null ? `${f.normalized_value} ${f.normalized_unit ?? ''}`.trim() : f.raw_value ?? '—',
    page:      f.source_page_number ?? '—',
    section:   f.source_section ?? '—',
    table:     f.source_table ?? '—',
    cell:      f.source_cell ?? '—',
    evidentialTone: f.has_conflict ? 'orange' : f.has_flag ? 'yellow' : 'green',
    confidence: f.confidence_score,
  }))
}

export default function DocumentWorkspace() {
  const { id } = useParams()
  const { token } = useAuth()
  const [doc, setDoc]               = useState(null)
  const [facts, setFacts]           = useState([])
  const [phase2Status, setPhase2Status] = useState(null)
  const [selectedFactId, setSelectedFactId] = useState(null)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [toast, setToast]           = useState('')
  const [factEvidence, setFactEvidence] = useState(null)   // full lineage from GET /facts/{id}/evidence

  const showToast = (msg) => { setToast(msg); window.setTimeout(() => setToast(''), 2500) }

  const loadWorkspace = useCallback(async () => {
    if (!id || !token) return
    setLoading(true)
    setError(null)
    try {
      const [docData, factsData, p2] = await Promise.allSettled([
        getDocument(token, id),
        apiFetch(`/facts?document_id=${id}&page_size=50`, { token }),
        getPhase2Status(token, id),
      ])
      if (docData.status === 'fulfilled')   setDoc(normaliseDoc(docData.value))
      else setError('Could not load document. Check that the backend is running.')
      if (factsData.status === 'fulfilled') setFacts(normaliseFacts(factsData.value?.items ?? []))
      if (p2.status === 'fulfilled')        setPhase2Status(p2.value?.status ?? null)
    } finally {
      setLoading(false)
    }
  }, [id, token])

  useEffect(() => { loadWorkspace() }, [loadWorkspace])

  // Fetch full evidence lineage when a fact is selected
  useEffect(() => {
    if (!selectedFactId || !token) { setFactEvidence(null); return }
    getFactEvidence(token, selectedFactId)
      .then((data) => setFactEvidence(data))
      .catch(() => setFactEvidence(null))
  }, [selectedFactId, token])

  const handlePdfDownload = async () => {
    if (!doc) return
    showToast(`Downloading ${doc.title}…`)
    try {
      const blobUrl = await downloadOriginal(token, doc.id)
      const a = Object.assign(document.createElement('a'), { href: blobUrl, download: doc.title })
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(blobUrl)
    } catch {
      showToast('Download failed — file may not be available.')
    }
  }

  if (loading) {
    return (
      <div className="document-workspace">
        <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '14px' }}>
          Loading workspace…
        </div>
      </div>
    )
  }

  if (error || !doc) {
    return (
      <div className="document-workspace">
        <div style={{ padding: '60px 20px', textAlign: 'center' }}>
          <p style={{ color: '#dc2626', fontWeight: 600, fontSize: '15px' }}>{error ?? 'Document not found.'}</p>
          <button type="button" onClick={loadWorkspace} style={{ marginTop: '12px', padding: '8px 16px', borderRadius: '6px', border: '1px solid currentColor', background: 'transparent', cursor: 'pointer', fontSize: '13px' }}>
            Retry
          </button>
        </div>
      </div>
    )
  }

  const selectedFact = facts.find((f) => f.id === selectedFactId) ?? null

  // Build evidence array for the selected fact (or all facts as a list)
  // If we have full lineage from GET /facts/{id}/evidence, use it; otherwise fall back to fact list
  const evidenceForExplorer = factEvidence
    ? [{
        label:      factEvidence.fact?.metric ?? 'Extracted fact',
        value:      `${factEvidence.fact?.normalized_value ?? ''} ${factEvidence.fact?.normalized_unit ?? ''}`.trim(),
        confidence: factEvidence.extracted?.extraction_confidence != null
                      ? Math.round(factEvidence.extracted.extraction_confidence * 100)
                      : null,
        tone:       (factEvidence.flags ?? []).length > 0 ? 'orange' : 'green',
        // Extra lineage fields EvidenceExplorer surfaces in its chain display
        document:   factEvidence.document?.original_filename ?? factEvidence.document?.filename,
        page:       factEvidence.page?.page_number,
        excerpt:    factEvidence.source?.block?.text?.slice(0, 200),
        source_type: factEvidence.source?.type,
      }]
    : selectedFact
      ? [{ label: selectedFact.label, value: selectedFact.value, page: selectedFact.page, section: selectedFact.section, confidence: selectedFact.confidence }]
      : facts.slice(0, 6).map((f) => ({ label: f.label, value: f.value, page: f.page, section: f.section, confidence: f.confidence }))

  return (
    <div className="document-workspace">
      <div className="page-header">
        <div>
          <p className="eyebrow">Document workspace</p>
          <h1>{doc.title}</h1>
        </div>
        <Button variant="secondary" onClick={handlePdfDownload}>Download PDF</Button>
      </div>

      {toast && <div className="report-toast document-workspace-toast">{toast}</div>}

      <div className="workspace-grid">
        <div className="workspace-main">
          <Card className="workspace-card">
            <div className="workspace-meta">
              <div>
                <div className="workspace-meta__label">Document ID</div>
                <div>{doc.id}</div>
              </div>
              <div>
                <div className="workspace-meta__label">Type</div>
                <div>{doc.type}</div>
              </div>
              <div>
                <div className="workspace-meta__label">Subsidiary</div>
                <div>{doc.subsidiary}</div>
              </div>
              <div>
                <div className="workspace-meta__label">Uploaded</div>
                <div>{new Date(doc.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
              </div>
              <div>
                <div className="workspace-meta__label">Processing</div>
                <Badge tone={STATUS_TONE[doc.status] ?? 'neutral'}>{doc.status}</Badge>
              </div>
              {phase2Status && (
                <div>
                  <div className="workspace-meta__label">Fact Extraction</div>
                  <Badge tone={STATUS_TONE[phase2Status] ?? 'neutral'}>{phase2Status}</Badge>
                </div>
              )}
              {doc.pages && (
                <div>
                  <div className="workspace-meta__label">Pages</div>
                  <div>{doc.pages}</div>
                </div>
              )}
            </div>
          </Card>

          <Card className="workspace-card">
            <div className="section-header">
              <h2>Extracted Facts {facts.length > 0 && <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-muted)' }}>({facts.length})</span>}</h2>
            </div>
            {facts.length === 0 ? (
              <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                {doc.status === 'done' || phase2Status === 'done'
                  ? 'No facts extracted yet. Try re-running Phase 2.'
                  : 'Fact extraction is still in progress…'}
              </div>
            ) : (
              <div className="field-groups">
                {facts.map((fact) => (
                  <button
                    key={fact.id}
                    type="button"
                    className={`field-item ${selectedFactId === fact.id ? 'is-selected' : ''}`}
                    onClick={() => setSelectedFactId(selectedFactId === fact.id ? null : fact.id)}
                  >
                    <div className="field-item__header">
                      <span>{fact.label}</span>
                      <Badge tone={toneMap[fact.evidentialTone] ?? 'neutral'}>{fact.evidentialTone}</Badge>
                    </div>
                    <div className="field-item__value">{fact.value}</div>
                    <div className="field-item__meta">
                      Page {fact.page} · {fact.section} · {fact.table} · {fact.cell}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="workspace-side">
          <Card className="workspace-card">
            <EvidenceExplorer
              evidence={evidenceForExplorer.length > 0 ? { items: evidenceForExplorer } : null}
              title={selectedFact ? selectedFact.label : doc.title}
            />
          </Card>
        </div>
      </div>
    </div>
  )
}
