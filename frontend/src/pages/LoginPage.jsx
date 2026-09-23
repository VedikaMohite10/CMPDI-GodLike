/**
 * LoginPage — dedicated /login route (Phase 6).
 *
 * Renders a full-screen branded login form.
 * On success: redirects to the page the user was trying to reach,
 * or /dashboard as default.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function CoalFlameIcon() {
  return (
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" width="28" height="28" aria-hidden="true">
      <path
        d="M20 4C14 10 10 15 10 22a10 10 0 0 0 20 0c0-4-2-8-5-11-1 3-3 5-5 5 0-4 0-8 0-12Z"
        fill="rgba(212,115,46,0.9)"
      />
      <path
        d="M20 16c-1.5 2-2.5 4-2.5 6a2.5 2.5 0 0 0 5 0c0-2-1-4-2.5-6Z"
        fill="rgba(255,200,100,0.8)"
      />
    </svg>
  )
}

export default function LoginPage() {
  const { login, isAuthenticated, error, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname ?? '/dashboard'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const userRef = useRef(null)

  // If already authenticated, skip login
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, authLoading, navigate, from])

  useEffect(() => {
    userRef.current?.focus()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password) return
    setSubmitting(true)
    const result = await login(username.trim(), password)
    setSubmitting(false)
    if (result.success) {
      navigate(from, { replace: true })
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #07191b 0%, #0d2b2e 40%, #123a3e 70%, #1a4f55 100%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background geometry */}
      <svg
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', opacity: 0.07 }}
        viewBox="0 0 1440 900"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        <circle cx="200" cy="150" r="400" stroke="white" strokeWidth="0.8" />
        <circle cx="1300" cy="750" r="500" stroke="white" strokeWidth="0.8" />
        <path d="M0 600 Q 360 400 720 550 Q 1080 700 1440 500" stroke="rgba(212,115,46,0.6)" strokeWidth="1" fill="none" />
        <path d="M0 700 Q 400 500 800 650 Q 1100 760 1440 600" stroke="rgba(212,115,46,0.4)" strokeWidth="1" fill="none" />
      </svg>

      {/* Institution badge at top */}
      <div style={{
        position: 'absolute',
        top: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        color: 'rgba(255,255,255,0.45)',
        fontSize: '12px',
        fontWeight: 600,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
      }}>
        <span style={{ width: '32px', height: '1px', background: 'rgba(255,255,255,0.2)' }} />
        Government of India &middot; Ministry of Coal
        <span style={{ width: '32px', height: '1px', background: 'rgba(255,255,255,0.2)' }} />
      </div>

      {/* Login card */}
      <div style={{ width: '100%', maxWidth: '400px', position: 'relative', zIndex: 2 }}>
        {/* Brand mark */}
        <div style={{ textAlign: 'center', marginBottom: '36px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '64px',
            height: '64px',
            borderRadius: '14px',
            background: 'rgba(212,115,46,0.15)',
            border: '1px solid rgba(212,115,46,0.35)',
            marginBottom: '16px',
            boxShadow: '0 0 32px rgba(212,115,46,0.2)',
          }}>
            <CoalFlameIcon />
          </div>
          <h1 style={{ margin: '0 0 6px', color: '#ffffff', fontSize: '22px', fontWeight: 800, letterSpacing: '-0.01em' }}>
            CMPDI Intelligence Platform
          </h1>
          <p style={{ margin: 0, color: 'rgba(255,255,255,0.45)', fontSize: '13px' }}>
            Coal India Limited &middot; Operational Intelligence
          </p>
        </div>

        {/* Form card */}
        <form
          id="login-form"
          onSubmit={handleSubmit}
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '16px',
            padding: '32px',
            backdropFilter: 'blur(16px)',
            boxShadow: '0 32px 80px rgba(0,0,0,0.5)',
          }}
        >
          <p style={{ margin: '0 0 24px', color: 'rgba(255,255,255,0.6)', fontSize: '13px', textAlign: 'center' }}>
            Sign in with your CMPDI credentials
          </p>

          {/* Username */}
          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="login-username" style={{
              display: 'block', color: 'rgba(255,255,255,0.65)', fontSize: '11px',
              fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px',
            }}>
              Username
            </label>
            <input
              id="login-username"
              ref={userRef}
              type="text"
              value={username}
              required
              autoComplete="username"
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              style={{
                width: '100%', padding: '11px 14px', borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.14)', background: 'rgba(255,255,255,0.07)',
                color: '#ffffff', fontSize: '14px', outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: '24px' }}>
            <label htmlFor="login-password" style={{
              display: 'block', color: 'rgba(255,255,255,0.65)', fontSize: '11px',
              fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px',
            }}>
              Password
            </label>
            <input
              id="login-password"
              type="password"
              value={password}
              required
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              style={{
                width: '100%', padding: '11px 14px', borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.14)', background: 'rgba(255,255,255,0.07)',
                color: '#ffffff', fontSize: '14px', outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Error banner */}
          {error && (
            <div style={{
              background: 'rgba(220,50,50,0.12)', border: '1px solid rgba(220,50,50,0.35)',
              borderRadius: '8px', padding: '10px 14px', color: '#ff8080', fontSize: '13px',
              marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px',
            }}>
              <span style={{ fontSize: '15px' }}>&#9888;</span>
              <span>{error}</span>
            </div>
          )}

          {/* Submit */}
          <button
            id="login-submit"
            type="submit"
            disabled={submitting || !username.trim() || !password}
            style={{
              width: '100%', padding: '12px', borderRadius: '8px', border: 'none',
              background: submitting || !username.trim() || !password
                ? 'rgba(212,115,46,0.35)'
                : 'linear-gradient(135deg, #d4732e 0%, #c05d1e 100%)',
              color: '#ffffff', fontSize: '14px', fontWeight: 700, letterSpacing: '0.04em',
              cursor: submitting || !username.trim() || !password ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              boxShadow: submitting ? 'none' : '0 4px 16px rgba(212,115,46,0.3)',
            }}
          >
            {submitting ? 'Signing in\u2026' : 'Sign in \u2192'}
          </button>
        </form>

        <p style={{ marginTop: '24px', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '11px', lineHeight: 1.6 }}>
          Restricted to authorised CMPDI personnel only.<br />
          Unauthorised access is a punishable offence.
        </p>
      </div>
    </div>
  )
}
