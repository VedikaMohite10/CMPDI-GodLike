import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Map, Layers, AlertCircle } from 'lucide-react'
import { getMapLayer, getMapRegionDetail } from '../../api/queries'
import { IndustrialCard, LoadingSkeleton, EmptyState, StatusBadge } from '../../components/ui/DesignSystem'

// Real approximate SVG positions for Indian states (% of a 500x600 canvas)
const STATE_POSITIONS: Record<string, { x: number; y: number }> = {
  AS: { x: 82, y: 28 },  // Assam
  CG: { x: 55, y: 52 },  // Chhattisgarh
  JH: { x: 62, y: 45 },  // Jharkhand
  MP: { x: 48, y: 46 },  // Madhya Pradesh
  MH: { x: 38, y: 58 },  // Maharashtra
  OD: { x: 63, y: 53 },  // Odisha
  RJ: { x: 32, y: 36 },  // Rajasthan
  UP: { x: 52, y: 35 },  // Uttar Pradesh
  WB: { x: 70, y: 44 },  // West Bengal
  TS: { x: 50, y: 63 },  // Telangana
  AP: { x: 52, y: 68 },  // Andhra Pradesh
  KA: { x: 44, y: 72 },  // Karnataka
  KL: { x: 42, y: 81 },  // Kerala
  TN: { x: 50, y: 80 },  // Tamil Nadu
  GJ: { x: 24, y: 50 },  // Gujarat
  HR: { x: 40, y: 28 },  // Haryana
  PB: { x: 34, y: 22 },  // Punjab
  UK: { x: 46, y: 26 },  // Uttarakhand
  HP: { x: 40, y: 20 },  // Himachal Pradesh
  MG: { x: 80, y: 35 },  // Meghalaya
}

const LAYERS = [
  { value: 'production',       label: 'Production' },
  { value: 'dispatch',         label: 'Dispatch' },
  { value: 'resources',        label: 'Resources' },
  { value: 'reserves',         label: 'Reserves' },
  { value: 'report_volume',    label: 'Report Volume' },
  { value: 'data_quality',     label: 'Data Quality' },
  { value: 'conflict_density', label: 'Conflict Density' },
]

function qualityColor(bucket: unknown) {
  if (bucket === 'green') return 'text-status-operational'
  if (bucket === 'yellow') return 'text-amber-400'
  return 'text-status-offline'
}

function valueColor(val: unknown) {
  if (val == null) return '#4A5F58'
  return '#F2A900'
}

