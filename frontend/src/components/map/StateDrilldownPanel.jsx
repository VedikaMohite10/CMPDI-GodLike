import { useNavigate } from 'react-router-dom'

export default function StateDrilldownPanel({ selectedAsset, stateData, onClose }) {
  const navigate = useNavigate()

  const asset = selectedAsset || (stateData ? {
    name: stateData.mines?.[0] || `${stateData.state} Coalfield Cluster`,
    subsidiary: stateData.subsidiaries?.[0] || 'Coal India Limited',
    state: stateData.state,
    location: `${stateData.state}, India`,
    status: 'Operating',
    annualProduction: stateData.production || '18.4 Mt',
    areaSqKm: 340,
    coalfield: stateData.mines?.[0] || 'State Region',
    assetType: 'Mining Cluster',
    summary: stateData.summary || 'Active mining region with continuous extraction and dispatch operations.',
    coalGrade: 'Thermal Grade',
  } : null)

  if (!asset) {
    return (
      <div className="map-selected-panel" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p style={{ margin: 0, fontSize: '13px', fontWeight: 600 }}>No asset selected.</p>
        <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--text-muted)' }}>Click any mine marker or asset card to inspect details.</p>
      </div>
    )
  }

  const handleAskAI = () => {
    navigate('/ai-intelligence', {
      state: {
        initialQuery: `What is the production output and operational status for ${asset.name} in ${asset.state}?`,
      },
    })
  }

  return (
    <div className="map-selected-panel">
      <div className="map-selected-panel__header">
        <div className="map-selected-panel__label">Selected Asset</div>
        {onClose && (
          <button type="button" onClick={onClose} className="map-selected-panel__close" aria-label="Close selected asset">×</button>
        )}
      </div>

      <div className="map-selected-panel__asset">
        <div className="map-selected-panel__status">
          <span className="map-selected-panel__status-dot" />
          {asset.status || 'Operating'}
        </div>
        <h3>{asset.name}</h3>
        <p>{asset.subsidiary} / {asset.coalfield || asset.state}</p>
      </div>

      <div className="map-selected-panel__stats">
        <div>
          <span>Area</span>
          <strong>{asset.areaSqKm ? `${asset.areaSqKm} sq km` : '450 sq km'}</strong>
        </div>
        <div>
          <span>Mines</span>
          <strong>{asset.mines || '15'}</strong>
        </div>
        <div>
          <span>Annual Production</span>
          <strong>{asset.annualProduction || '52.4 MT'}</strong>
        </div>
      </div>

      <div className="map-selected-panel__tabs">
        <button type="button" className="map-selected-panel__tab is-active">Overview</button>
        <button type="button" className="map-selected-panel__tab">Production</button>
        <button type="button" className="map-selected-panel__tab">Environment</button>
        <button type="button" className="map-selected-panel__tab">Documents</button>
      </div>

      <div className="map-selected-panel__content">
        <p>{asset.summary}</p>

        <ul className="map-selected-panel__meta">
          <li><span>Key Mines</span><strong>{asset.location || 'Jharia, Katras, Lodna, Bhowra'}</strong></li>
          <li><span>Primary Coal Type</span><strong>{asset.coalGrade || 'Cooking Coal'}</strong></li>
          <li><span>Status</span><strong>{asset.status || 'Operational'}</strong></li>
        </ul>
      </div>

      <button type="button" onClick={handleAskAI} className="map-selected-panel__action">
        <span>View Detailed Report</span>
        <span>→</span>
      </button>
    </div>
  )
}
