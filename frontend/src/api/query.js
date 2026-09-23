/**
 * Query & Analytics API — Phase 3.
 */
import { apiFetch } from './client'

/**
 * Submit a question to the AI Query Copilot.
 * Returns ExplainableAIResponse:
 *   { query_id, answer, evidence[], conflicts_surfaced[], analytics_results,
 *     calculation, confidence, reasoning_type, model_used_intent, model_used_synthesis }
 *
 * Note: This can take 5–30 seconds (LLM inference).
 */
export function submitQuery(token, question, topK = 5) {
  return apiFetch('/query', {
    method: 'POST',
    body: JSON.stringify({ question, top_k_semantic: topK }),
    token,
  })
}

/** Retrieve a previously persisted query response by ID. */
export function getQueryById(token, id) {
  return apiFetch(`/query/${id}`, { token })
}

/** Direct semantic search against Qdrant (no LLM). */
export function semanticSearch(token, query, topK = 10, filter = {}) {
  return apiFetch('/search', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK, filter }),
    token,
  })
}

// ---------------------------------------------------------------------------
// Deterministic analytics (pure SQL/Python — no LLM)
// ---------------------------------------------------------------------------

/**
 * Compare multiple entities on a metric over a date range.
 * Returns: { entities[{entity_id, data_points[], yoy_changes[], cagr}], anomalies[] }
 */
export function compareAnalytics(token, { entityIds, metric, periodStartYear, periodEndYear }) {
  return apiFetch('/analytics/compare', {
    method: 'POST',
    body: JSON.stringify({
      entity_ids: entityIds,
      metric,
      period_start_year: periodStartYear,
      period_end_year:   periodEndYear,
    }),
    token,
  })
}

/**
 * Get a time series for one entity and metric.
 * Returns: { series[{period_label, value, fact_id, has_conflict, has_flag}] }
 */
export function trendSeries(token, { entityId, metric, periodStartYear, periodEndYear }) {
  return apiFetch('/analytics/trend', {
    method: 'POST',
    body: JSON.stringify({
      entity_id:         entityId,
      metric,
      period_start_year: periodStartYear,
      period_end_year:   periodEndYear,
    }),
    token,
  })
}

/**
 * Get a Why-did-this-change explanation.
 * Returns: { why_change_detail: { from_value, to_value, pct_change, classification, cited_passages[] } }
 */
export function whyDidThisChange(token, { entityId, metric, periodYear, topK = 5 }) {
  return apiFetch('/analytics/why-did-this-change', {
    method: 'POST',
    body: JSON.stringify({
      entity_id:      entityId,
      metric,
      period_year:    periodYear,
      top_k_semantic: topK,
    }),
    token,
  })
}
