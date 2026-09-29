import axios from 'axios'
import type { AnalyticsTrendResponse, CompareResponse, SearchResult } from '../types'
import { apiClient } from './client'

export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ── Dashboard ──────────────────────────────────────────────────────────────
export async function getDashboardStats() {
  const { data } = await apiClient.get('/dashboard/stats')
  return data
}

// ── Analytics trend — entity_id + metric REQUIRED ─────────────────────────
export async function analyticsTrend(payload: {
  entity_id: string
  metric: string
  period_start_year?: number
  period_end_year?: number
}): Promise<AnalyticsTrendResponse> {
  const { data } = await apiClient.post('/analytics/trend', payload)
  return data
}

// ── Analytics compare ──────────────────────────────────────────────────────
export async function analyticsCompare(payload: {
  entity_ids: string[]
  metric: string
  period_start_year?: number
  period_end_year?: number
}): Promise<CompareResponse> {
  const { data } = await apiClient.post('/analytics/compare', payload)
  return data
}

// ── Semantic search ────────────────────────────────────────────────────────
export async function semanticSearch(query: string, top_k = 10): Promise<SearchResult> {
  const { data } = await apiClient.post('/search', { query, top_k })
  return data
}

// ── Topics ─────────────────────────────────────────────────────────────────
export async function listTopics(params: { page?: number; page_size?: number } = {}) {
  const { data } = await apiClient.get('/topics', { params })
  return data
}
