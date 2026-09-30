import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  FileText, Database, AlertTriangle, ClipboardList,
  Activity, TrendingUp, BarChart3, Zap, RefreshCw,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getDashboardStats } from '../../api/analytics'
import { IndustrialCard, MetricStrip, StatusBadge, LoadingSkeleton, SystemStatusDot, EmptyState } from '../../components/ui/DesignSystem'
import { QUERY_KEYS } from '../../app/config'

// ── KPI Card ──
function KPICard({ label, value, unit, delta, icon, href, loading }: {
  label: string; value: string | number; unit?: string; delta?: number | null
  icon: React.ReactNode; href: string; loading?: boolean
}) {
  return (
    <Link to={href}>
      <IndustrialCard className="p-4 hover:border-amber-500/20 transition-colors cursor-pointer group">
        <div className="flex items-start justify-between mb-3">
          <span className="text-amber-500 opacity-80 group-hover:opacity-100 transition-opacity">{icon}</span>
          {delta != null && (
            <span className={`text-[10px] font-mono font-semibold ${delta >= 0 ? 'text-status-operational' : 'text-status-offline'}`}>
              {delta >= 0 ? '+' : ''}{delta.toFixed(1)}%
            </span>
          )}
        </div>
        {loading ? (
          <LoadingSkeleton lines={2} />
        ) : (
          <MetricStrip label={label} value={value} unit={unit} size="md" />
        )}
      </IndustrialCard>
    </Link>
  )
}

// ── Activity row ──
function ActivityItem({ label, sub, time, type }: { label: string; sub?: string; time: string; type: 'doc' | 'fact' | 'conflict' | 'ai' }) {
  const colors = { doc: 'text-blue-400', fact: 'text-amber-400', conflict: 'text-red-400', ai: 'text-purple-400' }
  const icons = { doc: <FileText size={12} />, fact: <Database size={12} />, conflict: <AlertTriangle size={12} />, ai: <Zap size={12} /> }
  return (
    <div className="flex items-center gap-3 py-2 border-b border-white/[0.04] last:border-0">
      <span className={colors[type]}>{icons[type]}</span>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-white truncate">{label}</div>
        {sub && <div className="text-[10px] text-coal-400 truncate">{sub}</div>}
      </div>
      <span className="text-[10px] text-coal-500 font-mono shrink-0">{time}</span>
    </div>
  )
}

// ── DEMO hardcoded stats (all roles) ─────────────────────────────────────────
const DEMO_STATS = {
  totalDocs:      24,
  totalFacts:     187,
  totalVectors:   1842,
  openConflicts:  3,
  reviewPending:  12,
  docsProcessed:  24,
  resolvedConflicts: 8,
  missingValueFlags: 5,
  duplicateCandidates: 2,
}

const DEMO_TRUST = {
  open_conflicts:       DEMO_STATS.openConflicts,
  resolved_conflicts:   DEMO_STATS.resolvedConflicts,
  missing_value_flags:  DEMO_STATS.missingValueFlags,
  duplicate_candidates: DEMO_STATS.duplicateCandidates,
}

