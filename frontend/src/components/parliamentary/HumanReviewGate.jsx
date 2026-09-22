function ReviewStateIcon({ tone }) {
  const commonProps = {
    viewBox: '0 0 20 20',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '1.8',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': 'true',
  }

  if (tone === 'success') {
    return (
      <svg {...commonProps}>
        <path d="M4 10.4 7.6 14l8.4-9.2" />
      </svg>
    )
  }

  if (tone === 'critical') {
    return (
      <svg {...commonProps}>
        <path d="M10 3.6v7.1M10 15.5h.01" />
        <path d="M3.8 15.6 10 4.4l6.2 11.2H3.8Z" />
      </svg>
    )
  }

  return (
    <svg {...commonProps}>
      <circle cx="10" cy="10" r="6.2" />
      <path d="M10 6.3v4.1M10 13.5h.01" />
    </svg>
  )
}

export default function HumanReviewGate({ review, onApprove, onRevisionRequest }) {
  const stateTone = review?.approved ? 'success' : review?.status === 'Revision requested' ? 'critical' : 'warning'
  const stateLabel = review?.approved ? 'Approved' : review?.status === 'Revision requested' ? 'Revision requested' : 'Awaiting review'

  return (
    <div className="parliamentary-card parliamentary-card--review">
      <div className="section-header">
        <div>
          <p className="eyebrow">Mandatory review</p>
          <h2>Human approval gate</h2>
        </div>
        <span className={`parliamentary-status parliamentary-status--${stateTone}`}>
          <span className="parliamentary-status__icon"><ReviewStateIcon tone={stateTone} /></span>
          {stateLabel}
        </span>
      </div>

      <div className="parliamentary-review__meta">
        <span>Reviewer</span>
        <strong>{review?.reviewer || 'Unassigned'}</strong>
        <span>Status</span>
        <strong>{review?.status || 'Awaiting approval'}</strong>
      </div>

      <div className="button-row">
        <button
          type="button"
          className="ui-button ui-button--success ui-button--md"
          onClick={onApprove}
          disabled={review?.approved}
        >
          Approve final response
        </button>
        <button type="button" className="ui-button ui-button--secondary ui-button--md" onClick={onRevisionRequest}>
          Request revision
        </button>
      </div>

      <p className="parliamentary-review__note">
        Final response state is not available until a human reviewer explicitly approves the draft.
      </p>
    </div>
  )
}
