import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import DataTable from '../ui/DataTable'
import Badge from '../ui/Badge'
import EvidenceExplorer from '../evidence/EvidenceExplorer'

const tableColumns = [
  { key: 'metric', label: 'Metric' },
  { key: 'ccl', label: 'CCL' },
  { key: 'wcl', label: 'WCL' },
  { key: 'secl', label: 'SECL' },
]

export default function ReportPreview({ report, form }) {
  if (!report) {
    return null
  }

  const reportingPeriod = form?.timePeriod || '2025-26'
  const selectedEntities = form?.subsidiaries?.length ? form.subsidiaries.join(', ') : 'No entities selected'
  const generatedDate = new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date())

  const tableRows = [
    { id: 'production', metric: 'Production', ccl: '26.4 Mt', wcl: '21.1 Mt', secl: '18.9 Mt' },
    { id: 'dispatch', metric: 'Dispatch', ccl: '18.9 Mt', wcl: '15.6 Mt', secl: '16.3 Mt' },
    { id: 'quality', metric: 'Quality', ccl: '5023 kcal/kg', wcl: '4740 kcal/kg', secl: '5120 kcal/kg' },
  ]

  return (
    <div className="report-preview">
      <div className="report-preview__header">
        <div>
          <p className="eyebrow">Generated report</p>
          <h2>Management performance report</h2>
        </div>
      </div>

      <div className="report-metadata" aria-label="Report metadata">
        <div className="report-metadata__item">
          <span>Reporting period</span>
          <strong>FY {reportingPeriod}</strong>
        </div>
        <div className="report-metadata__item">
          <span>Entities</span>
          <strong>{selectedEntities}</strong>
        </div>
        <div className="report-metadata__item">
          <span>Generated</span>
          <strong>{generatedDate}</strong>
        </div>
        <div className="report-metadata__item">
          <span>Status</span>
          <strong>Ready for review</strong>
        </div>
      </div>

      <section className="report-section">
        <h3>Executive Summary</h3>
        <p>{report.executiveSummary}</p>
      </section>

      <section className="report-section">
        <h3>Key Metrics</h3>
        <div className="report-metrics">
          <div className="report-metric-card">
            <span>Total production</span>
            <strong>{report.productionOverview.total}</strong>
          </div>
          <div className="report-metric-card">
            <span>Year-on-year</span>
            <strong>{report.productionOverview.yoy}</strong>
          </div>
          <div className="report-metric-card">
            <span>Dispatch</span>
            <strong>{report.productionOverview.dispatch}</strong>
          </div>
          <div className="report-metric-card">
            <span>Quality</span>
            <strong>{report.productionOverview.quality}</strong>
          </div>
        </div>
      </section>

      <section className="report-section">
        <h3>Historical Trends</h3>
        <div className="report-chart">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={report.historicalTrends}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
              <XAxis dataKey="label" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip />
              <Area type="monotone" dataKey="value" stroke="var(--navy-800)" fill="var(--surface-strong)" strokeWidth={2.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="report-section">
        <h3>Comparative Analysis</h3>
        <div className="report-analysis-list">
          {report.comparativeAnalysis.map((item) => (
            <div key={item.title} className="report-analysis-item">
              <div className="report-analysis-item__topline">
                <strong>{item.title}</strong>
                <Badge tone={item.tone === 'green' ? 'success' : 'warning'}>{item.tone || 'neutral'}</Badge>
              </div>
              <p>{item.detail}</p>
              <EvidenceExplorer evidence={item.evidence} title={item.title} />
            </div>
          ))}
        </div>
      </section>

      <section className="report-section">
        <h3>Comparative Table</h3>
        <DataTable columns={tableColumns} rows={tableRows} />
      </section>

      <section className="report-section">
        <h3>Heat Map</h3>
        <div className="report-heatmap">
          {report.heatmap.map((item) => (
            <div key={item.label} className="report-heatmap__cell" style={{ opacity: 0.4 + item.value / 120 }}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="report-section">
        <h3>Key Findings</h3>
        <ul className="report-list">
          {report.keyFindings.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="report-section">
        <h3>Data Quality Warnings</h3>
        <ul className="report-list report-list--warning">
          {report.dataQualityWarnings.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="report-section">
        <h3>Sources &amp; Citations</h3>
        <ul className="report-list">
          {report.sources.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="report-section">
        <h3>AI Recommendations</h3>
        <ul className="report-list">
          {report.recommendations.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
