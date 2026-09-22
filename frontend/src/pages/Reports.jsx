import { useMemo, useRef, useState } from 'react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import ExportButtons from '../components/reports/ExportButtons'
import ReportPreview from '../components/reports/ReportPreview'
import ReportScopeForm from '../components/reports/ReportScopeForm'
import { LoadingState } from '../components/ui/StatePanel'
import { reportsMock, reportsWorkspaceMock } from '../data/reportsMock'
import { ReportsTabNavigation } from './ReportsTabs'

const defaultForm = {
  timePeriod: '2025-26',
  subsidiaries: ['CCL', 'WCL', 'SECL'],
  metrics: ['Production', 'Dispatch', 'Quality'],
  requirements: ['Trend analysis', 'Comparative analysis'],
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 3.5h7l5 5V19a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5.5a2 2 0 0 1 2-2Z" />
      <path d="M14 3.5v5h5M8.5 13h7M8.5 16.5h5" />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="8.5" cy="8.5" r="5.2" />
      <path d="M13 13l4 4" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
      <path d="M10 4v12M4 10h12" />
    </svg>
  )
}

function MoreIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <circle cx="4" cy="10" r="1.3" />
      <circle cx="10" cy="10" r="1.3" />
      <circle cx="16" cy="10" r="1.3" />
    </svg>
  )
}

function ReportStatus({ status }) {
  return <span className={`reports-status reports-status--${status.toLowerCase()}`}>{status}</span>
}

