import Card from '../ui/Card'

export default function TopicClusterCard({ cluster }) {
  return (
    <Card className="topic-cluster-card">
      <div className="topic-cluster-card__header">
        <h3>{cluster.title}</h3>
        <span className="topic-score">{cluster.score}%</span>
      </div>
      <p>{cluster.summary}</p>
      <div className="topic-cluster-card__footer">
        <span className="topic-intensity">{cluster.intensity}</span>
      </div>
    </Card>
  )
}
