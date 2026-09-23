import { useEffect, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Breadcrumbs from '../components/Breadcrumbs'
import LandingNavigation from '../components/LandingNavigation'
import InstitutionalHeader from '../components/InstitutionalHeader'
import InstitutionalFooter from '../components/InstitutionalFooter'
import { useAuth } from '../context/AuthContext'

// ---------------------------------------------------------------------------
// Inline login overlay — shown whenever the user is not authenticated.
// A full /login route is added in Phase 6; this keeps the app functional now.
// ---------------------------------------------------------------------------
function LoginOverlay() {
  const { login, error } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const userRef = useRef(null)

  useEffect(() => {
    userRef.current?.focus()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    await login(username, password)
    setLoading(false)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'linear-gradient(135deg, #0d2b2e 0%, #123a3e 60%, #1c4f54 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <form onSubmit={handleSubmit} style={{
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: '12px',
        padding: '40px 36px',
        width: '360px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 24px 64px rgba(0,0,0,0.4)',
      }}>
        {/* Logo / brand mark */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: '52px', height: '52px', borderRadius: '10px',
            background: 'rgba(212,115,46,0.2)', border: '1px solid rgba(212,115,46,0.4)',
            marginBottom: '14px',
          }}>
            <span style={{ fontSize: '22px', fontWeight: 900, color: '#d4732e' }}>C</span>
          </div>
          <div style={{ color: '#fff', fontSize: '17px', fontWeight: 700, letterSpacing: '0.3px' }}>
            CMPDI Intelligence Platform
          </div>
          <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px', marginTop: '4px' }}>
            Coal India Limited · Ministry of Coal
          </div>
        </div>

        {/* Fields */}
        {[
          { label: 'Username', value: username, setter: setUsername, type: 'text', ref: userRef },
          { label: 'Password', value: password, setter: setPassword, type: 'password', ref: null },
        ].map(({ label, value, setter, type, ref }) => (
          <div key={label} style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', color: 'rgba(255,255,255,0.7)', fontSize: '12px', fontWeight: 600, marginBottom: '6px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
              {label}
            </label>
            <input
              ref={ref}
              type={type}
              value={value}
              required
              autoComplete={type === 'password' ? 'current-password' : 'username'}
              onChange={(e) => setter(e.target.value)}
              style={{
                width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.18)',
                background: 'rgba(255,255,255,0.08)', color: '#fff', fontSize: '14px',
                outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>
        ))}

        {/* Error message */}
        {error && (
          <div style={{
            background: 'rgba(220,50,50,0.15)', border: '1px solid rgba(220,50,50,0.4)',
            borderRadius: '6px', padding: '10px 12px',
            color: '#ff8080', fontSize: '13px', marginBottom: '16px',
          }}>
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%', padding: '11px', borderRadius: '6px', border: 'none',
            background: loading ? 'rgba(212,115,46,0.4)' : '#d4732e',
            color: '#fff', fontSize: '14px', fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
            letterSpacing: '0.3px', transition: 'background 0.2s',
          }}
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main shell
// ---------------------------------------------------------------------------
export default function AppShell() {
  const location = useLocation()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(false)
  const { isAuthenticated, loading } = useAuth()

  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [location.pathname])

  const handleMenuToggle = () => {
    if (window.innerWidth <= 768) {
      setIsMobileMenuOpen((state) => !state)
      return
    }
    setIsDesktopCollapsed((state) => !state)
  }

  // While restoring session from sessionStorage, show a minimal spinner
  if (loading) {
    return (
      <div style={{
        position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#0d2b2e',
      }}>
        <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>Loading…</div>
      </div>
    )
  }

  // Not authenticated — show login overlay above everything
  if (!isAuthenticated) {
    return <LoginOverlay />
  }

  if (location.pathname.startsWith('/dashboard')) {
    return (
      <div className="dashboard-shell">
        <Outlet />
      </div>
    )
  }

  if (location.pathname.startsWith('/reports')) {
    return (
      <div className="reports-route-shell">
        <LandingNavigation />
        <main className="reports-route-shell__main">
          <div className="reports-route-shell__container">
            <Breadcrumbs key={location.pathname} />
            <Outlet />
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="platform-app-shell">
      <InstitutionalHeader />
      <main className="platform-main-container">
        <Outlet />
      </main>
      <InstitutionalFooter />
    </div>
  )
}

