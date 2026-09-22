const workflowSteps = [
  'Intent Detection',
  'Query Planning',
  'Multi-Source Retrieval',
  'Extraction / Calculation',
  'Cross-Validation',
  'Evidence Mapping',
  'Confidence Verification',
]

export default function StepIndicator({ activeStep = 0, loading = false }) {
  return (
    <div
      className="processing-verification-status"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 20px',
        margin: '16px 0',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 700, color: 'var(--navy-900)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ width: '16px', height: '16px', color: 'var(--steel-700)' }}>
            <path d="M10 3.2a6.8 6.8 0 0 1 6.8 6.8A6.8 6.8 0 0 1 10 16.8a6.8 6.8 0 0 1-6.8-6.8A6.8 6.8 0 0 1 10 3.2Z" />
            <path d="M7.2 10.3 9 12.1l3.8-4.6" />
          </svg>
          {loading ? 'Executing Multi-Source Extraction Pipeline...' : 'AI Audit & Verification Pipeline Complete'}
        </div>
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
          Step {Math.min(activeStep + 1, workflowSteps.length)} of {workflowSteps.length}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '4px' }}>
        {workflowSteps.map((step, index) => {
          const isDone = index < activeStep
          const isCurrent = loading && index === activeStep

          return (
            <div
              key={step}
              style={{
                flex: 1,
                minWidth: '95px',
                padding: '6px 8px',
                background: isCurrent ? 'var(--navy-800)' : isDone ? 'var(--surface-strong)' : 'transparent',
                color: isCurrent ? 'var(--white)' : isDone ? 'var(--text-primary)' : 'var(--text-muted)',
                border: isCurrent ? '1px solid var(--navy-900)' : '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: isCurrent || isDone ? 600 : 400,
                textAlign: 'center',
                whiteSpace: 'nowrap',
              }}
            >
              {isDone ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginRight: '4px' }} aria-hidden="true">
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px', height: '12px' }}>
                    <path d="M4 10.4 7.7 14l8.3-9.2" />
                  </svg>
                </span>
              ) : null}
              {step}
            </div>
          )
        })}
      </div>
    </div>
  )
}
