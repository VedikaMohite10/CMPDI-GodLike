import React, { useMemo, useState } from 'react'
import IndiaMap from '../components/map/IndiaMap'
import LayerToggle from '../components/map/LayerToggle'
import StateDrilldownPanel from '../components/map/StateDrilldownPanel'
import '../styles/DocumentsPage.css'
import {
  assetTypeOptions,
  coalfieldOptions,
  miningAssets,
  miningMapMock,
  sortOptions,
  subsidiaryOptions,
} from '../data/miningMapMock'

const layers = [
  'Production',
  'Dispatch',
  'Exploration Activity',
  'Reserves',
  'Data Quality',
]

const palette = {
  Production: '#123a3e',
  Dispatch: '#1c1d1f',
  'Exploration Activity': '#d9531e',
  Reserves: '#0e7490',
  'Data Quality': '#15803d',
}

function SearchIcon({ style }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16" aria-hidden="true" style={style}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  )
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="14" height="14" aria-hidden="true">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}

export default function MiningMapPage() {
  const [activeLayer, setActiveLayer] = useState('Production')
  const [selectedState, setSelectedState] = useState('Odisha')
  const [selectedAsset, setSelectedAsset] = useState(miningAssets[0])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSub, setSelectedSub] = useState('All Subsidiaries')
  const [selectedCoalfield, setSelectedCoalfield] = useState('All Coalfields')
  const [selectedAssetType, setSelectedAssetType] = useState('All Asset Types')
  const [sortBy, setSortBy] = useState('name-asc')
  const [toast, setToast] = useState('')

  // State overview fallback data
  const selectedStateData = useMemo(
    () => miningMapMock[selectedState] || miningMapMock['Odisha'],
    [selectedState],
  )

  // Combined Search + Multi-Criteria Filtering
  const filteredAssets = useMemo(() => {
    let result = miningAssets.filter((asset) => {
      const matchesSearch =
        !searchQuery ||
        [asset.name, asset.subsidiary, asset.coalfield, asset.location, asset.assetType, asset.state]
          .join(' ')
          .toLowerCase()
          .includes(searchQuery.toLowerCase())

      const matchesSub = selectedSub === 'All Subsidiaries' || asset.subsidiary === selectedSub
      const matchesCoalfield = selectedCoalfield === 'All Coalfields' || asset.coalfield === selectedCoalfield
      const matchesType = selectedAssetType === 'All Asset Types' || asset.assetType === selectedAssetType

      return matchesSearch && matchesSub && matchesCoalfield && matchesType
    })

    // Sorting
    result.sort((a, b) => {
      if (sortBy === 'name-asc') return a.name.localeCompare(b.name)
      if (sortBy === 'name-desc') return b.name.localeCompare(a.name)
      if (sortBy === 'prod-desc') return (b.productionValue || 0) - (a.productionValue || 0)
      if (sortBy === 'subsidiary') return a.subsidiary.localeCompare(b.subsidiary)
      return 0
    })

    return result
  }, [searchQuery, selectedSub, selectedCoalfield, selectedAssetType, sortBy])

  const handleReset = () => {
    setSearchQuery('')
    setSelectedSub('All Subsidiaries')
    setSelectedCoalfield('All Coalfields')
    setSelectedAssetType('All Asset Types')
    setSortBy('name-asc')
  }

  const handleSelectAsset = (asset) => {
    setSelectedAsset(asset)
    if (asset.state) {
      setSelectedState(asset.state)
    }
  }

  const handleExportMap = () => {
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      ['ID,Name,Subsidiary,Coalfield,Type,State,Production,Status']
        .concat(
          filteredAssets.map(
            (a) =>
              `"${a.id}","${a.name}","${a.subsidiary}","${a.coalfield}","${a.assetType}","${a.state}","${a.annualProduction}","${a.status}"`,
          ),
        )
        .join('\n')

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `CMPDI_Mining_Assets_${new Date().toISOString().slice(0, 10)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    setToast(`Exported ${filteredAssets.length} asset record(s) to CSV.`)
    window.setTimeout(() => setToast(''), 2500)
  }

  return (
    <div className="mining-map-page">
      {toast && (
        <div className="mining-map-toast">{toast}</div>
      )}

      {/* Geospatial Intelligence Header Banner */}
      <section
        style={{
          position: 'relative',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          minHeight: '110px',
        }}
      >
        <div style={{ maxWidth: '640px', zIndex: 2 }}>
          <p
            style={{
              margin: '0 0 6px',
              color: '#d9531e',
              fontSize: '11px',
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              fontWeight: 700,
            }}
          >
            GEOSPATIAL INTELLIGENCE
          </p>
          <h1
            style={{
              margin: 0,
              fontFamily: 'Georgia, serif',
              fontSize: 'clamp(2.2rem, 3.2vw, 3.4rem)',
              lineHeight: 1.05,
              color: 'var(--navy-900)',
              fontWeight: 700,
              letterSpacing: '-0.04em',
            }}
          >
            Mining Map &amp; Assets
          </h1>
          <p
            style={{
              margin: '10px 0 0',
              color: 'var(--text-secondary)',
              fontSize: '14px',
              lineHeight: 1.5,
            }}
          >
            Interactive geospatial view of coalfields, mines, and critical infrastructure across CIL subsidiaries for better planning, monitoring, and decision-making.
          </p>
        </div>

        {/* Mountain Silhouette Background & Tagline */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '24px',
            position: 'relative',
            zIndex: 2,
          }}
        >
          {/* Mountain Silhouette SVG */}
          <div
            style={{
              position: 'absolute',
              right: '0px',
              top: '-30px',
              width: '440px',
              height: '140px',
              pointerEvents: 'none',
              opacity: 0.35,
              zIndex: 1,
            }}
          >
            <svg viewBox="0 0 440 140" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', height: '100%' }}>
              <path
                d="M 40 140 L 120 50 L 180 85 L 280 20 L 360 75 L 440 35 L 440 140 Z"
                fill="rgba(18, 58, 62, 0.08)"
                stroke="rgba(18, 58, 62, 0.12)"
                strokeWidth="1"
              />
              <path
                d="M 90 140 L 170 70 L 230 95 L 320 45 L 390 90 L 440 70 L 440 140 Z"
                fill="rgba(18, 58, 62, 0.05)"
              />
              <path d="M 280 20 L 260 140" stroke="rgba(18, 58, 62, 0.1)" strokeWidth="1" />
              <path d="M 120 50 L 140 140" stroke="rgba(18, 58, 62, 0.08)" strokeWidth="1" />
            </svg>
          </div>

          <div
            style={{
              position: 'relative',
              zIndex: 2,
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
            }}
          >
            <div style={{ textAlign: 'right', fontSize: '13px', fontFamily: 'Georgia, serif', color: 'var(--navy-900)', fontWeight: 600, lineHeight: 1.3 }}>
              From Maps to<br />Smarter Mining
            </div>
            <div style={{ width: '48px', height: '2px', background: '#d9531e' }} />
          </div>
        </div>
      </section>

      {/* Operational Control Bar */}
      <section className="doc-control-bar" style={{ gap: '12px' }}>
        <div className="doc-search-box" style={{ maxWidth: '340px' }}>
          <SearchIcon />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search mines, coalfields, subsidiaries, or locations..."
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, justifyContent: 'flex-start' }}>
          <select
            value={selectedSub}
            onChange={(e) => setSelectedSub(e.target.value)}
            className="doc-select-filter"
          >
            {subsidiaryOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>

          <select
            value={selectedCoalfield}
            onChange={(e) => setSelectedCoalfield(e.target.value)}
            className="doc-select-filter"
          >
            {coalfieldOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>

          <select
            value={selectedAssetType}
            onChange={(e) => setSelectedAssetType(e.target.value)}
            className="doc-select-filter"
          >
            {assetTypeOptions.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: 'auto' }}>
          <button
            type="button"
            className="doc-upload-button-primary"
            style={{ height: '38px', padding: '0 18px' }}
            onClick={() => {
              setToast(`Filters applied (${filteredAssets.length} asset records found)`)
              window.setTimeout(() => setToast(''), 2200)
            }}
          >
            <span>Apply Filters</span>
            <span aria-hidden="true">&rarr;</span>
          </button>

          <button
            type="button"
            className="doc-reset-btn"
            onClick={handleReset}
          >
            Reset
          </button>
        </div>
      </section>

      <section className="mining-map-workspace">
        <aside className="mining-map-panel mining-map-panel--layers">
          <div className="mining-map-panel__header-row">
            <span>Map Layers</span>
            <button type="button" className="mining-map-link-button" onClick={handleReset}>Reset</button>
          </div>

          <div className="mining-map-layer-list">
            <label className="mining-map-check"><input type="checkbox" defaultChecked /><span>Coal Mines</span></label>
            <label className="mining-map-check"><input type="checkbox" defaultChecked /><span>Coalfields</span></label>
            <label className="mining-map-check"><input type="checkbox" defaultChecked /><span>Subsidiary Boundaries</span></label>
            <label className="mining-map-check"><input type="checkbox" /><span>Railway Network</span></label>
            <label className="mining-map-check"><input type="checkbox" /><span>Major Infrastructure</span></label>
            <label className="mining-map-check"><input type="checkbox" /><span>Environment Sensitive Areas</span></label>
            <label className="mining-map-check"><input type="checkbox" /><span>Satellite Imagery</span></label>
          </div>

          <div className="mining-map-divider" />

          <div className="mining-map-panel__header-row">
            <span>Map View</span>
          </div>

          <div className="mining-map-layer-list mining-map-layer-list--radio">
            <label className="mining-map-radio"><input type="radio" name="map-view-base" defaultChecked /><span>Standard</span></label>
            <label className="mining-map-radio"><input type="radio" name="map-view-base" /><span>Satellite</span></label>
            <label className="mining-map-radio"><input type="radio" name="map-view-base" /><span>Terrain</span></label>
            <label className="mining-map-radio"><input type="radio" name="map-view-base" /><span>Hybrid</span></label>
          </div>
        </aside>

        <div className="mining-map-canvas-panel">
          <IndiaMap
            layerColor={palette[activeLayer] || '#123a3e'}
            assets={filteredAssets}
            selectedAssetId={selectedAsset?.id}
            onSelectAsset={handleSelectAsset}
            onSelectState={setSelectedState}
            selectedState={selectedState}
          />
        </div>

        <aside className="mining-map-panel mining-map-panel--details">
          <StateDrilldownPanel
            selectedAsset={selectedAsset}
            stateData={selectedStateData}
            onClose={() => setSelectedAsset(null)}
          />
        </aside>
      </section>

      <section className="map-summary-row">
        <div className="map-summary-card">
          <div className="map-summary-card__icon">✦</div>
          <div className="map-summary-card__content">
            <strong>350+</strong>
            <span>Total Mines</span>
          </div>
        </div>
        <div className="map-summary-card">
          <div className="map-summary-card__icon">◫</div>
          <div className="map-summary-card__content">
            <strong>83</strong>
            <span>Coalfields</span>
          </div>
        </div>
        <div className="map-summary-card">
          <div className="map-summary-card__icon">▣</div>
          <div className="map-summary-card__content">
            <strong>7</strong>
            <span>CIL Subsidiaries</span>
          </div>
        </div>
        <div className="map-summary-card">
          <div className="map-summary-card__icon">⤢</div>
          <div className="map-summary-card__content">
            <strong>12,500+ km</strong>
            <span>Rail Connectivity</span>
          </div>
        </div>
      </section>
    </div>
  )
}
