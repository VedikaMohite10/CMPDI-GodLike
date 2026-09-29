import React from 'react'
import { clsx } from 'clsx'

// ── IndustrialCard ──
interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  className?: string
}
export function IndustrialCard({ children, className, ...props }: CardProps) {
  return (
    <div className={clsx('industrial-card', className)} {...props}>
      {children}
    </div>
  )
}

// ── MetricStrip ──
interface MetricStripProps {
  label:    string
  value:    string | number
  unit?:    string
  delta?:   number | null
  size?:    'sm' | 'md' | 'lg'
  className?: string
}
export function MetricStrip({ label, value, unit, delta, size = 'md', className }: MetricStripProps) {
  const sizes = { sm: 'text-lg', md: 'text-2xl', lg: 'text-4xl' }
  return (
    <div className={clsx('flex flex-col gap-0.5', className)}>
      <span className="section-label">{label}</span>
      <div className="flex items-baseline gap-1.5">
        <span className={clsx('metric-value', sizes[size])}>{value}</span>
        {unit && <span className="text-coal-300 text-xs font-mono">{unit}</span>}
        {delta != null && (
          <span className={delta >= 0 ? 'metric-delta-positive' : 'metric-delta-negative'}>
            {delta >= 0 ? '+' : ''}{delta.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  )
}

// ── StatusBadge ──
interface StatusBadgeProps {
  status: string
  size?:  'sm' | 'md'
}
const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  done:          { label: 'Processed',   color: 'text-status-operational bg-status-operational/10', dot: 'bg-status-operational' },
  processing:    { label: 'Processing',  color: 'text-amber-500 bg-amber-500/10',                  dot: 'bg-amber-500 animate-pulse' },
  pending:       { label: 'Pending',     color: 'text-coal-300 bg-coal-800',                       dot: 'bg-coal-400' },
  failed:        { label: 'Failed',      color: 'text-status-offline bg-status-offline/10',        dot: 'bg-status-offline' },
  open:          { label: 'Open',        color: 'text-status-warning bg-status-warning/10',        dot: 'bg-status-warning' },
  resolved:      { label: 'Resolved',   color: 'text-status-operational bg-status-operational/10', dot: 'bg-status-operational' },
  pending_review:{ label: 'Under Review',color: 'text-amber-400 bg-amber-400/10',                  dot: 'bg-amber-400 animate-pulse' },
  approved:      { label: 'Approved',    color: 'text-status-operational bg-status-operational/10', dot: 'bg-status-operational' },
  rejected:      { label: 'Rejected',    color: 'text-status-offline bg-status-offline/10',        dot: 'bg-status-offline' },
  accepted:      { label: 'Accepted',    color: 'text-status-operational bg-status-operational/10', dot: 'bg-status-operational' },
  corrected:     { label: 'Corrected',   color: 'text-earth-cyan bg-earth-cyan/10',                dot: 'bg-earth-cyan' },
}
export function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status] || { label: status, color: 'text-coal-300 bg-coal-800', dot: 'bg-coal-400' }
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 rounded-sm font-semibold uppercase tracking-wider',
      size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1',
      cfg.color
    )}>
      <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', cfg.dot)} />
      {cfg.label}
    </span>
  )
}

// ── LoadingSkeleton ──
interface SkeletonProps { className?: string; lines?: number }
export function LoadingSkeleton({ className, lines = 1 }: SkeletonProps) {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={clsx('skeleton h-4 rounded-sm', i === lines - 1 ? 'w-2/3' : 'w-full')} />
      ))}
    </div>
  )
}

