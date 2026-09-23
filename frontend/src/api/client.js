/**
 * Central API client for the CMPDI backend (http://localhost:8000).
 *
 * All requests go through /api/* which Vite proxies to the backend,
 * stripping the /api prefix before forwarding.
 *
 * Usage:
 *   import { apiFetch } from './client'
 *   const data = await apiFetch('/documents', { token })
 *   const data = await apiFetch('/documents/upload', { method: 'POST', body: formData, token })
 */

export const BASE = '/api'

/**
 * Structured error thrown for non-2xx responses.
 * Callers can check `err.status` to distinguish 401/403/404/422/500.
 */
export class ApiError extends Error {
  constructor(status, message, detail = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/**
 * Core fetch wrapper.
 *
 * @param {string} path       - Backend path e.g. '/documents' (no /api prefix needed)
 * @param {object} options    - Standard RequestInit options + `token` field
 * @param {string} [options.token]   - JWT access token (attached as Bearer)
 * @param {boolean} [options.blob]  - If true, return raw blob (for file downloads)
 * @returns {Promise<any>}    - Parsed JSON (or Blob if options.blob = true)
 */
export async function apiFetch(path, { token, blob = false, ...init } = {}) {
  const headers = new Headers(init.headers || {})

  // Attach auth token when available
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  // Only set Content-Type for JSON bodies; let browser set it for FormData
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
  })

  // Signal 401 globally so AuthContext can force logout
  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('cmpdi:unauthorized'))
    throw new ApiError(401, 'Session expired. Please log in again.')
  }

  if (!response.ok) {
    let detail = null
    try {
      const body = await response.json()
      detail = body.detail ?? body.message ?? null
    } catch {
      // non-JSON error body — ignore
    }
    throw new ApiError(
      response.status,
      detail ?? `Request failed with status ${response.status}`,
      detail,
    )
  }

  if (blob) return response.blob()

  // 204 No Content
  if (response.status === 204) return null

  return response.json()
}
