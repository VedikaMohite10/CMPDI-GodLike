import React, { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Activity, Play, AlertCircle, RefreshCw, Server, Database, Zap } from 'lucide-react'
import { getSystemHealth, runBenchmark } from '../../api/review'
import { getDashboardStats } from '../../api/analytics'
import { IndustrialCard, LoadingSkeleton, EmptyState, SystemStatusDot, MetricStrip } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'
import { API_BASE_URL } from '../../app/config'

export default function SystemHealthPage() {
  const [benchmarkResult, setBenchmarkResult] = useState<Record<string, unknown> | null>(null)

  const { data: health, isLoading: healthLoading, error: healthError, refetch: refetchHealth } = useQuery({
    queryKey: QUERY_KEYS.systemHealth,
    queryFn: getSystemHealth,
    refetchInterval: 30_000,
  })

  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: QUERY_KEYS.dashboard,
    queryFn: getDashboardStats,
    refetchInterval: 30_000,
  })

  const benchmarkMutation = useMutation({
    mutationFn: runBenchmark,
    onSuccess: (res) => setBenchmarkResult(res as Record<string, unknown>),
  })

  const systemStatus = healthError ? 'offline' : health ? 'operational' : 'degraded'
  const extraction = stats?.extraction as Record<string, unknown> | undefined

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-white/[0.06] px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <div className="section-label mb-0.5">SYSTEM ADMINISTRATION</div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              <Activity size={16} className="text-amber-500" />
              System Health
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <SystemStatusDot status={systemStatus as 'operational' | 'degraded' | 'offline'} />
            <button
              onClick={() => { refetchHealth(); refetchStats() }}
              className="text-coal-400 hover:text-white transition-colors"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">
        {/* System overview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* API health */}
          <IndustrialCard className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Server size={14} className="text-amber-500" />
              <div className="section-label">API STATUS</div>
            </div>
            {healthLoading ? (
              <LoadingSkeleton lines={2} />
            ) : health ? (
              <div>
                <SystemStatusDot status="operational" />
                <div className="mt-2 text-xs font-mono text-coal-400">
                  Version: {health.version || '—'}
                </div>
                <div className="text-xs font-mono text-coal-400 mt-1 truncate">
                  Endpoint: {API_BASE_URL}
                </div>
              </div>
            ) : (
              <div className="text-status-offline text-xs">API Unreachable</div>
            )}
          </IndustrialCard>

          {/* Database */}
          <IndustrialCard className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Database size={14} className="text-amber-500" />
              <div className="section-label">DATABASE</div>
            </div>
            {statsLoading ? (
              <LoadingSkeleton lines={2} />
            ) : stats ? (
              <div>
                <SystemStatusDot status="operational" />
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <div>
                    <div className="section-label">Documents</div>
                    <div className="text-white font-mono font-bold">
                      {String((extraction?.total_documents as number | undefined) ?? '—')}
                    </div>
                  </div>
                  <div>
                    <div className="section-label">Vectors</div>
                    <div className="text-white font-mono font-bold">
                      {String((extraction?.total_vectors_indexed as number | undefined) ?? '—')}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-status-offline text-xs">DB Unreachable</div>
            )}
          </IndustrialCard>

          {/* AI Engine */}
          <IndustrialCard className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={14} className="text-amber-500" />
              <div className="section-label">AI ENGINE</div>
            </div>
            <SystemStatusDot status={stats ? 'operational' : 'degraded'} />
            <div className="mt-2 text-xs text-coal-400">
              <div>LLM: Inference ready</div>
              <div>Vector: Embedding indexed</div>
              <div>Forecast: MA/SES/ARIMA ready</div>
            </div>
          </IndustrialCard>
        </div>

        {/* Full stats */}
        {stats && (
          <IndustrialCard className="p-4">
            <div className="section-label mb-3">PLATFORM METRICS</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {extraction && Object.entries(extraction)
                .filter(([_, v]) => typeof v === 'number')
                .map(([key, val]) => (
                  <div key={key}>
                    <div className="section-label">{key.replace(/_/g, ' ')}</div>
                    <div className="text-white font-mono font-bold text-xl">
                      {Number(val).toLocaleString()}
                    </div>
                  </div>
                ))
              }
            </div>
          </IndustrialCard>
        )}

        {/* Benchmark */}
        <IndustrialCard className="p-4">
          <div className="section-label mb-2 flex items-center gap-2">
            <Play size={12} />
            BENCHMARK HARNESS
          </div>
          <p className="text-coal-400 text-xs mb-3 leading-relaxed">
            Run the accuracy benchmark against ground truth data. Validates AI extraction quality.
            <span className="text-amber-500 ml-1">Admin only. Do not run in production without cause.</span>
          </p>
          <button
            onClick={() => benchmarkMutation.mutate()}
            disabled={benchmarkMutation.isPending}
            className="btn-secondary text-xs"
          >
            <Play size={12} />
            {benchmarkMutation.isPending ? 'Running benchmark...' : 'Run Benchmark'}
          </button>

          {benchmarkMutation.isPending && (
            <div className="mt-3 text-xs text-amber-500 font-mono animate-pulse">
              Benchmark running... This may take several minutes.
            </div>
          )}

          {benchmarkResult && (
            <div className="mt-4 bg-coal-950 border border-white/[0.06] rounded-sm p-4">
              <div className="section-label mb-2">BENCHMARK RESULTS</div>
              <pre className="text-xs text-coal-200 font-mono overflow-auto max-h-64">
                {JSON.stringify(benchmarkResult, null, 2)}
              </pre>
            </div>
          )}
        </IndustrialCard>
      </div>
    </div>
  )
}
