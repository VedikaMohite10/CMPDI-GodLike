import Card from '../ui/Card'
import Badge from '../ui/Badge'

export default function DataQualityDashboard({ metrics }) {
  const sections = [
    {
      title: 'Ingestion & Volume',
      items: [
        { label: 'Documents processed', value: metrics.documentsProcessed.toLocaleString(), tone: 'neutral' },
        { label: 'Pages processed', value: metrics.pagesProcessed.toLocaleString(), tone: 'neutral' },
        { label: 'Tables extracted', value: metrics.tablesExtracted.toLocaleString(), tone: 'info' },
      ],
    },
    {
      title: 'Data Health & Accuracy',
      items: [
        { label: 'Extraction accuracy', value: `${metrics.extractionAccuracy}%`, tone: 'success' },
        { label: 'Low-confidence fields', value: metrics.lowConfidenceFields.toLocaleString(), tone: 'warning' },
        { label: 'Duplicate documents', value: metrics.duplicateDocuments.toLocaleString(), tone: 'danger' },
      ],
    },
    {
      title: 'Discrepancy & Reconciliation',
      items: [
        { label: 'Conflicting values', value: metrics.conflictingValues.toLocaleString(), tone: 'danger' },
        { label: 'Missing data fields', value: metrics.missingData.toLocaleString(), tone: 'warning' },
        { label: 'Human corrections', value: metrics.humanCorrections.toLocaleString(), tone: 'info' },
      ],
    },
    {
      title: 'Automation & Efficiency',
      items: [
        { label: 'Automation rate', value: `${metrics.automationPercent}%`, tone: 'success' },
        { label: 'Manual time reduction', value: metrics.manualTimeReduction, tone: 'success' },
        { label: 'Avg processing time', value: metrics.averageProcessingTime, tone: 'neutral' },
      ],
    },
  ]

  return (
    <div className="governance-dashboard" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 1. DATA TRUST SCORE Header Section (Stage D requirement) */}
      <Card className="governance-card" style={{ padding: '24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(240px, 1fr) minmax(280px, 1.2fr)', gap: '24px', alignItems: 'center' }}>
          <div>
            <p className="eyebrow">Institutional Data Monitoring System</p>
            <h2 style={{ margin: '4px 0 8px', fontSize: '22px', fontWeight: 800, color: 'var(--navy-900)' }}>
              DATA TRUST SCORE: {metrics.extractionAccuracy}%
            </h2>
            <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Current system data quality based on currently processed records across geological surveys, 
              subsidiary production registers, and official filings.
            </p>
            <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
              <Badge tone="success">96.4% Verified Accuracy</Badge>
              <Badge tone="neutral">81% Automated Extraction</Badge>
              <Badge tone="info">8 CIL Subsidiaries Covered</Badge>
            </div>
          </div>

          {/* Semi-circular arc gauge visual */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', padding: '16px', background: 'var(--surface-strong)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
            <svg width="120" height="70" viewBox="0 0 120 70" aria-hidden="true">
              <path d="M 10 65 A 50 50 0 0 1 110 65" fill="none" stroke="var(--border)" strokeWidth="10" strokeLinecap="round" />
              <path d="M 10 65 A 50 50 0 0 1 102 30" fill="none" stroke="var(--steel-700)" strokeWidth="10" strokeLinecap="round" />
            </svg>
            <div>
              <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--navy-900)' }}>{metrics.extractionAccuracy}%</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', fontWeight: 600 }}>System Data Trust Index</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--green-600)', marginTop: '4px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ width: '14px', height: '14px' }}>
                  <path d="M4 10.4 7.7 14l8.3-9.2" />
                </svg>
                Verified against CIL standards
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* 2. Key Quality Metrics (4 Structured Columns) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        {sections.map((section) => (
          <Card key={section.title} style={{ padding: '18px' }}>
            <h3 style={{ fontSize: 'var(--font-size-sm)', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', margin: '0 0 14px', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
              {section.title}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {section.items.map((item) => (
                <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>{item.label}</span>
                  <Badge tone={item.tone}>{item.value}</Badge>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* 3. Issues Requiring Attention Banner */}
      <Card style={{ padding: '18px 24px', background: 'var(--surface-strong)', borderLeft: '4px solid var(--amber-500)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--navy-900)' }}>
              Issues Requiring Review: {metrics.conflictingValues} Conflicting Values & {metrics.lowConfidenceFields} Low-Confidence Fields
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>
              Based on currently processed records. Open items have been routed to the human verification review queue.
            </div>
          </div>
          <Badge tone="warning">Pending Sign-off</Badge>
        </div>
      </Card>
    </div>
  )
}
