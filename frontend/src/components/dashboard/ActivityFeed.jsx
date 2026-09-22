import Badge from '../ui/Badge'

const getTone = (type) => {
  if (type === 'ingestion') return 'neutral'
  if (type === 'validation') return 'success'
  if (type === 'verification') return 'warning'
  if (type === 'ai' || type === 'report') return 'neutral'
  return 'danger'
}

export default function ActivityFeed({ items }) {
  return (
    <div className="activity-feed">
      {items.map((item) => (
        <div key={item.id} className="activity-feed__item">
          <div className="activity-feed__icon">
            <Badge tone={getTone(item.type)}>{item.type}</Badge>
          </div>
          <div className="activity-feed__content">
            <div className="activity-feed__title">{item.title}</div>
            <div className="activity-feed__detail">{item.detail}</div>
          </div>
          <div className="activity-feed__time">{item.timestamp}</div>
        </div>
      ))}
    </div>
  )
}
