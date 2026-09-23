/**
 * Dashboard, Topics, and Parliamentary API modules — Phases 4 & 5.
 */
import { apiFetch } from './client'

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export const getDashboardStats   = (token) => apiFetch('/dashboard/stats', { token })
export const getTrustStats       = (token) => apiFetch('/dashboard/stats/trust', { token })
export const getReviewStats      = (token) => apiFetch('/dashboard/stats/review', { token })
export const getExtractionStats  = (token) => apiFetch('/dashboard/stats/extraction', { token })

// ---------------------------------------------------------------------------
// Topics
// ---------------------------------------------------------------------------

export const listTopics          = (token) => apiFetch('/topics', { token })
export const getTopicTrends      = (token) => apiFetch('/topics/trends', { token })
export const getTopicById        = (token, id) => apiFetch(`/topics/${id}`, { token })

// ---------------------------------------------------------------------------
// Parliamentary Queries
// ---------------------------------------------------------------------------

/** Submit a new parliamentary question. Returns { query_id, status:"pending_review", ... } */
export function submitParliamentaryQuery(token, question) {
  return apiFetch('/parliamentary/query', {
    method: 'POST',
    body: JSON.stringify({ question }),
    token,
  })
}

export function listParliamentaryQueries(token, { status, page = 1, pageSize = 20 } = {}) {
  const p = new URLSearchParams({ page, page_size: pageSize })
  if (status) p.set('status', status)
  return apiFetch(`/parliamentary?${p}`, { token })
}

export function getParliamentaryQuery(token, id) {
  return apiFetch(`/parliamentary/${id}`, { token })
}

/** Approve a parliamentary draft (reviewer+ only). Returns { final_answer, ... } */
export function approveParliamentaryQuery(token, id, note = '') {
  return apiFetch(`/parliamentary/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ note }),
    token,
  })
}

/** Reject a parliamentary draft (reviewer+ only). */
export function rejectParliamentaryQuery(token, id, note) {
  return apiFetch(`/parliamentary/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ note }),
    token,
  })
}

// ---------------------------------------------------------------------------
// Mining Map
// ---------------------------------------------------------------------------

/**
 * @param {'production'|'dispatch'|'resources'|'reserves'|'exploration'|'report_volume'|'data_quality'|'conflict_density'} layer
 */
export function getMapLayer(token, layer) {
  return apiFetch(`/map/layers?layer=${encodeURIComponent(layer)}`, { token })
}

export function getRegionDetail(token, regionId) {
  return apiFetch(`/map/regions/${regionId}`, { token })
}

// ---------------------------------------------------------------------------
// Forecasting
// ---------------------------------------------------------------------------

/**
 * Run a forecast.
 * @param {{ entityId, metric, horizonYears }} params
 */
export function runForecast(token, { entityId, metric, horizonYears }) {
  return apiFetch('/forecast', {
    method: 'POST',
    body: JSON.stringify({ entity_id: entityId, metric, horizon_years: horizonYears }),
    token,
  })
}

export function listForecasts(token, { entityId, metric, limit = 20 } = {}) {
  const p = new URLSearchParams({ limit })
  if (entityId) p.set('entity_id', entityId)
  if (metric)   p.set('metric', metric)
  return apiFetch(`/forecast?${p}`, { token })
}

export function getForecast(token, id) {
  return apiFetch(`/forecast/${id}`, { token })
}

// ---------------------------------------------------------------------------
// Entities (for entity selectors across the app)
// ---------------------------------------------------------------------------

export function listEntities(token, { entityType, page = 1, pageSize = 50 } = {}) {
  const p = new URLSearchParams({ page, page_size: pageSize })
  if (entityType) p.set('entity_type', entityType)
  return apiFetch(`/entities?${p}`, { token })
}

export function getEntity(token, id) {
  return apiFetch(`/entities/${id}`, { token })
}

// ---------------------------------------------------------------------------
// Benchmarking
// ---------------------------------------------------------------------------

export const getBenchmarkResults = (token, limit = 10) =>
  apiFetch(`/benchmark/results?limit=${limit}`, { token })

export const runBenchmark = (token, note = '') =>
  apiFetch('/benchmark/run', { method: 'POST', body: JSON.stringify({ note }), token })
