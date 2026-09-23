/**
 * Documents API — Phase 1 ingestion pipeline.
 *
 * All functions accept `token` as first argument (from useAuth().token).
 */
import { apiFetch } from './client'

/** List documents with optional filters and pagination. */
export function listDocuments(token, { page = 1, pageSize = 20, status, fileType } = {}) {
  const params = new URLSearchParams({ page, page_size: pageSize })
  if (status)   params.set('status', status)
  if (fileType) params.set('file_type', fileType)
  return apiFetch(`/documents?${params}`, { token })
}

/** Get a single document's detail + extraction summary. */
export function getDocument(token, id) {
  return apiFetch(`/documents/${id}`, { token })
}

/**
 * Upload one or more files.
 * @param {FileList|File[]} files
 * @returns {{ documents: [{id, filename, processing_status}] }}
 */
export function uploadDocuments(token, files) {
  const body = new FormData()
  Array.from(files).forEach((f) => body.append('files', f))
  return apiFetch('/documents/upload', { method: 'POST', body, token })
}

/** Poll processing status for a single document. */
export function getDocumentStatus(token, id) {
  return apiFetch(`/documents/${id}/status`, { token })
}

/**
 * Download the original document file.
 * Returns a blob: URL that the caller can assign to an <a href>.
 */
export async function downloadOriginal(token, id) {
  const blob = await apiFetch(`/documents/${id}/original`, { blob: true, token })
  return URL.createObjectURL(blob)
}

/** Get all extracted content for a single page (text blocks, tables, images). */
export function getPageContent(token, docId, pageNumber) {
  return apiFetch(`/documents/${docId}/pages/${pageNumber}`, { token })
}

/** Trigger Phase 2 fact extraction for a single document. */
export function triggerPhase2(token, id, force = false) {
  const params = force ? '?force=true' : ''
  return apiFetch(`/documents/${id}/process-facts${params}`, { method: 'POST', token })
}

/** Trigger Phase 2 for all ready documents (batch). */
export function triggerPhase2Batch(token, force = false) {
  const params = force ? '?force=true' : ''
  return apiFetch(`/documents/process-facts/batch${params}`, { method: 'POST', token })
}

/** Poll Phase 2 status for a document. */
export function getPhase2Status(token, id) {
  return apiFetch(`/documents/${id}/process-facts/status`, { token })
}

/** Get topic assignments for a document. */
export function getDocumentTopics(token, id) {
  return apiFetch(`/documents/${id}/topics`, { token })
}
