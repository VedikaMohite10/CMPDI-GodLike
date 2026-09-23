/**
 * ExplainableAIPanel — renders a full ExplainableAIResponse from POST /query
 * or GET /parliamentary/{id}.
 *
 * Props:
 *   answer   {object}  — the raw backend ExplainableAIResponse / parliamentary record
 *   compact  {bool}    — smaller variant for parliamentary draft panel
 *
 * Rendered fields:
 *   answer / draft_answer
 *   reasoning_type          — badge (Deterministic / Hybrid / LLM-Grounded / Insufficient Evidence)
 *   confidence              — 0-100 progress bar
 *   evidence[]              — document + page + excerpt citations
 *   conflicts_surfaced[]    — ⚠ conflict callout for each
 *   calculation             — formula/derivation string
 *   model_used_intent / model_used_synthesis — attribution footer
 */
import Badge from '../ui/Badge'

const REASONING_TONE = {
  Deterministic:          'success',
  'Hybrid (Analytics + Semantic)': 'info',
  'LLM-Grounded':         'warning',
  'Insufficient Evidence':'danger',
}

function ConfidenceBar({ value }) {
  const pct = Math.min(100, Math.max(0, value ?? 0))
  const color =
    pct >= 80 ? '#16a34a' :
    pct >= 60 ? '#ca8a04' :
                '#dc2626'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <div style={{
        flex: 1, height: '6px', borderRadius: '3px',
        background: 'var(--border)', overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: color, borderRadius: '3px',
          transition: 'width 0.4s ease',
        }} />
      </div>
      <span style={{ fontSize: '12px', fontWeight: 700, color, flexShrink: 0 }}>
        {pct}%
      </span>
    </div>
  )
}

function EvidenceItem({ item, index }) {
  return (
    <div style={{
      padding: '10px 12px',
      background: 'var(--surface-strong, #f8f9fa)',
      border: '1px solid var(--border)',
      borderLeft: '3px solid #0e7490',
      borderRadius: '6px',
      fontSize: '12px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <strong style={{ color: 'var(--navy-900)', fontSize: '11px', fontWeight: 700 }}>
          [{index + 1}] {item.document_filename || item.document_id || 'Source document'}
        </strong>
        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
          p.{item.page_number ?? '—'} · {item.block_type ?? 'text'}
        </span>
      </div>
      {item.text_excerpt && (
        <p style={{
          margin: 0, color: 'var(--text-secondary)', lineHeight: 1.5,
          fontStyle: 'italic', maxHeight: '72px', overflow: 'hidden',
        }}>
          "{item.text_excerpt.slice(0, 240)}{item.text_excerpt.length > 240 ? '…' : ''}"
        </p>
      )}
      {item.score != null && (
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
          Relevance score: {(item.score * 100).toFixed(1)}%
        </span>
      )}
    </div>
  )
}

function ConflictCallout({ conflict }) {
  return (
    <div style={{
      padding: '10px 12px',
      background: 'rgba(220,38,38,0.06)',
      border: '1px solid rgba(220,38,38,0.2)',
      borderLeft: '3px solid #dc2626',
      borderRadius: '6px',
      fontSize: '12px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
        <span style={{ color: '#dc2626', fontWeight: 700, fontSize: '13px' }}>⚠ Conflict detected</span>
      </div>
      <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
        {conflict.description || conflict.detail || `${conflict.metric ?? 'Metric'}: ${conflict.value_a ?? '—'} vs ${conflict.value_b ?? '—'} (${conflict.delta_pct != null ? `${conflict.delta_pct.toFixed(1)}% delta` : 'delta unknown'})`}
      </p>
      {(conflict.document_a_filename || conflict.document_b_filename) && (
        <div style={{ marginTop: '4px', color: 'var(--text-muted)', fontSize: '11px' }}>
          {conflict.document_a_filename} ↔ {conflict.document_b_filename}
        </div>
      )}
    </div>
  )
}

export default function ExplainableAIPanel({ answer, compact = false }) {
  if (!answer) return null

  // Normalise field names — backend uses snake_case, mock data may differ
  const text          = answer.answer ?? answer.draft_answer ?? answer.summary ?? ''
  const reasoningType = answer.reasoning_type
  const confidence    = answer.confidence
  const evidence      = Array.isArray(answer.evidence) ? answer.evidence : []
  const conflicts     = Array.isArray(answer.conflicts_surfaced) ? answer.conflicts_surfaced : []
  const calculation   = answer.calculation
  const modelIntent   = answer.model_used_intent
  const modelSynth    = answer.model_used_synthesis

  // Only render if this is a real backend response (has reasoning_type or evidence)
  const isReal = reasoningType != null || evidence.length > 0
  if (!isReal) return null

  const headingSize = compact ? '13px' : '15px'

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: compact ? '12px' : '16px',
      marginTop: compact ? '12px' : '20px',
      padding: compact ? '14px' : '20px',
      background: 'rgba(18,58,62,0.03)',
      border: '1px solid rgba(18,58,62,0.1)',
      borderRadius: '8px',
    }}>

      {/* ── Header row: Reasoning type + Confidence ── */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Explainable AI
          </span>
          {reasoningType && (
            <Badge tone={REASONING_TONE[reasoningType] ?? 'neutral'}>
              {reasoningType}
            </Badge>
          )}
        </div>
        {confidence != null && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '140px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, whiteSpace: 'nowrap' }}>Confidence</span>
            <ConfidenceBar value={confidence} />
          </div>
        )}
      </div>

      {/* ── Conflicts surfaced ── */}
      {conflicts.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#dc2626' }}>
            {conflicts.length} Cross-document conflict{conflicts.length > 1 ? 's' : ''} detected
          </span>
          {conflicts.map((c, i) => <ConflictCallout key={i} conflict={c} />)}
        </div>
      )}

      {/* ── Evidence citations ── */}
      {evidence.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Evidence ({evidence.length} source{evidence.length !== 1 ? 's' : ''})
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: compact ? '200px' : '320px', overflowY: 'auto' }}>
            {evidence.map((e, i) => <EvidenceItem key={i} item={e} index={i} />)}
          </div>
        </div>
      )}

      {/* ── Calculation / derivation ── */}
      {calculation && (
        <div style={{
          padding: '10px 12px',
          background: 'rgba(15,118,110,0.05)',
          border: '1px solid rgba(15,118,110,0.15)',
          borderRadius: '6px',
        }}>
          <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#0f766e', display: 'block', marginBottom: '4px' }}>
            Calculation
          </span>
          <code style={{ fontSize: '12px', color: 'var(--navy-900)', lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {calculation}
          </code>
        </div>
      )}

      {/* ── Model attribution footer ── */}
      {(modelIntent || modelSynth) && (
        <div style={{ fontSize: '10px', color: 'var(--text-muted)', borderTop: '1px solid var(--border)', paddingTop: '8px' }}>
          {modelIntent && <span>Intent model: <strong>{modelIntent}</strong></span>}
          {modelIntent && modelSynth && <span style={{ margin: '0 6px' }}>·</span>}
          {modelSynth && <span>Synthesis model: <strong>{modelSynth}</strong></span>}
          <span style={{ margin: '0 6px' }}>·</span>
          <span>Running on local Ollama — no data leaves the system</span>
        </div>
      )}
    </div>
  )
}
