import { apiClient } from './client'
import type {
  ExplainableAIResponse, ForecastResponse,
  ParliamentaryQueryOut, ReportOut, MapLayerResponse, MapRegionDetail
} from '../types'

// ── AI Copilot query ───────────────────────────────────────────────────────
export async function submitQuery(payload: {
  question: string
  top_k_semantic?: number
}): Promise<ExplainableAIResponse> {
  const { data } = await apiClient.post('/query', payload)
  return data
}

// ── Forecast — entity_id + metric REQUIRED ─────────────────────────────────
export async function runForecast(payload: {
  entity_id: string
  metric: string
  horizon_years?: number
}): Promise<ForecastResponse> {
  const { data } = await apiClient.post('/forecast', payload)
  return data
}

// ── Map layers ─────────────────────────────────────────────────────────────
export async function getMapLayer(layer: string): Promise<MapLayerResponse> {
  const { data } = await apiClient.get('/map/layers', { params: { layer } })
  return data
}

export async function getMapRegionDetail(regionId: string): Promise<MapRegionDetail> {
  const { data } = await apiClient.get(`/map/regions/${regionId}`)
  return data
}

// ── Parliamentary ──────────────────────────────────────────────────────────
export async function submitParliamentaryQuery(question: string): Promise<ParliamentaryQueryOut> {
  const { data } = await apiClient.post('/parliamentary/query', { question })
  return data
}

export async function listParliamentaryQueries(params: {
  status?: string
  page?: number
  page_size?: number
} = {}): Promise<{ items: ParliamentaryQueryOut[]; total: number }> {
  const { data } = await apiClient.get('/parliamentary', { params })
  return data
}

export async function getParliamentaryQuery(id: string): Promise<ParliamentaryQueryOut> {
  const { data } = await apiClient.get(`/parliamentary/${id}`)
  return data
}

export async function approveParliamentaryQuery(id: string, note?: string): Promise<ParliamentaryQueryOut> {
  const { data } = await apiClient.post(`/parliamentary/${id}/approve`, { note })
  return data
}

export async function rejectParliamentaryQuery(id: string, reason: string): Promise<ParliamentaryQueryOut> {
  const { data } = await apiClient.post(`/parliamentary/${id}/reject`, { reason })
  return data
}

// ── Reports — period_start + period_end REQUIRED ───────────────────────────
export async function generateReport(payload: {
  entity_ids?: string[]
  metrics?: string[]
  period_start: string   // ISO date e.g. "2020-01-01"
  period_end: string     // ISO date e.g. "2024-12-31"
  label?: string
}): Promise<ReportOut> {
  const { data } = await apiClient.post('/reports/generate', payload)
  return data
}

export async function listReports(params: { page?: number; page_size?: number } = {}) {
  const { data } = await apiClient.get('/reports', { params })
  return data
}

export function getReportExportUrl(reportId: string, format: 'pdf' | 'docx' | 'xlsx') {
  return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/reports/${reportId}/export?format=${format}`
}
