/**
 * Review / Verification API — Phase 4.
 * Covers validation flags, conflicts, and audit log.
 */
import { apiFetch } from './client'

// ---------------------------------------------------------------------------
// Validation Flags
// ---------------------------------------------------------------------------

export function listFlags(token, { flagType, severity, status, documentId, page = 1, pageSize = 20 } = {}) {
  const p = new URLSearchParams({ page, page_size: pageSize })
  if (flagType)   p.set('flag_type', flagType)
  if (severity)   p.set('severity', severity)
  if (status)     p.set('status', status)
  if (documentId) p.set('document_id', documentId)
  return apiFetch(`/review/flags?${p}`, { token })
}

/** Accept a flag (reviewer+ only). */
export function acceptFlag(token, flagId, reviewer, note = '') {
  return apiFetch(`/review/flags/${flagId}/accept`, {
    method: 'POST',
    body: JSON.stringify({ reviewer, note }),
    token,
  })
}

/** Correct the underlying normalized value (reviewer+ only). */
export function correctFlag(token, flagId, { reviewer, correctedValue, correctedUnit, note = '' }) {
  return apiFetch(`/review/flags/${flagId}/correct`, {
    method: 'POST',
    body: JSON.stringify({ reviewer, corrected_value: correctedValue, corrected_unit: correctedUnit, note }),
    token,
  })
}

/** Reject a flag (reviewer+ only). */
export function rejectFlag(token, flagId, reviewer, note = '') {
  return apiFetch(`/review/flags/${flagId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reviewer, note }),
    token,
  })
}

// ---------------------------------------------------------------------------
// Conflicts
// ---------------------------------------------------------------------------

export function listConflicts(token, { entityId, metric, status, page = 1, pageSize = 20 } = {}) {
  const p = new URLSearchParams({ page, page_size: pageSize })
  if (entityId) p.set('entity_id', entityId)
  if (metric)   p.set('metric', metric)
  if (status)   p.set('status', status)
  return apiFetch(`/review/conflicts?${p}`, { token })
}

/** Resolve a conflict (reviewer+ only). */
export function resolveConflict(token, conflictId, { resolution, canonicalValue, canonicalUnit, reviewer, note = '' }) {
  return apiFetch(`/review/conflicts/${conflictId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({
      resolution,
      canonical_value: canonicalValue,
      canonical_unit:  canonicalUnit,
      reviewer,
      note,
    }),
    token,
  })
}

// ---------------------------------------------------------------------------
// Conflict detail (full dual-evidence chain)
// ---------------------------------------------------------------------------

/**
 * Fetch full detail for a single conflict including both fact evidence chains.
 * Returns { conflict, fact_a_evidence, fact_b_evidence }
 */
export function getConflictById(token, conflictId) {
  return apiFetch(`/conflicts/${conflictId}`, { token })
}

// ---------------------------------------------------------------------------
// Fact evidence lineage
// ---------------------------------------------------------------------------

/**
 * Fetch the full evidence lineage for a normalized fact.
 * Returns { fact, extracted, source, page, document, flags, entity }
 */
export function getFactEvidence(token, factId) {
  return apiFetch(`/facts/${factId}/evidence`, { token })
}

// ---------------------------------------------------------------------------
// Audit Log
// ---------------------------------------------------------------------------

export function listAuditLog(token, { actionType, reviewer, targetId, page = 1, pageSize = 20 } = {}) {
  const p = new URLSearchParams({ page, page_size: pageSize })
  if (actionType) p.set('action_type', actionType)
  if (reviewer)   p.set('reviewer', reviewer)
  if (targetId)   p.set('target_id', targetId)
  return apiFetch(`/review/audit-log?${p}`, { token })
}
