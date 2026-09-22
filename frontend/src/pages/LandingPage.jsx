import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import InstitutionalHeader from '../components/InstitutionalHeader'
import InstitutionalFooter from '../components/InstitutionalFooter'
import { dashboardSummary } from '../data/dashboardMock'
import { ArrowIcon } from '../components/LandingNavigation'

const EXAMPLE_PROMPTS = [
  'Compare CCL and WCL production output for FY 2025-26',
  'Show mine safety audit discrepancies in SECL',
  'What is the environmental compliance status for MCL coalfields?',
]

const CORE_FEATURES = [
  {
    title: 'Document Intelligence',
    description: 'Converts mine reports, safety logs, and compliance records into structured, searchable operational evidence.',
    route: '/documents',
    icon: 'document',
  },
  {
    title: 'AI Intelligence',
    description: 'Cross-validates production, risk, and governance signals with traceable evidence and assisted query workflows.',
    route: '/ai-intelligence',
    icon: 'ai',
  },
  {
    title: 'Mining Operations',
    description: 'Tracks field-level performance, production patterns, and operational status across subsidiaries and coalfields.',
    route: '/mining-map',
    icon: 'map',
  },
]

const INSTITUTIONAL_MODULES = [
  { label: 'Documents', route: '/documents', icon: 'document' },
  { label: 'AI Intelligence', route: '/ai-intelligence', icon: 'ai' },
  { label: 'Parliamentary Responses', route: '/reports/parliamentary', icon: 'briefcase' },
  { label: 'Mining Map', route: '/mining-map', icon: 'map' },
  { label: 'Verification', route: '/data-quality', icon: 'shield' },
  { label: 'Reports', route: '/reports', icon: 'chart' },
]

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 10.5 7.8 14l8.2-9.2" />
    </svg>
  )
}

function DocumentIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 3.5h7l5 5V19a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5.5a2 2 0 0 1 2-2Z" />
      <path d="M14 3.5v5h5" />
      <path d="M8.5 12h7M8.5 15.5h7" />
    </svg>
  )
}

function AIIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 12a4 4 0 1 1 8 0 4 4 0 0 1-8 0Z" />
      <path d="M9.5 12h5M12 9.5v5M4 6.5V4.7A1.7 1.7 0 0 1 5.7 3h2.8M20 17.5v1.8a1.7 1.7 0 0 1-1.7 1.7h-2.8M20 6.5V4.7A1.7 1.7 0 0 0 18.3 3h-2.8M4 17.5v1.8A1.7 1.7 0 0 0 5.7 21h2.8" />
    </svg>
  )
}

function MapIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 4.5 3.5 6.3v13.2L9 16l6 3.5 5.5-1.8V4.5L15 6.3 9 4.5Z" />
      <path d="M9 4.5v11.5M15 6.3v11.5" />
    </svg>
  )
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3.2 18.5 5.8v5.4c0 4.2-2.6 7.8-6.5 9.6-3.9-1.8-6.5-5.4-6.5-9.6V5.8L12 3.2Z" />
      <path d="m9.5 12.1 1.6 1.6 3.4-3.7" />
    </svg>
  )
}

function BriefcaseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3.8 9.2A2 2 0 0 1 5.8 7.2h12.4a2 2 0 0 1 2 2v8.6a2 2 0 0 1-2 2H5.8a2 2 0 0 1-2-2V9.2Z" />
      <path d="M9 7.2V5.8A2 2 0 0 1 11 3.8h2a2 2 0 0 1 2 2v1.4M3.8 12.7h16.4" />
    </svg>
  )
}

function ChartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 18.5h16" />
      <path d="M7 15V9.5M12 15V6.5M17 15v-4" />
    </svg>
  )
}

const iconMap = {
  document: DocumentIcon,
  ai: AIIcon,
  map: MapIcon,
  shield: ShieldIcon,
  briefcase: BriefcaseIcon,
  chart: ChartIcon,
}

