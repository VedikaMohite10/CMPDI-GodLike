import { apiClient } from './client'
import type { PaginatedResponse } from '../types'

export interface CanonicalEntity {
  id:              string
  canonical_name:  string
  entity_type:     string
  aliases:         string[]
  created_at:      string
}

export interface ExtractedFact {
  id:           string
  document_id:  string
  metric:       string
  raw_value:    string
  raw_unit:     string
  period_label: string
  confidence:   number
  page_number:  number | null
}

export interface NormalizedFact {
  id:                  string
  extracted_fact_id:   string
  canonical_entity_id: string | null
  metric:              string
  normalized_value:    number
  normalized_unit:     string
  period_start:        string | null
  period_end:          string | null
  is_flagged:          boolean
  has_conflict:        boolean
}

export interface ValidationFlag {
  id:                 string
  normalized_fact_id: string
  flag_type:          string
  severity:           string
  status:             string
  detail:             string
  detected_at:        string
  metric:             string | null
  normalized_value:   number | null
  normalized_unit:    string | null
  entity_name:        string | null
  document_id:        string | null
  available_actions:  string[]
}

export interface Conflict {
  id:                    string
  canonical_entity_name: string | null
  metric:                string
  period_label:          string | null
  value_a:               number
  unit_a:                string
  value_b:               number
  unit_b:                string
  delta_pct:             number | null
  document_a_filename:   string | null
  document_b_filename:   string | null
  status:                string
  detected_at:           string
  available_actions:     string[]
  valid_resolutions:     string[]
}

export interface Duplicate {
  id:           string
  document_id_a: string
  document_id_b: string
  similarity:    number
  status:        string
  detected_at:   string
}

// ── Entities ──
export async function listEntities(params?: { page?: number; page_size?: number; q?: string }): Promise<PaginatedResponse<CanonicalEntity>> {
  const { data } = await apiClient.get('/entities', { params })
  return data
}

export async function getEntity(id: string): Promise<CanonicalEntity> {
  const { data } = await apiClient.get(`/entities/${id}`)
  return data
}

// ── Facts ──
export async function listFacts(params?: { page?: number; page_size?: number; document_id?: string; entity_id?: string; metric?: string }): Promise<PaginatedResponse<NormalizedFact>> {
  const { data } = await apiClient.get('/facts', { params })
  return data
}

export async function getFactEvidence(factId: string) {
  const { data } = await apiClient.get(`/facts/${factId}/evidence`)
  return data
}

// ── Conflicts ──
export async function listConflicts(params?: { entity_id?: string; metric?: string; status?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<Conflict>> {
  const { data } = await apiClient.get('/conflicts', { params })
  return data
}

export async function getConflictDetail(id: string) {
  const { data } = await apiClient.get(`/conflicts/${id}`)
  return data
}

// ── Flags (Data Quality) ──
export async function listFlags(params?: { flag_type?: string; severity?: string; status?: string; document_id?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<ValidationFlag>> {
  const { data } = await apiClient.get('/review/flags', { params })
  return data
}

// ── Duplicates ──
export async function listDuplicates(params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<Duplicate>> {
  const { data } = await apiClient.get('/duplicates', { params })
  return data
}
