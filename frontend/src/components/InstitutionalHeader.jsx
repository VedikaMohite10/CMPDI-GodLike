import React from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Documents', path: '/documents' },
  { label: 'AI Intelligence', path: '/ai-intelligence' },
  { label: 'Reports', path: '/reports' },
  { label: 'Mining Map', path: '/mining-map' },
]

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}

export default function InstitutionalHeader() {
  const location = useLocation()

  return (
    <>
      <div className="dashboard-topbar-utility">
        <div className="dashboard-shell-inner dashboard-topbar-utility__inner">
          <div className="dashboard-topbar-meta">
            <span>Coal India Limited</span>
            <span>CMPDI / Central Mine Planning &amp; Design Institute</span>
          </div>
          <div className="dashboard-topbar-links">
            <a href="#platform">Platform</a>
            <a href="#capabilities">Capabilities</a>
            <a href="#operations">Operations</a>
          </div>
        </div>
      </div>

      <header className="dashboard-site-header">
        <div className="dashboard-shell-inner dashboard-site-header__inner">
          <Link to="/" className="dashboard-brand" style={{ textDecoration: 'none' }} aria-label="CMPDI Mining Intelligence Platform">
            <div className="dashboard-logo-mark">CMPDI</div>
            <div className="dashboard-brand-text">
              <span className="dashboard-brand-title">Mining Intelligence Platform</span>
              <span className="dashboard-brand-subtitle">Coal India Limited</span>
            </div>
          </Link>

          <nav className="dashboard-nav" aria-label="Main navigation">
            {NAV_ITEMS.map(({ label, path }) => (
              <NavLink
                key={path}
                to={path}
                className={({ isActive }) => {
                  const isDashboard = path === '/dashboard' && location.pathname.startsWith('/dashboard')
                  const isDocuments = path === '/documents' && location.pathname.startsWith('/documents')
                  const isAI = path === '/ai-intelligence' && location.pathname.startsWith('/ai-intelligence')
                  const isReports = path === '/reports' && location.pathname.startsWith('/reports')
                  const isMap = path === '/mining-map' && location.pathname.startsWith('/mining-map')

                  const active = isActive || isDashboard || isDocuments || isAI || isReports || isMap

                  return `dashboard-nav__link ${active ? 'is-active' : ''}`
                }}
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Link to="/dashboard" className="dashboard-header-cta">
              <span>Open Dashboard</span>
              <ArrowIcon />
            </Link>

            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: '#efece6',
                border: '1px solid var(--border)',
                display: 'grid',
                placeItems: 'center',
                fontWeight: 700,
                fontSize: '12px',
                color: 'var(--navy-900)',
                position: 'relative',
              }}
              title="User Account"
            >
              DT
              <span
                style={{
                  position: 'absolute',
                  bottom: '1px',
                  right: '1px',
                  width: '9px',
                  height: '9px',
                  borderRadius: '50%',
                  background: '#22c55e',
                  border: '2px solid #ffffff',
                }}
              />
            </div>
          </div>
        </div>
      </header>
    </>
  )
}
