import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import EvidenceExplorer from '../components/evidence/EvidenceExplorer'
import { documentsMock } from '../data/documentsMock'
import { evidenceMock } from '../data/evidenceMock'

const toneMap = {
  green: 'success',
  yellow: 'warning',
  orange: 'warning',
  red: 'danger',
}

export default function DocumentWorkspace() {
  const { id } = useParams()
  const [selectedField, setSelectedField] = useState(null)
  const [toast, setToast] = useState('')

  const document = useMemo(
    () => documentsMock.find((item) => item.id === id) || documentsMock[0],
    [id],
  )

  const evidence = selectedField ? evidenceMock[selectedField] || evidenceMock.productionProof : evidenceMock.productionProof

  const fields = Object.entries(document.extractedFields || {})

  const handlePdfDownload = () => {
    setToast(`${document.title} PDF package queued for download.`)
    window.setTimeout(() => setToast(''), 2200)
  }

  return (
    <div className="document-workspace">
      <div className="page-header">
        <div>
          <p className="eyebrow">Document workspace</p>
          <h1>{document.title}</h1>
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
                <div>{document.id}</div>
              </div>
              <div>
                <div className="workspace-meta__label">Type</div>
                <div>{document.type}</div>
              </div>
              <div>
                <div className="workspace-meta__label">Subsidiary</div>
                <div>{document.subsidiary}</div>
              </div>
              <div>
                <div className="workspace-meta__label">Date</div>
                <div>{new Date(document.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
              </div>
              <div>
                <div className="workspace-meta__label">Status</div>
                <Badge tone={document.status === 'Validated' ? 'success' : document.status === 'Flagged' ? 'danger' : 'warning'}>
                  {document.status}
                </Badge>
              </div>
            </div>
          </Card>

          <Card className="workspace-card">
            <div className="section-header">
              <h2>Extracted Fields</h2>
            </div>
            <div className="field-groups">
              {fields.map(([key, field]) => (
                <button
                  key={key}
                  type="button"
                  className="field-item"
                  onClick={() => setSelectedField(key === 'production' ? 'productionProof' : key === 'reserve' ? 'reserveProof' : 'partialProof')}
                >
                  <div className="field-item__header">
                    <span>{field.label}</span>
                    <Badge tone={toneMap[field.evidentialTone] || 'neutral'}>{field.evidentialTone}</Badge>
                  </div>
                  <div className="field-item__value">{field.value}</div>
                  <div className="field-item__meta">
                    Page {field.page} · {field.section} · {field.table} · {field.cell}
                  </div>
                </button>
              ))}
            </div>
          </Card>
        </div>

        <div className="workspace-side">
          <Card className="workspace-card">
            <EvidenceExplorer evidence={evidence} title={document.title} />
          </Card>
        </div>
      </div>
    </div>
  )
}
