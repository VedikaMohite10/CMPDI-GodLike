import { apiClient } from './client'
import type { PaginatedResponse } from '../types'

// ── Review: Flags ──
export interface FlagAcceptRequest    { reviewer: string; note?: string }
export interface FlagCorrectRequest   { corrected_value: number; corrected_unit?: string; reviewer: string; note?: string }
export interface FlagRejectRequest    { reviewer: string; note: string }
export interface ConflictResolveRequest {
  resolution:      string
  canonical_value?: number
  canonical_unit?:  string
  reviewer:         string
  note?:            string
}

export interface ReviewActionResponse {
  status:         string
  action_type:    string
  target_id:      string
  audit_log_id:   string
  message:        string
}

export async function acceptFlag(flagId: string, req: FlagAcceptRequest): Promise<ReviewActionResponse> {
  const { data } = await apiClient.post(`/review/flags/${flagId}/accept`, req)
  return data
}

export async function correctFlag(flagId: string, req: FlagCorrectRequest): Promise<ReviewActionResponse> {
  const { data } = await apiClient.post(`/review/flags/${flagId}/correct`, req)
  return data
}

export async function rejectFlag(flagId: string, req: FlagRejectRequest): Promise<ReviewActionResponse> {
  const { data } = await apiClient.post(`/review/flags/${flagId}/reject`, req)
  return data
}

// ── Review: Conflicts ──
export async function resolveConflict(conflictId: string, req: ConflictResolveRequest): Promise<ReviewActionResponse> {
  const { data } = await apiClient.post(`/review/conflicts/${conflictId}/resolve`, req)
  return data
}

// ── Audit Log ──
export interface AuditLogEntry {
  id:           string
  timestamp:    string
  reviewer:     string
  action_type:  string
  target_table: string
  target_id:    string
  before_value: Record<string, unknown> | null
  after_value:  Record<string, unknown> | null
  note:         string | null
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
  page:  number
  page_size: number
}

export async function getAuditLog(params?: {
  action_type?: string
  reviewer?: string
  target_id?: string
  page?: number
  page_size?: number
}): Promise<AuditLogListResponse> {
  const { data } = await apiClient.get('/review/audit-log', { params })
  return data
}

// ── System Health ──
export interface SystemHealthStatus {
  status:  string
  version: string
}

export async function getSystemHealth(): Promise<SystemHealthStatus> {
  const { data } = await apiClient.get('/health')
  return data
}

// ── Benchmark ──
export async function runBenchmark() {
  const { data } = await apiClient.post('/benchmark/run')
  return data
}
