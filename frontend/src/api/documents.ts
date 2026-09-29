import { apiClient } from './client'
import type { DocumentSummary, DocumentDetail, FactProcessingStatus } from '../types'

// Re-export types so consumers can import from this module
export type { DocumentSummary, DocumentDetail, FactProcessingStatus }

// ── Upload ──────────────────────────────────────────────────────────────────
export async function uploadDocuments(files: File[]) {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  const { data } = await apiClient.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ── List ────────────────────────────────────────────────────────────────────
export async function listDocuments(params: {
  page?: number
  page_size?: number
  status?: string
  file_type?: string
} = {}): Promise<{ items: DocumentSummary[]; total: number; page: number; page_size: number }> {
  const { data } = await apiClient.get('/documents', { params })
  return data
}

// ── Single doc ──────────────────────────────────────────────────────────────
export async function getDocument(id: string): Promise<DocumentDetail> {
  const { data } = await apiClient.get(`/documents/${id}`)
  return data
}

// ── Processing status ───────────────────────────────────────────────────────
export async function getDocumentStatus(id: string) {
  const { data } = await apiClient.get(`/documents/${id}/status`)
  return data
}

// ── Fact extraction — Phase 2 ───────────────────────────────────────────────
// force=true lets you re-run even if already done
export async function processDocumentFacts(id: string, force = false) {
  const { data } = await apiClient.post(
    `/documents/${id}/process-facts`,
    null,
    { params: force ? { force: true } : undefined }
  )
  return data
}

export async function getFactProcessingStatus(id: string): Promise<FactProcessingStatus> {
  const { data } = await apiClient.get(`/documents/${id}/process-facts/status`)
  return data
}

// ── Download URL ────────────────────────────────────────────────────────────
export function getDocumentDownloadUrl(id: string) {
  return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/documents/${id}/original`
}
