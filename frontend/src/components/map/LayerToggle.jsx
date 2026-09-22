export default function LayerToggle({ layers, activeLayer, onChange }) {
  const mapLayers = [
    { id: 'Production', label: 'Production' },
    { id: 'Dispatch', label: 'Dispatch' },
    { id: 'Exploration Activity', label: 'Exploration' },
    { id: 'Reserves', label: 'Reserves' },
    { id: 'Data Quality', label: 'Coal Quality & Data Trust' },
  ]

  return (
    <div
      className="map-layer-toolbar"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        flexWrap: 'wrap',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-sm)',
        padding: '6px 10px',
        marginBottom: '14px',
      }}
    >
      <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--text-secondary)', marginRight: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Spatial Layer:
      </span>
      {mapLayers.map((layer) => {
        const isActive = activeLayer === layer.id
        return (
          <button
            key={layer.id}
            type="button"
            className={`map-layer-pill ${isActive ? 'is-active' : ''}`}
            onClick={() => onChange(layer.id)}
            style={{
              border: isActive ? '1px solid var(--navy-800)' : '1px solid var(--border)',
              background: isActive ? 'var(--navy-800)' : 'var(--surface-strong)',
              color: isActive ? 'var(--white)' : 'var(--text-primary)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 10px',
              fontSize: 'var(--font-size-xs)',
              fontWeight: isActive ? 700 : 500,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            {layer.label}
          </button>
        )
      })}
    </div>
  )
}