// ── EmptyState ──
interface EmptyStateProps {
  title:     string
  message:   string
  icon?:     React.ReactNode
  action?:   React.ReactNode
}
export function EmptyState({ title, message, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center px-8">
      {icon && <div className="mb-4 text-coal-600">{icon}</div>}
      <div className="text-white font-semibold mb-1">{title}</div>
      <div className="text-coal-400 text-sm max-w-sm">{message}</div>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// ── ConfidenceIndicator ──
interface ConfidenceProps { value: number | null; showBar?: boolean }
export function ConfidenceIndicator({ value, showBar = false }: ConfidenceProps) {
  if (value === null) return <span className="text-coal-400 font-mono text-xs">—</span>
  const pct = Math.round(value * 100)
  const cls = pct >= 80 ? 'confidence-high' : pct >= 60 ? 'confidence-medium' : 'confidence-low'
  return (
    <div className="flex items-center gap-2">
      <span className={clsx('font-mono text-xs font-semibold', cls)}>{pct}%</span>
      {showBar && (
        <div className="w-16 h-1 bg-coal-800 rounded-full overflow-hidden">
          <div
            className={clsx('h-full rounded-full', pct >= 80 ? 'bg-status-operational' : pct >= 60 ? 'bg-amber-500' : 'bg-status-offline')}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  )
}

// ── PipelineProgress ──
interface PipelineStep { label: string; status: 'done' | 'running' | 'pending' | 'error' }
export function PipelineProgress({ steps }: { steps: PipelineStep[] }) {
  const icons = { done: '✓', running: '●', pending: '○', error: '✕' }
  return (
    <div className="flex items-center gap-0">
      {steps.map((step, i) => (
        <React.Fragment key={step.label}>
          <div className={clsx('pipeline-stage text-[10px]', step.status)}>
            <span>{icons[step.status]}</span>
            <span>{step.label}</span>
          </div>
          {i < steps.length - 1 && <span className="text-coal-600 mx-1.5">→</span>}
        </React.Fragment>
      ))}
    </div>
  )
}

// ── SystemStatus indicator ──
export function SystemStatusDot({ status }: { status: 'operational' | 'degraded' | 'offline' }) {
  const colors = {
    operational: 'bg-status-operational',
    degraded:    'bg-status-degraded',
    offline:     'bg-status-offline',
  }
  const labels = { operational: 'OPERATIONAL', degraded: 'DEGRADED', offline: 'OFFLINE' }
  return (
    <div className="flex items-center gap-1.5">
      <div className={clsx('w-1.5 h-1.5 rounded-full', colors[status], status === 'operational' ? 'animate-pulse-slow' : 'animate-pulse')} />
      <span className={clsx('text-[10px] font-mono font-semibold uppercase tracking-wider',
        status === 'operational' ? 'text-status-operational' :
        status === 'degraded' ? 'text-status-degraded' : 'text-status-offline'
      )}>{labels[status]}</span>
    </div>
  )
}

// ── DocumentChip ──
interface DocumentChipProps { filename: string; docId?: string; onClick?: () => void }
export function DocumentChip({ filename, docId, onClick }: DocumentChipProps) {
  const ext = filename.split('.').pop()?.toUpperCase() || 'DOC'
  const extColors: Record<string, string> = {
    PDF: 'text-red-400 bg-red-400/10', DOCX: 'text-blue-400 bg-blue-400/10',
    XLSX: 'text-green-400 bg-green-400/10', XLS: 'text-green-400 bg-green-400/10',
  }
  const extColor = extColors[ext] || 'text-coal-300 bg-coal-800'
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 bg-coal-850 border border-white/[0.06] rounded-sm px-2 py-1 text-xs hover:border-amber-500/30 transition-colors"
    >
      <span className={clsx('text-[10px] font-bold px-1 py-0.5 rounded-sm', extColor)}>{ext}</span>
      <span className="text-coal-100 truncate max-w-[160px]">{filename}</span>
    </button>
  )
}

// ── EvidencePanel ──
interface EvidenceItem {
  document_filename: string | null
  document_id:       string | null
  page_number:       number | null
  excerpt:           string
  confidence?:       number | null
}
interface EvidencePanelProps {
  items:      EvidenceItem[]
  onDocClick?: (docId: string) => void
}
export function EvidencePanel({ items, onDocClick }: EvidencePanelProps) {
  if (!items.length) return (
    <div className="text-coal-400 text-xs text-center py-4">No evidence available.</div>
  )
  return (
    <div className="space-y-3">
      <div className="section-label flex items-center gap-2">
        <span>EVIDENCE</span>
        <div className="flex-1 h-px bg-amber-500/20" />
      </div>
      {items.map((ev, i) => (
        <div key={i} className="evidence-panel">
          <div className="flex items-start justify-between gap-2 mb-2">
            {ev.document_filename && (
              <button
                onClick={() => ev.document_id && onDocClick?.(ev.document_id)}
                className="text-xs text-amber-500 hover:text-amber-400 font-mono truncate"
              >
                {ev.document_filename}
                {ev.page_number ? ` · p.${ev.page_number}` : ''}
              </button>
            )}
            {ev.confidence != null && (
              <ConfidenceIndicator value={ev.confidence} />
            )}
          </div>
          <p className="text-xs text-coal-200 leading-relaxed italic">"{ev.excerpt}"</p>
        </div>
      ))}
    </div>
  )
}
