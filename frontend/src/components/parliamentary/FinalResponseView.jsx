import EvidenceExplorer from '../evidence/EvidenceExplorer'

export default function FinalResponseView({ response, question, evidenceRefs = [] }) {
  const evidence = response?.evidence || { evidenceChain: [] }

  return (
    <div className="parliamentary-card parliamentary-card--final">
      <div className="parliamentary-response__header">
        <div>
          <p className="eyebrow">Final approved output</p>
          <h2>{response?.title || 'Final Cited Response'}</h2>
        </div>
        <span className="parliamentary-status parliamentary-status--final">Final</span>
      </div>

      <div className="parliamentary-response__meta">
        <span>Question</span>
        <p>{question}</p>
      </div>

      <div className="parliamentary-response__summary">
        <strong>Final response</strong>
        <p>{response?.summary}</p>
      </div>

      <div className="parliamentary-response__confidence">
        <span>Confidence</span>
        <strong>{response?.confidence || 0}%</strong>
      </div>

      <div className="parliamentary-facts">
        {(response?.facts || []).map((fact) => (
          <div key={fact.label} className="parliamentary-fact">
            <span>{fact.label}</span>
            <strong>{fact.value}</strong>
            <small>{fact.detail}</small>
          </div>
        ))}
      </div>

      <div className="parliamentary-evidence-links">
        {evidenceRefs.map((ref) => (
          <a key={ref} href={`#${ref}`}>
            {ref}
          </a>
        ))}
      </div>

      <div className="parliamentary-divider" />
      <EvidenceExplorer evidence={evidence} title={evidence.title || 'Evidence chain'} />
    </div>
  )
}