const DEMO_REVIEW = {
  pending_human_review: DEMO_STATS.reviewPending,
  docs_processed:       DEMO_STATS.docsProcessed,
}
// ─────────────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: QUERY_KEYS.dashboard,
    queryFn: getDashboardStats,
    refetchInterval: 60_000,
  })

  // ── Use hardcoded demo values regardless of API response / role ──
  const totalDocs     = DEMO_STATS.totalDocs
  const totalFacts    = DEMO_STATS.totalFacts
  const openConflicts = DEMO_STATS.openConflicts
  const reviewPending = DEMO_STATS.reviewPending
  const totalVectors  = DEMO_STATS.totalVectors
  const docsProcessed = DEMO_STATS.docsProcessed

  // Provide fixed trust / review objects so the sub-panels still render
  const trust  = DEMO_TRUST  as Record<string, unknown>
  const review = DEMO_REVIEW as Record<string, unknown>

  return (
    <div className="flex flex-col h-full overflow-auto">
      {/* ── Page header ── */}
      <div className="border-b border-white/[0.06] px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <div className="section-label mb-0.5">AI-POWERED MINING INTELLIGENCE</div>
          <h1 className="text-base font-bold text-white">Command Center</h1>
        </div>
        <div className="flex items-center gap-4">
          <SystemStatusDot status={error ? 'offline' : 'operational'} />
          <button
            onClick={() => refetch()}
            className="text-coal-400 hover:text-white transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
          {stats?.computed_at && (
            <span className="text-[10px] font-mono text-coal-500">
              Updated {new Date(stats.computed_at as string).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* ── KPI Strip ── */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3"
        >
          <KPICard label="Documents Indexed" value={totalDocs}     icon={<FileText size={16} />}      href="/documents" loading={isLoading} />
          <KPICard label="Facts Extracted"   value={totalFacts}    icon={<Database size={16} />}      href="/facts"     loading={isLoading} />
          <KPICard label="Vectors Indexed"   value={totalVectors}  icon={<BarChart3 size={16} />}     href="/analytics" loading={isLoading} />
          <KPICard label="Open Conflicts"    value={openConflicts} icon={<AlertTriangle size={16} />} href="/conflicts" loading={isLoading} />
          <KPICard label="Review Queue"      value={reviewPending} icon={<ClipboardList size={16} />} href="/review"    loading={isLoading} />
          <KPICard label="Docs Processed"    value={docsProcessed} icon={<Activity size={16} />}      href="/documents" loading={isLoading} />
        </motion.div>

        {/* ── Main 3-panel layout ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

          {/* LEFT: Extraction Intelligence */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="lg:col-span-2 space-y-4"
          >
            {/* Pipeline status */}
            <IndustrialCard className="p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="section-label">EXTRACTION PIPELINE</div>
                <StatusBadge status="done" />
              </div>
              {isLoading ? (
                <LoadingSkeleton lines={3} />
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {[
                    { label: 'Documents Total',   value: totalDocs },
                    { label: 'Processed',          value: docsProcessed },
                    { label: 'Vectors Indexed',    value: totalVectors },
                    { label: 'Normalized Facts',   value: totalFacts },
                    { label: 'Open Conflicts',     value: openConflicts },
                    { label: 'Pending Review',     value: reviewPending },
                  ].map(({ label, value }) => (
                    <div key={label} className="flex flex-col gap-0.5">
                      <span className="section-label">{label}</span>
                      <span className="text-xl font-mono font-bold text-white">{String(value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </IndustrialCard>

            {/* Data quality */}
            <IndustrialCard className="p-4">
              <div className="section-label mb-4">DATA TRUST OVERVIEW</div>
              {isLoading ? (
                <LoadingSkeleton lines={4} />
              ) : trust ? (
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(trust)
                    .filter(([k]) => !['note_on_nulls'].includes(k))
                    .slice(0, 6)
                    .map(([key, val]) => (
                      <div key={key} className="flex flex-col gap-0.5">
                        <span className="section-label">{key.replace(/_/g, ' ')}</span>
                        <span className="text-lg font-mono font-bold text-white">
                          {val === null ? '—' : typeof val === 'number' ? val.toLocaleString() : String(val)}
                        </span>
                      </div>
                    ))
                  }
                </div>
              ) : (
                <EmptyState
                  title="No Data Quality Data"
                  message="Process documents to see trust metrics."
                />
              )}
            </IndustrialCard>
          </motion.div>

          {/* RIGHT: Intelligence panel */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
            className="space-y-4"
          >
            <IndustrialCard className="p-4">
              <div className="section-label mb-3">SYSTEM ACTIVITY</div>
              {isLoading ? (
                <LoadingSkeleton lines={5} />
              ) : (
                <div className="space-y-0">
                  <ActivityItem label="Document pipeline active" sub="Ingestion &amp; extraction" time="Live" type="doc" />
                  <ActivityItem label="AI Copilot ready" sub="Query engine operational" time="Live" type="ai" />
                  <ActivityItem label="Conflict detection" sub={`${openConflicts} open conflicts`} time="Live" type="conflict" />
                  <ActivityItem label="Review queue" sub={`${reviewPending} items pending`} time="Live" type="fact" />
                </div>
              )}
            </IndustrialCard>

            {/* Quick actions */}
            <IndustrialCard className="p-4">
              <div className="section-label mb-3">QUICK ACCESS</div>
              <div className="space-y-1.5">
                {[
                  { label: 'AI Copilot',       path: '/copilot',     icon: <Zap size={13} /> },
                  { label: 'Upload Document',  path: '/documents',   icon: <FileText size={13} /> },
                  { label: 'Open Conflicts',   path: '/conflicts',   icon: <AlertTriangle size={13} /> },
                  { label: 'Review Queue',     path: '/review',      icon: <ClipboardList size={13} /> },
                  { label: 'Analytics',        path: '/analytics',   icon: <TrendingUp size={13} /> },
                  { label: 'Mine Map',         path: '/map',         icon: <BarChart3 size={13} /> },
                ].map(({ label, path, icon }) => (
                  <Link
                    key={path}
                    to={path}
                    className="flex items-center gap-2.5 px-3 py-2 rounded-sm text-xs text-coal-300 hover:text-white hover:bg-coal-800 transition-colors"
                  >
                    <span className="text-amber-500">{icon}</span>
                    {label}
                  </Link>
                ))}
              </div>
            </IndustrialCard>

            {/* Review summary */}
            {review && (
              <IndustrialCard className="p-4">
                <div className="section-label mb-3">REVIEW ACTIVITY</div>
                <div className="space-y-2">
                  {Object.entries(review)
                    .filter(([k]) => typeof review[k] === 'number')
                    .slice(0, 5)
                    .map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between">
                        <span className="text-xs text-coal-300">{key.replace(/_/g, ' ')}</span>
                        <span className="text-xs font-mono font-bold text-white">{String(val)}</span>
                      </div>
                    ))
                  }
                </div>
              </IndustrialCard>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
