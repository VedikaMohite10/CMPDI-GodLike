import { useCallback, useEffect, useMemo, useState } from 'react'
import Card from '../components/ui/Card'
import ActionButtons from '../components/verification/ActionButtons'
import ConflictComparisonView from '../components/verification/ConflictComparisonView'
import VerificationQueueTable from '../components/verification/VerificationQueueTable'
import EvidenceExplorer from '../components/evidence/EvidenceExplorer'
import { EmptyState } from '../components/ui/StatePanel'
import { useAuth } from '../context/AuthContext'
import { listFlags, acceptFlag, correctFlag, rejectFlag, listAuditLog, getConflictById } from '../api/review'

const formatTimestamp = (iso) => {
  const d = iso ? new Date(iso) : new Date()
  return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/** Map backend flag record to the shape VerificationQueueTable expects */
function normaliseFlag(f) {
  return {
    id:         f.id,
    itemType:   f.flag_type ?? 'Flag',
    flagType:   f.severity ?? f.flag_type ?? 'Info',
    status:     f.status ?? 'open',
    metric:     f.metric ?? f.fact_type ?? '—',
    document:   f.document_id ?? '—',
    rawValue:   f.raw_value,
    normalizedValue: f.normalized_value,
    normalizedUnit:  f.normalized_unit,
    description: f.description ?? '',
    evidence:   null,
    _raw: f,
  }
}

/** Map backend audit-log entry to the shape the recent-actions panel expects */
function normaliseAuditEntry(entry) {
  return {
    id:        entry.id,
    itemId:    entry.target_id ?? '—',
    action:    entry.action_type ?? 'Action',
    // Backend uses `note` (not `description`) and `timestamp` (not `created_at`)
    summary:   entry.note ?? `${entry.action_type ?? 'Action'} by ${entry.reviewer ?? 'reviewer'}`,
    timestamp: formatTimestamp(entry.timestamp ?? entry.created_at),
  }
}

export default function VerificationPage({ hideHeader = false }) {
  const { token, user } = useAuth()

  const [items, setItems]       = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [filter, setFilter]     = useState('All')
  const [loading, setLoading]   = useState(true)
  const [apiError, setApiError] = useState(null)
  const [toastMessage, setToastMessage] = useState('')
  const [recentActions, setRecentActions] = useState([])
  const [actionLoading, setActionLoading] = useState(false)
  const [conflictDetail, setConflictDetail] = useState(null)

  const showToast = (msg) => { setToastMessage(msg); window.setTimeout(() => setToastMessage(''), 3000) }

  // --- Load flags ---
  const loadFlags = useCallback(async () => {
    setLoading(true)
    setApiError(null)
    try {
      const result = await listFlags(token, { pageSize: 50 })
      const normalised = (result.items ?? []).map(normaliseFlag)
      setItems(normalised)
      if (normalised.length > 0 && !selectedId) setSelectedId(normalised[0].id)
    } catch (err) {
      setApiError(err.message ?? 'Failed to load verification queue')
    } finally {
      setLoading(false)
    }
  }, [token, selectedId])

  // --- Load audit log ---
  const loadAuditLog = useCallback(async () => {
    try {
      const result = await listAuditLog(token, { pageSize: 10 })
      setRecentActions((result.items ?? []).map(normaliseAuditEntry))
    } catch {
      // non-fatal
    }
  }, [token])

  useEffect(() => { loadFlags() }, [loadFlags])
  useEffect(() => { loadAuditLog() }, [loadAuditLog])

  // Load full conflict detail (dual-evidence) when a conflict-type item is selected
  useEffect(() => {
    if (!selectedItem) { setConflictDetail(null); return }
    const raw = selectedItem._raw ?? {}
    // Conflicts are stored in /conflicts/{id}, flags in /review/flags/{id}
    // The review queue returns flags; conflicts linked to a flag live in review/conflicts
    // We try to load conflict detail when the flag has a conflict hint (value_a/value_b exist)
    const isConflictLike = raw.value_a != null || raw.value_b != null
    if (!isConflictLike || !token) return
    getConflictById(token, selectedItem.id)
      .then((detail) => setConflictDetail(detail))
      .catch(() => setConflictDetail(null))
  }, [selectedItem, token])

  const flagTypes = useMemo(
    () => ['All', ...new Set(items.map((item) => item.flagType))],
    [items],
  )

  const filteredItems = useMemo(
    () => (filter === 'All' ? items : items.filter((item) => item.flagType === filter)),
    [items, filter],
  )

  const selectedItem =
    filteredItems.find((item) => item.id === selectedId) ||
    items.find((item) => item.id === selectedId) ||
    items[0]

  const handleAction = async (action) => {
    if (!selectedItem) return
    const reviewer = user?.username ?? 'reviewer'
    setActionLoading(true)
    try {
      if (action === 'Accept') {
        await acceptFlag(token, selectedItem.id, reviewer, '')
        showToast('Flag accepted — queue updated')
      } else if (action === 'Reject') {
        await rejectFlag(token, selectedItem.id, reviewer, '')
        showToast('Flag rejected — queue updated')
      } else if (action === 'Correct') {
        // Simple prompt for corrected value; production UI would use a modal
        const correctedValue = window.prompt('Enter corrected value:', selectedItem.normalizedValue ?? '')
        if (correctedValue === null) { setActionLoading(false); return }
        await correctFlag(token, selectedItem.id, {
          reviewer,
          correctedValue: Number(correctedValue) || correctedValue,
          correctedUnit: selectedItem.normalizedUnit,
          note: 'Corrected via review console',
        })
        showToast('Value corrected — queue updated')
      }
      // Refresh both flags and audit log after action
      await Promise.all([loadFlags(), loadAuditLog()])
    } catch (err) {
      showToast(`Action failed: ${err.message ?? 'Unknown error'}`)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="verification-page">
      {!hideHeader && (
        <div className="page-header">
          <div>
            <p className="eyebrow">Verification</p>
            <h1>Review queue</h1>
          </div>
        </div>
      )}

      {toastMessage && (
        <div className="report-toast report-toast--success">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 10.4 7.7 14l8.3-9.2" />
          </svg>
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="verification-layout">
        <div className="verification-main">
          <Card className="verification-card verification-card--list">
            <div className="verification-toolbar">
              <div>
                <p className="eyebrow">Flags</p>
                <h2>Verification queue</h2>
              </div>
              <select className="documents-filter" value={filter} onChange={(event) => setFilter(event.target.value)}>
                {flagTypes.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            {apiError ? (
              <div style={{ padding: '40px 20px', textAlign: 'center' }}>
                <p style={{ color: '#dc2626', fontWeight: 600, fontSize: '14px' }}>{apiError}</p>
                <button type="button" onClick={loadFlags} style={{ marginTop: '10px', padding: '7px 14px', borderRadius: '6px', border: '1px solid currentColor', background: 'transparent', cursor: 'pointer', fontSize: '12px' }}>
                  Retry
                </button>
              </div>
            ) : loading ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px' }}>
                Loading verification queue…
              </div>
            ) : filteredItems.length === 0 ? (
              <EmptyState
                title="No verification items match the current filter"
                description="Try choosing another flag type to continue the review queue."
              />
            ) : (
              <VerificationQueueTable items={filteredItems} selectedId={selectedId} onSelect={setSelectedId} />
            )}
          </Card>

          <Card className="verification-card">
            <ConflictComparisonView item={selectedItem} conflictDetail={conflictDetail} />
          </Card>

          <Card className="verification-card">
            <EvidenceExplorer
            evidence={selectedItem?.evidence ?? (selectedItem?._raw?.normalized_value != null ? [{
              label: selectedItem._raw.metric ?? 'Value',
              value: `${selectedItem._raw.normalized_value} ${selectedItem._raw.normalized_unit ?? ''}`.trim(),
              confidence: null,
              tone: 'green',
            }] : null)}
            title={`${selectedItem?.itemType || 'Flag'} evidence`}
          />
          </Card>
        </div>

        <div className="verification-side">
          <Card className="verification-card">
            <div className="section-header">
              <div>
                <p className="eyebrow">Review</p>
                <h2>Actions</h2>
              </div>
            </div>
            <ActionButtons onAction={handleAction} disabled={actionLoading || !selectedItem} />
          </Card>

          <Card className="verification-card">
            <div className="section-header">
              <div>
                <p className="eyebrow">Audit trail</p>
                <h2>Recent actions</h2>
              </div>
            </div>

            {recentActions.length === 0 ? (
              <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                No recent actions yet.
              </div>
            ) : (
              <ul className="verification-log">
                {recentActions.map((entry) => (
                  <li key={entry.id} className="verification-log__item">
                    <div className="verification-log__topline">
                      <strong>{entry.action}</strong>
                      <span>{entry.timestamp}</span>
                    </div>
                    <p>{entry.summary}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}