export default function ReportsPage() {
  const [form, setForm] = useState(defaultForm)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [builderOpen, setBuilderOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState('All Reports')
  const [searchQuery, setSearchQuery] = useState('')
  const [dateRange, setDateRange] = useState('all')
  const [openMenu, setOpenMenu] = useState(null)
  const [notice, setNotice] = useState('')
  const builderRef = useRef(null)

  const filteredReports = useMemo(() => {
    const normalizedSearch = searchQuery.trim().toLowerCase()
    const days = dateRange === '30' ? 30 : dateRange === '90' ? 90 : null
    const cutoff = days ? new Date('2026-09-21T00:00:00') : null

    if (cutoff) {
      cutoff.setDate(cutoff.getDate() - days)
    }

    return reportsWorkspaceMock.reports.filter((item) => {
      const matchesCategory = selectedCategory === 'All Reports' || item.category === selectedCategory
      const matchesSearch = !normalizedSearch || [item.name, item.description, item.category, item.subsidiary].join(' ').toLowerCase().includes(normalizedSearch)
      const matchesDate = !cutoff || new Date(item.isoDate) >= cutoff
      return matchesCategory && matchesSearch && matchesDate
    })
  }, [dateRange, searchQuery, selectedCategory])

  const openBuilder = () => {
    setBuilderOpen(true)
    setNotice('')
    window.requestAnimationFrame(() => builderRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  const generateReport = () => {
    setLoading(true)
    const mainSubsidiary = form.subsidiaries[0] || 'CCL'
    const selected = reportsMock[form.timePeriod]?.[mainSubsidiary]

    window.setTimeout(() => {
      setReport(selected || reportsMock['2025-26'].CCL)
      setLoading(false)
    }, 1100)
  }

  const openReport = (item) => {
    const selected = reportsMock['2025-26']?.[item.subsidiary] || null
    setForm((current) => ({ ...current, timePeriod: '2025-26', subsidiaries: [item.subsidiary] }))
    setReport(selected)
    setOpenMenu(null)
    openBuilder()
  }

  const showActionNotice = (message) => {
    setNotice(message)
    setOpenMenu(null)
  }

  const showAllReports = () => {
    setSelectedCategory('All Reports')
    setSearchQuery('')
    setDateRange('all')
    document.getElementById('reports-table')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="reports-management">
      <section className="reports-hero" aria-labelledby="reports-analysis-title">
        <div className="reports-hero__copy">
          <p className="eyebrow">Reports &amp; Analysis</p>
          <h2 id="reports-analysis-title">Reports &amp; Analysis</h2>
          <p>Generate, view and analyze reports across subsidiaries, coalfields, and operational domains.</p>
        </div>
        <div className="reports-hero__editorial" aria-label="Data-driven decisions for a stronger Coal India">
          <span>Data-Driven</span>
          <span>Decisions for a</span>
          <span>Stronger Coal India</span>
        </div>
      </section>

      <section className="reports-kpi-grid" aria-label="Report summary">
        {reportsWorkspaceMock.summary.map((item) => (
          <div key={item.label} className={`reports-kpi-card reports-kpi-card--${item.tone}`}>
            <div className="reports-kpi-card__icon"><FileIcon /></div>
            <div>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.detail}</small>
            </div>
          </div>
        ))}
      </section>

      <ReportsTabNavigation />

      <section className="reports-management-grid" aria-label="Report management">
        <Card className="reports-categories-card">
          <div className="reports-panel-heading">
            <p className="eyebrow">Browse</p>
            <h3>Report categories</h3>
          </div>
          <nav className="reports-category-list" aria-label="Report categories">
            {reportsWorkspaceMock.categories.map((category) => (
              <button
                key={category.label}
                type="button"
                className={selectedCategory === category.label ? 'is-active' : ''}
                onClick={() => setSelectedCategory(category.label)}
              >
                <span>{category.label}</span>
                <strong>{category.count}</strong>
              </button>
            ))}
          </nav>
        </Card>

        <Card className="reports-table-card" id="reports-table">
          <div className="reports-panel-heading reports-panel-heading--table">
            <div>
              <p className="eyebrow">Validated records</p>
              <h3>Reports library</h3>
            </div>
            <span className="reports-result-count">{filteredReports.length} shown</span>
          </div>
          <div className="reports-filter-bar">
            <label className="reports-search-field">
              <SearchIcon />
              <input
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search reports by title, keyword, or category..."
                aria-label="Search reports by title, keyword, or category"
              />
            </label>
            <select value={dateRange} onChange={(event) => setDateRange(event.target.value)} aria-label="Select date range">
              <option value="all">Select date range</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
            </select>
            <Button variant="secondary" size="sm" onClick={() => setNotice('Filters are applied to the report library.')}>Filters</Button>
          </div>
          <div className="reports-table-wrap">
            <table className="reports-management-table">
              <thead>
                <tr>
                  <th>Report name</th>
                  <th>Category</th>
                  <th>Subsidiary</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {filteredReports.length ? filteredReports.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="reports-name-cell">
                        <span className="reports-file-type">{item.type}</span>
                        <span><strong>{item.name}</strong><small>{item.description}</small></span>
                      </div>
                    </td>
                    <td>{item.category}</td>
                    <td><span className="report-entity-badge">{item.subsidiary}</span></td>
                    <td>{item.date}</td>
                    <td><ReportStatus status={item.status} /></td>
                    <td className="reports-actions-cell">
                      <button type="button" className="reports-more-button" aria-label={`Actions for ${item.name}`} aria-expanded={openMenu === item.id} onClick={() => setOpenMenu(openMenu === item.id ? null : item.id)}>
                        <MoreIcon />
                      </button>
                      {openMenu === item.id && (
                        <div className="reports-actions-menu">
                          <button type="button" onClick={() => openReport(item)}>Open report</button>
                          <button type="button" onClick={() => showActionNotice(`Export is ready to connect for ${item.name}.`)}>Export</button>
                        </div>
                      )}
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan="6" className="reports-table-empty">No reports match the current filters.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {notice && <p className="reports-inline-notice" role="status">{notice}</p>}
        </Card>

        <aside className="reports-quick-column">
          <Card className="reports-quick-card">
            <div className="reports-panel-heading">
              <p className="eyebrow">Workspace</p>
              <h3>Quick actions</h3>
            </div>
            <Button onClick={openBuilder} className="reports-generate-action"><PlusIcon /> Generate new report</Button>
            <div className="reports-secondary-actions">
              <button type="button" onClick={() => showActionNotice('Scheduling is ready for a future reporting service.')}>Schedule report</button>
              <button type="button" onClick={() => showActionNotice('Templates will be available when document exports are connected.')}>Download templates</button>
              <button type="button" onClick={() => showActionNotice('Guidelines are available through the evidence and validation workflow.')}>Report guidelines</button>
            </div>
          </Card>

          <Card className="reports-recent-card">
            <div className="reports-panel-heading reports-panel-heading--compact">
              <p className="eyebrow">Latest activity</p>
              <h3>Recently generated</h3>
            </div>
            <div className="reports-recent-list">
              {reportsWorkspaceMock.recentlyGenerated.map((item) => (
                <div key={item.name}>
                  <span className="reports-recent-dot" />
                  <span><strong>{item.name}</strong><small>{item.date}</small></span>
                </div>
              ))}
            </div>
            <button type="button" className="reports-view-all" onClick={showAllReports}>View all <span aria-hidden="true">-&gt;</span></button>
          </Card>
        </aside>
      </section>

      <section className="reports-recent-section">
        <div className="reports-panel-heading">
          <p className="eyebrow">Archive</p>
          <h3>Recently generated reports</h3>
        </div>
        <div className="reports-recent-rail">
          {reportsWorkspaceMock.recentlyGenerated.map((item) => (
            <div key={item.name} className="reports-recent-rail__item">
              <span className="reports-recent-dot" />
              <div><strong>{item.name}</strong><small>{item.date}</small></div>
              <ReportStatus status={item.status} />
            </div>
          ))}
        </div>
      </section>

      {builderOpen && (
        <section ref={builderRef} className="report-builder-section" aria-label="Report builder">
          <div className="report-builder-section__heading">
            <div>
              <p className="eyebrow">Report builder</p>
              <h3>Configure and generate</h3>
            </div>
            <button type="button" className="reports-close-builder" onClick={() => setBuilderOpen(false)}>Close builder</button>
          </div>
          <ReportScopeForm form={form} setForm={setForm} onGenerate={generateReport} loading={loading} />
          {loading ? (
            <Card className="report-card report-card--result">
              <LoadingState title="Generating report preview" description="Compiling the latest metrics and validations for this view." />
            </Card>
          ) : report ? (
            <Card className="report-card report-card--preview">
              <div className="report-toolbar">
                <div><p className="eyebrow">Review and evidence</p><h2>Generated report preview</h2></div>
                <ExportButtons />
              </div>
              <ReportPreview report={report} form={form} />
            </Card>
          ) : (
            <div className="report-empty-state"><p className="eyebrow">Report result</p><h2>No report generated yet</h2><p>Set your scope above and generate a report to inspect evidence and export the result.</p></div>
          )}
        </section>
      )}
    </div>
  )
}
