import Badge from '../ui/Badge'

/**
 * ConflictComparisonView — handles both:
 *   - Flag items (backend: flag_type, severity, detail, metric, entity_name, normalized_value)
 *   - Conflict items (backend: value_a, unit_a, value_b, unit_b, delta_pct, period, document_a/b_filename)
 *   - Full conflict detail (fetched via GET /conflicts/{id}: fact_a_evidence, fact_b_evidence)
 */
export default function ConflictComparisonView({ item, conflictDetail = null }) {
  if (!item) {
    return (
      <div className="conflict-view" style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
        Select an item from the queue to inspect it.
      </div>
    )
  }

  const raw = item._raw ?? item

  // ── Conflict mode: item has value_a/value_b ──────────────────────────────
  const isConflict = raw.value_a != null || raw.value_b != null

  if (isConflict) {
    const deltaAbs = raw.delta_pct != null ? Math.abs(raw.delta_pct).toFixed(1) : '—'
    const docA = conflictDetail?.fact_a_evidence?.document?.original_filename ?? raw.document_a_filename ?? 'Source A'
    const docB = conflictDetail?.fact_b_evidence?.document?.original_filename ?? raw.document_b_filename ?? 'Source B'
    const pageA = conflictDetail?.fact_a_evidence?.page?.page_number
    const pageB = conflictDetail?.fact_b_evidence?.page?.page_number

    return (
      <div className="conflict-view">
        <div className="section-header">
          <div>
            <p className="eyebrow">Conflict comparison</p>
            <h2>{raw.metric ?? item.itemType ?? 'Data Conflict'}</h2>
          </div>
          <Badge tone={raw.status === 'resolved' ? 'success' : 'danger'}>
            {raw.status ?? 'open'}
          </Badge>
        </div>

        {raw.canonical_entity_name && (
          <div style={{ marginBottom: '12px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            Entity: <strong>{raw.canonical_entity_name}</strong>
            {raw.period_label && <span style={{ marginLeft: '10px' }}>· Period: {raw.period_label}</span>}
          </div>
        )}

        <div className="conflict-grid">
          <div className="source-panel source-panel--a">
            <div className="source-panel__label">Source A</div>
            <h3>{docA}</h3>
            {pageA && <div className="source-panel__meta">Page {pageA}</div>}
            <div className="source-panel__value is-delta">
              {raw.value_a != null ? raw.value_a : '—'} {raw.unit_a ?? ''}
            </div>
          </div>

          <div className="source-panel source-panel--b">
            <div className="source-panel__label">Source B</div>
            <h3>{docB}</h3>
            {pageB && <div className="source-panel__meta">Page {pageB}</div>}
            <div className="source-panel__value">
              {raw.value_b != null ? raw.value_b : '—'} {raw.unit_b ?? ''}
            </div>
          </div>
        </div>

        <div className="conflict-summary">
          <div>
            <div className="eyebrow">Delta</div>
            <strong>{raw.delta_pct != null ? `${deltaAbs}%` : '—'}</strong>
          </div>
          <div>
            <div className="eyebrow">Detected</div>
            <p>{raw.detected_at ? new Date(raw.detected_at).toLocaleDateString('en-IN') : '—'}</p>
          </div>
        </div>
      </div>
    )
  }

  // ── Flag mode: flag_type, severity, detail, metric ───────────────────────
  const severityTone = raw.severity === 'critical' ? 'danger' : raw.severity === 'warning' ? 'warning' : 'neutral'

  return (
    <div className="conflict-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">Validation flag</p>
          <h2>{raw.flag_type ?? item.itemType ?? 'Flag'}</h2>
        </div>
        <Badge tone={severityTone}>{raw.severity ?? 'Info'}</Badge>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 20px', marginBottom: '16px' }}>
        {raw.entity_name && (
          <div>
            <div className="eyebrow" style={{ fontSize: '10px' }}>Entity</div>
            <strong style={{ fontSize: '13px' }}>{raw.entity_name}</strong>
          </div>
        )}
        {raw.metric && (
          <div>
            <div className="eyebrow" style={{ fontSize: '10px' }}>Metric</div>
            <strong style={{ fontSize: '13px' }}>{raw.metric}</strong>
          </div>
        )}
        {raw.normalized_value != null && (
          <div>
            <div className="eyebrow" style={{ fontSize: '10px' }}>Current value</div>
            <strong style={{ fontSize: '13px' }}>{raw.normalized_value} {raw.normalized_unit ?? ''}</strong>
          </div>
        )}
        {raw.detected_at && (
          <div>
            <div className="eyebrow" style={{ fontSize: '10px' }}>Detected</div>
            <strong style={{ fontSize: '13px' }}>{new Date(raw.detected_at).toLocaleDateString('en-IN')}</strong>
          </div>
        )}
      </div>

      {raw.detail && (
        <div style={{
          padding: '12px 14px',
          background: 'rgba(220,38,38,0.05)',
          border: '1px solid rgba(220,38,38,0.15)',
          borderLeft: '3px solid #dc2626',
          borderRadius: '6px',
          fontSize: '13px',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
        }}>
          <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--navy-900)', fontSize: '12px' }}>Flag detail</strong>
          {typeof raw.detail === 'string' ? raw.detail : JSON.stringify(raw.detail, null, 2)}
        </div>
      )}

      {raw.status === 'open' && (
        <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
          Status: <strong style={{ color: '#d97706' }}>Open — awaiting reviewer action</strong>
        </div>
      )}
    </div>
  )
}
