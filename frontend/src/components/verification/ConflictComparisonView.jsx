import Badge from '../ui/Badge'

export default function ConflictComparisonView({ item }) {
  if (!item) {
    return null
  }

  const delta =
    item.sourceA && item.sourceB && item.sourceA.value !== item.sourceB.value
      ? item.sourceA.value.replace(/[^0-9.]/g, '') - item.sourceB.value.replace(/[^0-9.]/g, '')
      : 0

  return (
    <div className="conflict-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">Conflict comparison</p>
          <h2>{item.itemType}</h2>
        </div>
        <Badge tone={item.confidence >= 80 ? 'success' : item.confidence >= 65 ? 'warning' : 'danger'}>
          {item.confidence}% confidence
        </Badge>
      </div>

      <div className="conflict-grid">
        <div className="source-panel source-panel--a">
          <div className="source-panel__label">Source A</div>
          <h3>{item.sourceA.document}</h3>
          <div className="source-panel__meta">{item.sourceA.page} · {item.sourceA.section}</div>
          <div className="source-panel__value is-delta">{item.sourceA.value}</div>
          <div className="source-panel__ref">{item.sourceA.table} · {item.sourceA.cell}</div>
        </div>

        <div className="source-panel source-panel--b">
          <div className="source-panel__label">Source B</div>
          <h3>{item.sourceB.document}</h3>
          <div className="source-panel__meta">{item.sourceB.page} · {item.sourceB.section}</div>
          <div className="source-panel__value">{item.sourceB.value}</div>
          <div className="source-panel__ref">{item.sourceB.table} · {item.sourceB.cell}</div>
        </div>
      </div>

      <div className="conflict-summary">
        <div>
          <div className="eyebrow">Delta</div>
          <strong>{Math.abs(delta).toFixed(1)} {delta >= 0 ? 'higher' : 'lower'}</strong>
        </div>
        <div>
          <div className="eyebrow">Flag reason</div>
          <p>{item.flagReason}</p>
        </div>
      </div>
    </div>
  )
}