export default function LandingPage() {
  const navigate = useNavigate()
  const [queryInput, setQueryInput] = useState('')

  const formattedDocs = dashboardSummary.documentsProcessed.toLocaleString('en-IN')

  const handleQuerySubmit = (e) => {
    e.preventDefault()
    const queryToUse = queryInput.trim() || EXAMPLE_PROMPTS[0]
    navigate('/ai-intelligence', { state: { initialQuery: queryToUse } })
  }

  const handlePillClick = (promptText) => {
    navigate('/ai-intelligence', { state: { initialQuery: promptText } })
  }

  return (
    <div className="landing-page">
      <InstitutionalHeader />

      <main className="landing-main">
        <section className="landing-hero">
          <div className="landing-shell landing-hero__inner">
            <div className="landing-hero-copy">
              <p className="landing-kicker">CMPDI / Coal India</p>
              <h1>Mining Intelligence Operations</h1>
              <p className="landing-hero-subtitle">
                AI-assisted document processing, evidence-driven analysis, and operational oversight for coalfield governance and mine intelligence.
              </p>

              <form className="landing-ai-console" onSubmit={handleQuerySubmit}>
                <div className="landing-ai-console__header">
                  <div className="landing-ai-console__title">
                    <span className="landing-ai-console__dots" aria-hidden="true">
                      <span />
                      <span />
                      <span />
                    </span>
                    <span>AI QUERY CONSOLE</span>
                  </div>
                  <span className="landing-ai-console__live"><span className="landing-ai-console__live-dot" />Live</span>
                </div>

                <div className="landing-ai-console__prompt" aria-label="Suggested AI query">
                  <span className="landing-ai-console__prompt-mark">›</span>
                  <span>{EXAMPLE_PROMPTS[0]}</span>
                </div>

                <div className="landing-ai-console__input-row">
                  <input
                    type="text"
                    value={queryInput}
                    onChange={(event) => setQueryInput(event.target.value)}
                    placeholder="Ask about production, compliance, safety..."
                    aria-label="Ask about production, compliance, safety"
                  />
                  <button type="submit">
                    <span>Ask AI</span>
                    <ArrowIcon />
                  </button>
                </div>
              </form>
            </div>

            <div className="landing-hero-panel" aria-label="Operations overview panel">
              <div className="landing-hero-panel__top">
                <span className="landing-panel-tag">Operations overview</span>
                <span className="landing-panel-status">
                  <span className="landing-panel-status__dot" />
                  Live monitoring
                </span>
              </div>

              <div className="landing-panel-metrics">
                <div>
                  <strong>{formattedDocs}</strong>
                  <span>Ingested documents</span>
                </div>
                <div>
                  <strong>{dashboardSummary.automationRate}%</strong>
                  <span>Automation rate</span>
                </div>
                <div>
                  <strong>{dashboardSummary.pendingVerifications}</strong>
                  <span>Pending reviews</span>
                </div>
              </div>

              <ul className="landing-panel-list">
                <li>
                  <span className="landing-list-check"><CheckIcon /></span>
                  Subsidiary performance monitoring is active across mining operations.
                </li>
                <li>
                  <span className="landing-list-check"><CheckIcon /></span>
                  Evidence-backed review and verification workflows remain in progress.
                </li>
                <li>
                  <span className="landing-list-check"><CheckIcon /></span>
                  Production, governance, and compliance reporting are aligned to source records.
                </li>
              </ul>
            </div>
          </div>
        </section>

        <section id="platform" className="landing-feature-section landing-shell">
          <div className="landing-section-heading">
            <p className="landing-kicker">Operational platform</p>
            <h2>Institutional intelligence across the coal value chain</h2>
          </div>

          <div className="landing-feature-grid">
            {CORE_FEATURES.map(({ title, description, route, icon }) => {
              const Icon = iconMap[icon]

              return (
                <Link key={title} to={route} className="landing-feature-card">
                  <div className="landing-feature-card__icon">
                    <Icon />
                  </div>
                  <h3>{title}</h3>
                  <p>{description}</p>
                  <span className="landing-feature-card__link">
                    Access module
                    <ArrowIcon />
                  </span>
                </Link>
              )
            })}
          </div>
        </section>

        <section id="capabilities" className="landing-dark-band">
          <div className="landing-shell">
            <div className="landing-section-heading landing-section-heading--light">
              <p className="landing-kicker landing-kicker--light">Major capabilities</p>
              <h2>Operational oversight across the full institutional workflow</h2>
            </div>

            <div className="landing-module-grid">
              {INSTITUTIONAL_MODULES.map(({ label, route, icon }) => {
                const Icon = iconMap[icon]

                return (
                  <Link key={label} to={route} className="landing-module-item">
                    <div className="landing-module-item__icon">
                      <Icon />
                    </div>
                    <span>{label}</span>
                  </Link>
                )
              })}
            </div>
          </div>
        </section>

        <section className="landing-snapshot-section landing-shell">
          <div className="landing-section-heading landing-section-heading--left">
            <p className="landing-kicker">System snapshot</p>
            <h2>Evidence-led review with accountable operational controls</h2>
          </div>

          <div className="landing-snapshot-grid">
            <div className="landing-snapshot-card">
              <div className="landing-snapshot-label">Operational status</div>
              <div className="landing-snapshot-value">Stable</div>
              <ul className="landing-snapshot-list">
                <li><span className="landing-list-check"><CheckIcon /></span> Subsidiary monitoring remains current and aligned to source records.</li>
                <li><span className="landing-list-check"><CheckIcon /></span> Production reporting is active across each operational unit.</li>
              </ul>
            </div>

            <div className="landing-snapshot-card">
              <div className="landing-snapshot-label">Priority review</div>
              <div className="landing-snapshot-value">{dashboardSummary.pendingVerifications}</div>
              <ul className="landing-snapshot-list">
                <li><span className="landing-list-check"><CheckIcon /></span> Human verification queues are assigned and tracked.</li>
                <li><span className="landing-list-check"><CheckIcon /></span> Conflict resolution remains within review cycle thresholds.</li>
              </ul>
            </div>

            <div className="landing-snapshot-card">
              <div className="landing-snapshot-label">Current focus</div>
              <div className="landing-snapshot-value">Production intelligence</div>
              <ul className="landing-snapshot-list">
                <li><span className="landing-list-check"><CheckIcon /></span> CCL, WCL, SECL, and MCL operational indicators are active.</li>
                <li><span className="landing-list-check"><CheckIcon /></span> Governance and compliance reporting continue to be evidence-linked.</li>
              </ul>
            </div>
          </div>
        </section>

      </main>

      <InstitutionalFooter />
    </div>
  )
}
