/**
 * AuthContext — JWT-based authentication.
 *
 * Token is stored in component state only (never localStorage) to prevent
 * XSS token theft.  On mount we try to restore from sessionStorage so a
 * page refresh within the same tab keeps the user logged in.
 *
 * Events:
 *   window cmpdi:unauthorized  fired by apiFetch on 401 — triggers logout
 */
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { getMe, loginWithCredentials } from '../api/auth'
import { ApiError } from '../api/client'

const SESSION_KEY = 'cmpdi_token'
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)   // { id, username, role, is_active }
  const [token, setToken]     = useState(null)   // raw JWT string
  const [loading, setLoading] = useState(true)   // true while restoring session
  const [error, setError]     = useState(null)   // last login error message

  // Keep a ref so event listeners always see the latest setter
  const logoutRef = useRef(null)

  const logout = useCallback(() => {
    setUser(null)
    setToken(null)
    sessionStorage.removeItem(SESSION_KEY)
  }, [])

  logoutRef.current = logout

  // --- Restore session from sessionStorage on tab reload ---
  useEffect(() => {
    const stored = sessionStorage.getItem(SESSION_KEY)
    if (!stored) {
      setLoading(false)
      return
    }
    // Validate stored token is still accepted by the backend
    getMe(stored)
      .then((profile) => {
        setToken(stored)
        setUser({ ...profile })
      })
      .catch(() => {
        // Token expired or backend down — clear it
        sessionStorage.removeItem(SESSION_KEY)
      })
      .finally(() => setLoading(false))
  }, [])

  // --- Listen for 401 signals from apiFetch ---
  useEffect(() => {
    const handle = () => logoutRef.current?.()
    window.addEventListener('cmpdi:unauthorized', handle)
    return () => window.removeEventListener('cmpdi:unauthorized', handle)
  }, [])

  // --- Public login action ---
  const login = useCallback(async (username, password) => {
    setError(null)
    try {
      const resp = await loginWithCredentials(username, password)
      const { access_token } = resp

      // Fetch full profile (includes id, is_active)
      const profile = await getMe(access_token)
      setToken(access_token)
      setUser({ ...profile })
      sessionStorage.setItem(SESSION_KEY, access_token)
      return { success: true, user: profile }
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? (err.detail ?? err.message)
          : 'Backend unreachable. Check that the server is running.'
      setError(msg)
      return { success: false, error: msg }
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: user?.role ?? null,
        isAuthenticated: !!user,
        loading,
        error,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return ctx
}
