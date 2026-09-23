/**
 * Authentication API functions.
 * Talks to POST /auth/login and GET /auth/me.
 */
import { apiFetch } from './client'

/**
 * Exchange credentials for a JWT access token.
 * Backend expects OAuth2 form-encoded body.
 *
 * @returns {{ access_token, token_type, expires_in_minutes, username, role }}
 */
export async function loginWithCredentials(username, password) {
  const body = new URLSearchParams()
  body.append('username', username)
  body.append('password', password)

  return apiFetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  })
}

/**
 * Fetch the authenticated user's profile.
 * Used to restore session from a stored token.
 *
 * @returns {{ id, username, role, is_active }}
 */
export async function getMe(token) {
  return apiFetch('/auth/me', { token })
}
