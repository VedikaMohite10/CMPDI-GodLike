// Shared TypeScript types across the application

export interface PaginatedResponse<T = unknown> {
  items:     T[]
  total:     number
  page:      number
  page_size: number
}

export type Role = 'analyst' | 'reviewer' | 'admin'

export interface AuthUser {
  id:        string
  username:  string
  role:      Role
  is_active: boolean
}

export interface ApiError {
  detail:     string
  status_code?: number
}

export type ProcessingStatus = 'pending' | 'processing' | 'done' | 'failed'
export type ConflictStatus   = 'open' | 'resolved'
export type FlagStatus       = 'open' | 'accepted' | 'corrected' | 'rejected'
export type ParliamentaryStatus = 'draft' | 'pending_review' | 'approved' | 'rejected'

export interface SearchParams {
  page?:      number
  page_size?: number
  q?:         string
}

// Navigation structure
export interface NavSection {
  label: string
  items: NavItem[]
}

export interface NavItem {
  label:      string
  path:       string
  icon:       string
  badge?:     number | string
  roles?:     Role[]
  children?:  NavItem[]
}

// ── Document types ──
export interface ExtractionSummary {
  total_text_blocks:    number
  total_tables:         number
  total_images:         number
  total_vectors_indexed: number
}

export interface DocumentSummary {
  id:                string
  filename:          string
  original_filename: string
  file_type:         string
  mime_type:         string
  file_size_bytes:   number
  processing_status: ProcessingStatus
  upload_date:       string
  report_date:       string | null
  ocr_required:      boolean
}

export interface DocumentDetail extends DocumentSummary {
  storage_path:       string
  created_at:         string
  updated_at:         string
  extraction_summary?: ExtractionSummary | null
}

export interface FactProcessingStatus {
  document_id:      string
  status:           string
  facts_extracted:  number
  facts_normalized: number
  facts_flagged:    number
  conflicts_found:  number
  started_at:       string | null
  completed_at:     string | null
  error:            string | null
}

// ── AI Copilot / Query types ──
export interface EvidenceItem {
  document_id:       string | null
  document_filename: string | null
  page_number:       number | null
  excerpt:           string | null
  score:             number | null
}

export interface ConflictSurfaced {
  entity_name: string | null
  metric:      string | null
  value_a:     number | null
  value_b:     number | null
  delta_pct:   number | null
}

export interface ExplainableAIResponse {
  answer:             string
  evidence:           EvidenceItem[]
  conflicts_surfaced: ConflictSurfaced[]
  analytics_results:  Record<string, unknown> | null
  calculation:        string | null
  confidence:         number | null
  reasoning_type:     string | null
}

// ── Forecast types ──
export interface ForecastPoint {
  year:        number
  predicted:   number
  lower_bound: number
  upper_bound: number
}

export interface ForecastResponse {
  forecast_type:              string
  entity_id:                  string
  entity_name?:               string
  metric:                     string
  horizon_years?:             number
  model_used?:                string
  escalation_reason?:         string | null
  training_period_start?:     string | null
  training_period_end?:       string | null
  training_data_points?:      number
  forecast_points?:           ForecastPoint[]
  unit?:                      string
  assumptions?:               string[]
  data_quality_summary?:      Record<string, unknown>
  stored_result_id?:          string
  // Insufficient-data fields
  insufficient_historical_data?: boolean
  available_points?:          number
  required_points?:           number
  missing_period_ratio?:      number | null
  reason?:                    string | null
}

// ── Parliamentary types ──
export interface ParliamentaryQueryOut {
  id:                  string
  question:            string
  status:              ParliamentaryStatus
  submitted_by_id:     string | null
  has_open_conflicts:  boolean
  evidence_count:      number
  confidence:          number | null
  final_answer:        string | null
  draft_answer_for_review?: string | null
  reviewer_note:       string | null
  created_at:          string
  updated_at:          string
  reviewed_at:         string | null
  evidence?:           unknown[]
}

// ── Reports ──
export interface ReportOut {
  id:              string
  label:           string | null
  entity_ids:      string[]
  metrics:         string[]
  period_start:    string
  period_end:      string
  status:          string
  storage_path:    string | null
  created_at:      string
  sections:        Record<string, unknown>[]
}

// ── Map types ──
export interface MapRegionEntry {
  region_id:    string
  region_name:  string
  state_name:   string
  value:        number | null
  unit:         string | null
  entity_count: number
}

export interface MapLayerResponse {
  layer:   string
  metric:  string | null
  unit:    string | null
  regions: MapRegionEntry[]
}

export interface MapRegionDetail {
  region_id:                 string
  region_name:               string
  state_name:                string
  entity_count:              number
  open_conflicts:            number
  avg_extraction_confidence: number | null
  data_quality_bucket:       string
  entities:                  Record<string, unknown>[]
}

// ── Search ──
export interface SearchHit {
  score:             number
  document_id:       string
  page_id:           string
  block_id:          string
  qdrant_point_id:   string
  page_number:       number
  block_type:        string
  text_excerpt:      string
  document_filename: string
}

export interface SearchResult {
  query:   string
  results: SearchHit[]
}

// ── Analytics types ──
export interface TrendDataPoint {
  period_label: string
  value:        number
  unit:         string
  fact_ids:     string[]
  has_conflict: boolean
}

export interface AnalyticsTrendResponse {
  entity_id:    string
  entity_name:  string
  metric:       string
  unit:         string
  series:       TrendDataPoint[]
  all_fact_ids: string[]
}

export interface CompareSeriesEntry {
  entity_id:   string
  entity_name: string
  series:      TrendDataPoint[]
}

export interface CompareResponse {
  metric: string
  unit:   string
  series: CompareSeriesEntry[]
}
