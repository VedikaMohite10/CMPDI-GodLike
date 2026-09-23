/**
 * Reports API — Phase 4.
 */
import { apiFetch } from './client'

/**
 * Generate a new report.
 * @param {{ entityIds, metrics, periodStart, periodEnd, label? }} params
 * @returns {{ report_id, status, sections[], citation_count, dq_warning_count, model_used }}
 */
export function generateReport(token, { entityIds, metrics, periodStart, periodEnd, label }) {
  return apiFetch('/reports/generate', {
    method: 'POST',
    body: JSON.stringify({
      entity_ids:   entityIds,
      metrics,
      period_start: periodStart,
      period_end:   periodEnd,
      label,
    }),
    token,
  })
}

/** List all generated reports. */
export function listReports(token, { page = 1, pageSize = 20 } = {}) {
  return apiFetch(`/reports?page=${page}&page_size=${pageSize}`, { token })
}

/** Fetch a single report's full content. */
export function getReport(token, id) {
  return apiFetch(`/reports/${id}`, { token })
}

/**
 * Download a report as a file.
 * @param {'pdf'|'docx'|'xlsx'} format
 * @returns {string} Blob URL — assign to <a href> and call .click()
 */
export async function exportReport(token, id, format = 'pdf') {
  const blob = await apiFetch(`/reports/${id}/export?format=${format}`, { blob: true, token })
  return URL.createObjectURL(blob)
}