export default function MapPage() {
  const [selectedLayer, setSelectedLayer] = useState('production')
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)

  const { data: layerData, isLoading, error } = useQuery({
    queryKey: ['map-layer', selectedLayer],
    queryFn: () => getMapLayer(selectedLayer),
  })

  const { data: regionDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['map-region', selectedRegion],
    queryFn: () => getMapRegionDetail(selectedRegion!),
    enabled: !!selectedRegion,
  })

  const regions = (layerData?.regions as unknown as Record<string, unknown>[]) || []

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="section-label mb-0.5">GEOGRAPHIC INTELLIGENCE</div>
        <h1 className="text-base font-bold text-white flex items-center gap-2">
          <Map size={16} className="text-amber-500" />
          Mine Intelligence Map
        </h1>
      </div>

      <div className="flex-1 overflow-hidden flex">
        {/* LEFT PANEL — layers + region list */}
        <div className="w-64 border-r border-white/[0.06] flex flex-col overflow-hidden">
          {/* Layer selector */}
          <div className="p-4 border-b border-white/[0.06] shrink-0">
            <div className="section-label mb-2">MAP LAYERS</div>
            <div className="space-y-0.5">
              {LAYERS.map(l => (
                <button key={l.value} onClick={() => { setSelectedLayer(l.value); setSelectedRegion(null) }}
                  className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs transition-colors text-left ${
                    selectedLayer === l.value
                      ? 'bg-amber-500/10 text-amber-500'
                      : 'text-coal-300 hover:text-white hover:bg-coal-800'
                  }`}>
                  <Layers size={11} /> {l.label}
                </button>
              ))}
            </div>
          </div>

          {/* Region list */}
          <div className="flex-1 overflow-auto">
            <div className="px-4 py-2 border-b border-white/[0.04] shrink-0">
              <div className="section-label text-[10px]">REGIONS · {regions.length}</div>
            </div>
            {isLoading ? (
              <div className="p-4"><LoadingSkeleton lines={8} /></div>
            ) : error ? (
              <div className="p-4 text-xs text-red-300">Failed to load map data.</div>
            ) : regions.length === 0 ? (
              <div className="p-4 text-xs text-coal-400 text-center">No regions available.</div>
            ) : (
              regions.map(r => (
                <button key={String(r.region_id)}
                  onClick={() => setSelectedRegion(String(r.region_id))}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-coal-800 transition-colors text-left border-b border-white/[0.04] last:border-0 ${
                    selectedRegion === String(r.region_id) ? 'bg-coal-800' : ''
                  }`}
                >
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: valueColor(r.value) }} />
                  <span className="text-xs text-white flex-1 truncate">{String(r.region_name || r.region_id)}</span>
                  <span className="text-xs font-mono text-coal-400">
                    {r.value != null ? Number(r.value).toLocaleString() : '—'}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* CENTER — India SVG Map */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 relative bg-coal-950 border-b border-white/[0.04]">
            {/* Grid background */}
            <div className="absolute inset-0 bg-technical-grid opacity-10" />

            {/* India outline SVG */}
            <svg
              viewBox="0 0 500 580"
              className="absolute inset-0 w-full h-full"
              style={{ padding: '20px' }}
            >
              {/* Simplified India silhouette */}
              <path
                d="M180,50 L200,40 L240,35 L280,40 L320,55 L380,80 L420,110 L440,140 L450,170 L445,200 
                   L430,230 L400,270 L390,310 L370,350 L350,390 L330,420 L310,450 L290,470 L270,490 
                   L260,510 L250,530 L245,520 L240,500 L220,480 L200,460 L185,440 L170,420 L155,390 
                   L140,360 L125,330 L110,300 L100,270 L95,240 L90,210 L95,180 L100,150 L115,120 L140,90 L160,65 Z"
                fill="rgba(26,34,32,0.6)"
                stroke="rgba(242,169,0,0.2)"
                strokeWidth="1.5"
              />

              {/* Region dots */}
              {regions.map(r => {
                const pos = STATE_POSITIONS[String(r.region_id)]
                if (!pos) return null
                const cx = pos.x * 5   // scale to 500px width
                const cy = pos.y * 5.8 // scale to 580px height
                const isSelected = selectedRegion === String(r.region_id)
                const hasValue = r.value != null

                return (
                  <g key={String(r.region_id)}>
                    <circle
                      cx={cx} cy={cy}
                      r={isSelected ? 10 : 7}
                      fill={hasValue ? 'rgba(242,169,0,0.8)' : 'rgba(74,95,88,0.6)'}
                      stroke={isSelected ? '#F2A900' : 'rgba(255,255,255,0.2)'}
                      strokeWidth={isSelected ? 2 : 1}
                      className="cursor-pointer transition-all"
                      onClick={() => setSelectedRegion(String(r.region_id))}
                    />
                    <text
                      x={cx} y={cy + 20}
                      textAnchor="middle"
                      fill="rgba(200,213,209,0.7)"
                      fontSize="9"
                      style={{ pointerEvents: 'none', fontFamily: 'monospace' }}
                    >
                      {String(r.region_id)}
                    </text>
                    {isSelected && (
                      <circle cx={cx} cy={cy} r={14} fill="none"
                        stroke="#F2A900" strokeWidth="1" strokeDasharray="3,2" opacity={0.6} />
                    )}
                  </g>
                )
              })}
            </svg>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 bg-coal-900/80 border border-white/[0.06] rounded-sm p-3 backdrop-blur-sm">
              <div className="section-label mb-2">LEGEND</div>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-[10px] text-coal-300">Has data</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-coal-500" />
                <span className="text-[10px] text-coal-300">No data</span>
              </div>
              <div className="mt-2 text-[10px] text-coal-500 font-mono">
                Layer: {LAYERS.find(l => l.value === selectedLayer)?.label}
              </div>
            </div>
          </div>

          {/* BOTTOM — Region detail */}
          {selectedRegion ? (
            <div className="h-48 overflow-auto p-4 shrink-0 bg-coal-900">
              <div className="section-label mb-3">
                REGION DETAIL · {selectedRegion}
              </div>
              {detailLoading ? (
                <LoadingSkeleton lines={3} />
              ) : regionDetail ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {regionDetail.data_quality_bucket != null && (
                    <div>
                      <span className="section-label block mb-0.5">Data Quality</span>
                      <span className={`text-sm font-bold font-mono uppercase ${qualityColor(regionDetail.data_quality_bucket)}`}>
                        {String(regionDetail.data_quality_bucket)}
                      </span>
                    </div>
                  )}
                  {regionDetail.avg_extraction_confidence != null && (
                    <div>
                      <span className="section-label block mb-0.5">Avg Confidence</span>
                      <span className="text-sm font-bold font-mono text-white">
                        {(Number(regionDetail.avg_extraction_confidence) * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                  {regionDetail.open_conflicts != null && (
                    <div>
                      <span className="section-label block mb-0.5">Open Conflicts</span>
                      <span className="text-sm font-bold font-mono text-amber-400">
                        {String(regionDetail.open_conflicts)}
                      </span>
                    </div>
                  )}
                  {regionDetail.entity_count != null && (
                    <div>
                      <span className="section-label block mb-0.5">Entities</span>
                      <span className="text-sm font-bold font-mono text-white">
                        {String(regionDetail.entity_count)}
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-coal-400">No detail data available for this region.</p>
              )}
            </div>
          ) : (
            <div className="h-16 flex items-center justify-center text-xs text-coal-500 font-mono shrink-0">
              Click a region dot or list item to view detail
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
