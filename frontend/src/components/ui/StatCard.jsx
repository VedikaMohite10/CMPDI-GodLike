function StatIcon({ name }) {
  const commonProps = {
    width: 18,
    height: 18,
    viewBox: '0 0 20 20',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': 'true',
  }

  switch (name) {
    case 'documents':
      return (
        <svg {...commonProps}>
          <path d="M6 2.8h6l3 3v10.4a1.8 1.8 0 0 1-1.8 1.8H6A1.8 1.8 0 0 1 4.2 16.2V4.6A1.8 1.8 0 0 1 6 2.8Z" />
          <path d="M12 2.8v3.4h3.2" />
          <path d="M7 9.5h6M7 12.8h6" />
        </svg>
      )
    case 'gauge':
      return (
        <svg {...commonProps}>
          <path d="M4.5 13.5a5.5 5.5 0 1 1 11 0" />
          <path d="M10 10V6.7" />
          <path d="M10 10l2.8 2.5" />
          <path d="M3.5 15.2h13" />
        </svg>
      )
    case 'alert':
      return (
        <svg {...commonProps}>
          <path d="M10 3.4 16.2 15H3.8L10 3.4Z" />
          <path d="M10 7.3v4.2M10 12.9h.01" />
        </svg>
      )
    case 'clock':
      return (
        <svg {...commonProps}>
          <circle cx="10" cy="10" r="6.2" />
          <path d="M10 6v4.2l2.8 1.8" />
        </svg>
      )
    case 'check':
      return (
        <svg {...commonProps}>
          <path d="M4 10.4 7.7 14l8.3-9.2" />
        </svg>
      )
    default:
      return (
        <svg {...commonProps}>
          <circle cx="10" cy="10" r="5.8" />
        </svg>
      )
  }
}

export default function StatCard({
  label,
  value,
  change,
  tone = 'neutral',
  trend = 'up',
  icon,
}) {
  return (
    <div className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__header">
        <div className="stat-card__label">{label}</div>
        {icon ? (
          <div className={`stat-card__icon stat-card__icon--${tone}`}>
            <StatIcon name={icon} />
          </div>
        ) : null}
      </div>
      <div className="stat-card__value">{value}</div>
      <div className={`stat-card__change stat-card__change--${trend}`}>
        {change}
      </div>
    </div>
  )
}
