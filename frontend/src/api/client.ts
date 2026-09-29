import axios, { type AxiosInstance, type AxiosError } from 'axios'
import { API_BASE_URL } from '../app/config'
import { useAuthStore } from '../stores/authStore'

// Create Axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request Interceptor: attach JWT ──
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response Interceptor: handle 401/403 ──
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid — clear auth state
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Typed error helper ──
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string })?.detail
    if (detail) return detail
    if (error.response?.status === 403) return 'You do not have permission to perform this action.'
    if (error.response?.status === 404) return 'The requested resource was not found.'
    if (error.response?.status === 500) return 'An internal server error occurred. Please try again.'
    return error.message || 'Network error'
  }
  if (error instanceof Error) return error.message
  return 'An unknown error occurred.'
}

// ── Multipart form client for file uploads ──
export function createFormDataClient(): AxiosInstance {
  const token = useAuthStore.getState().token
  return axios.create({
    baseURL: API_BASE_URL,
    timeout: 120000,
    headers: {
      'Content-Type': 'multipart/form-data',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}
