import React from 'react'
import TrendChart from '../components/dashboard/TrendChart'
import { dashboardSummary } from '../data/dashboardMock'

const formatNumber = (value) => new Intl.NumberFormat('en-IN').format(value)

const reviewRows = [
  { item: 'Environmental Compliance Report', type: 'Compliance', subsidiary: 'MCL', date: '21 Sep 2026', status: 'Under Review', action: 'Review' },
  { item: 'Parliamentary Question Response', type: 'Parliamentary', subsidiary: 'SECL', date: '20 Sep 2026', status: 'Pending', action: 'Take Action' },
  { item: 'Production Data Discrepancy', type: 'Production', subsidiary: 'WCL', date: '19 Sep 2026', status: 'Needs Verification', action: 'Verify' },
]

export default function DashboardPage() {
  const summary = dashboardSummary
  const processedValue = 112430
  const processedShare = 75.7

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero" id="operations">
        <div className="dashboard-hero__copy">
          <p className="dashboard-kicker">Executive operations</p>
          <h1>Mining Operations Overview</h1>
          <p className="dashboard-hero__description">
            Real-time view of document processing, production insights, compliance status, and operational intelligence across CIL subsidiaries.
          </p>
        </div>

        <div className="dashboard-status-panel">
          <div className="dashboard-panel-header dashboard-panel-header--status">
            <span className="dashboard-panel-label">System status</span>
            <span className="dashboard-online"><span className="dashboard-online__dot" />All systems operational</span>
          </div>

          <div className="dashboard-status-grid">
            <div className="dashboard-metric-card">
              <strong>{formatNumber(summary.documentsProcessed)}</strong>
              <span>Documents processed</span>
            </div>
            <div className="dashboard-metric-card">
              <strong>{summary.automationRate}%</strong>
              <span>Automation rate</span>
            </div>
            <div className="dashboard-metric-card">
              <strong>{summary.pendingVerifications}</strong>
              <span>Pending reviews</span>
            </div>
            <div className="dashboard-metric-card">
              <strong>{summary.subsidiaries.length}</strong>
              <span>Subsidiaries active</span>
            </div>
          </div>

          <div className="dashboard-status-checklist">
            <span>Document pipelines active</span>
            <span>AI analysis operational</span>
            <span>Verification workflows running</span>
            <span>Reports up to date</span>
          </div>
        </div>
      </section>

      <section className="dashboard-analytics" id="platform">
        <article className="dashboard-panel dashboard-panel--wide">
          <div className="dashboard-panel-header dashboard-panel-header--split">
            <div>
              <p className="dashboard-kicker">Production trends</p>
              <h2>Monthly Coal Production</h2>
            </div>
            <button type="button" className="dashboard-filter-button">Last 6 Months</button>
          </div>
          <TrendChart data={summary.trend} />
        </article>

        <article className="dashboard-panel" id="capabilities">
          <div className="dashboard-panel-header dashboard-panel-header--split">
            <div>
              <p className="dashboard-kicker">Document processing</p>
              <h2>Document Ingestion Status</h2>
            </div>
            <button type="button" className="dashboard-filter-button">All Document Types</button>
          </div>

          <div className="dashboard-donut-wrap">
            <div className="dashboard-donut" aria-label="Documents processed breakdown">
              <div className="dashboard-donut__inner">
                <strong>{formatNumber(summary.documentsProcessed)}</strong>
                <span>Total</span>
              </div>
            </div>

            <ul className="dashboard-donut-legend">
              <li>
                <span className="dashboard-legend-dot dashboard-legend-dot--processed" />
                <span className="dashboard-legend-label">Processed</span>
                <strong>{formatNumber(processedValue)}</strong>
                <em>{processedShare}%</em>
              </li>
              <li>
                <span className="dashboard-legend-dot dashboard-legend-dot--review" />
                <span className="dashboard-legend-label">In Review</span>
                <strong>{formatNumber(21400)}</strong>
                <em>14.4%</em>
              </li>
              <li>
                <span className="dashboard-legend-dot dashboard-legend-dot--pending" />
                <span className="dashboard-legend-label">Pending</span>
                <strong>{formatNumber(9860)}</strong>
                <em>6.6%</em>
              </li>
              <li>
                <span className="dashboard-legend-dot dashboard-legend-dot--failed" />
                <span className="dashboard-legend-label">Failed</span>
                <strong>{formatNumber(4900)}</strong>
                <em>3.3%</em>
              </li>
            </ul>
          </div>
        </article>
      </section>

      <section className="dashboard-panel dashboard-panel--table">
        <div className="dashboard-panel-header dashboard-panel-header--split">
          <div>
            <p className="dashboard-kicker">Requires attention</p>
            <h2>Pending Reviews &amp; Actions</h2>
          </div>
          <button type="button" className="dashboard-filter-button">View all</button>
        </div>
        <p className="dashboard-panel-subtitle">Items requiring review, verification, or further action.</p>

        <div className="dashboard-table-wrap">
          <table className="dashboard-review-table">
            <thead>
              <tr>
                <th>Document / Item</th>
                <th>Type</th>
                <th>Subsidiary</th>
                <th>Date</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {reviewRows.map((row) => (
                <tr key={row.item}>
                  <td>{row.item}</td>
                  <td>{row.type}</td>
                  <td>{row.subsidiary}</td>
                  <td>{row.date}</td>
                  <td><span className={`dashboard-status-badge dashboard-status-badge--${row.status.toLowerCase().replace(/\s+/g, '-')}`}>{row.status}</span></td>
                  <td className="dashboard-action-cell">{row.action} →</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
