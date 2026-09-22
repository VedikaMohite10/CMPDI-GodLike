import Badge from '../ui/Badge'

const toneStyles = {
  green: 'evidence-chain__item--green',
  yellow: 'evidence-chain__item--yellow',
  orange: 'evidence-chain__item--orange',
  red: 'evidence-chain__item--red',
}

export default function EvidenceExplorer({ evidence, title }) {
  const chain = evidence?.evidenceChain || evidence || []

  return (
    <div className="evidence-explorer">
      <div className="evidence-explorer__header">
        <div>
          <div className="eyebrow">Evidence chain</div>
          <h3>{title || evidence?.title || 'Evidence Explorer'}</h3>
        </div>
      </div>

      <div className="evidence-chain">
        {chain.map((item, index) => (
          <div key={`${item.id || item.label}-${index}`} className={`evidence-chain__item ${toneStyles[item.tone] || ''}`}>
            <div className="evidence-chain__step">
              <span>Step {index + 1}</span>
              <Badge tone={item.tone === 'green' ? 'success' : item.tone === 'yellow' ? 'warning' : item.tone === 'orange' ? 'warning' : 'danger'}>
                {item.tone || 'neutral'}
              </Badge>
            </div>
            <div className="evidence-chain__label">{item.label}</div>
            <div className="evidence-chain__value">{item.value}</div>
            <div className="evidence-chain__confidence">
              Confidence <strong>{item.confidence}%</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
