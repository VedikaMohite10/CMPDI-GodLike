import Button from '../ui/Button'

export default function QueryInput({ question, onChange, onSubmit, examples, loading }) {
  return (
    <div className="query-composer-section">
      <div className="section-header" style={{ marginBottom: '10px' }}>
        <div>
          <p className="eyebrow">Conversational Research Assistant</p>
          <h2 style={{ fontSize: '20px', fontWeight: 700, margin: '2px 0 0', color: 'var(--text-primary)' }}>
            Ask a question about CMPDI / CIL data
          </h2>
        </div>
        <span className="ui-badge ui-badge--neutral">1,48,640 Document Records Indexed</span>
      </div>

      <div
        className="query-composer-box"
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-md)',
          padding: '16px',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <textarea
          value={question}
          onChange={(event) => onChange(event.target.value)}
          rows={3}
          placeholder="e.g. Compare production of CCL, WCL and SECL over the last five years, or ask about coal reserves and quality metrics..."
          className="query-composer-textarea"
          style={{
            width: '100%',
            border: '0',
            background: 'transparent',
            resize: 'vertical',
            fontSize: 'var(--font-size-md)',
            color: 'var(--text-primary)',
            outline: 'none',
            minHeight: '70px',
            fontFamily: 'inherit',
          }}
        />

        <div
          className="query-composer-actions"
          style={{
            display: 'flex',
            justify: 'space-between',
            alignItems: 'center',
            paddingTop: '12px',
            borderTop: '1px solid var(--border-subtle)',
            marginTop: '8px',
          }}
        >
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Executes multi-subsidiary extraction, calculation & verification pipeline
          </span>
          <Button onClick={onSubmit} disabled={loading} variant="primary">
            {loading ? 'Processing Query...' : 'Run Research Search'}
          </Button>
        </div>
      </div>

      <div className="query-suggestions" style={{ marginTop: '16px' }}>
        <div
          style={{
            fontSize: 'var(--font-size-xs)',
            fontWeight: 700,
            color: 'var(--text-secondary)',
            marginBottom: '8px',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          Suggested Research Queries
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {examples.map((example) => (
            <button
              key={example.id}
              type="button"
              className="suggestion-chip"
              onClick={() => onChange(example.question)}
              style={{
                border: '1px solid var(--border)',
                background: 'var(--surface)',
                color: 'var(--text-primary)',
                borderRadius: 'var(--radius-sm)',
                padding: '6px 12px',
                fontSize: 'var(--font-size-sm)',
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'background 0.15s ease, border-color 0.15s ease',
              }}
            >
              {example.question}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
