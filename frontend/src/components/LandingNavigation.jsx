import { Link, useLocation } from 'react-router-dom'
import '../styles/LandingPage.css'

export function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}

export default function LandingNavigation() {
  const location = useLocation()

  return (
    <>
      <div className="landing-utility-bar">
        <div className="landing-shell landing-utility-bar__inner">
          <div className="landing-utility-meta">
            <span>Coal India Limited</span>
            <span>CMPDI / Central Mine Planning &amp; Design Institute</span>
          </div>
          <div className="landing-utility-links">
            <a href="/#platform">Platform</a>
            <a href="/#capabilities">Capabilities</a>
            <a href="/#insight">Operations</a>
          </div>
        </div>
      </div>

      <header className="landing-header">
        <div className="landing-shell landing-header__inner">
          <Link to="/" className="landing-brand" aria-label="CMPDI Mining Intelligence Platform">
            <div className="landing-logo-mark">CMPDI</div>
            <div className="landing-brand-text">
              <span className="landing-brand-title">Mining Intelligence Platform</span>
              <span className="landing-brand-subtitle">Coal India Limited</span>
            </div>
          </Link>

          <nav className="landing-header-nav" aria-label="Main navigation">
            <Link className={location.pathname.startsWith('/dashboard') ? 'is-active' : ''} to="/dashboard">Dashboard</Link>
            <Link className={location.pathname.startsWith('/documents') ? 'is-active' : ''} to="/documents">Documents</Link>
            <Link className={location.pathname.startsWith('/ai-intelligence') ? 'is-active' : ''} to="/ai-intelligence">AI Intelligence</Link>
            <Link className={location.pathname.startsWith('/reports') ? 'is-active' : ''} to="/reports">Reports</Link>
            <Link className={location.pathname.startsWith('/mining-map') ? 'is-active' : ''} to="/mining-map">Mining Map</Link>
          </nav>

          <Link to="/dashboard" className="landing-header-cta">
            <span>Open Dashboard</span>
            <ArrowIcon />
          </Link>
        </div>
      </header>
    </>
  )
}
