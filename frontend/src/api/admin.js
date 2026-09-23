/**
 * Admin API — user management (admin only).
 * Calls PATCH /auth/users/{id} and DELETE /auth/users/{id}.
 */
import { apiFetch } from './client'

/**
 * Update a user's role or active status.
 * @param {{ role?: string, isActive?: boolean }} updates
 */
export function updateUser(token, userId, { role, isActive } = {}) {
  const body = {}
  if (role !== undefined)     body.role      = role
  if (isActive !== undefined) body.is_active = isActive
  return apiFetch(`/auth/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
    token,
  })
}

/**
 * Soft-deactivate a user account (sets is_active=false).
 * Backend keeps the record for audit integrity.
 */
export function deactivateUser(token, userId) {
  return apiFetch(`/auth/users/${userId}`, { method: 'DELETE', token })
}
