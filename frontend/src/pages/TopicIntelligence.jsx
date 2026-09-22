import { useMemo, useState } from 'react'
import Card from '../components/ui/Card'
import WordCloud from '../components/topics/WordCloud'
import TopicClusterCard from '../components/topics/TopicClusterCard'
import TopicTrendChart from '../components/topics/TopicTrendChart'
import { EmptyState } from '../components/ui/StatePanel'
import { topicsMock } from '../data/topicsMock'

export default function TopicIntelligencePage({ hideHeader = false }) {
  const [selectedTopic, setSelectedTopic] = useState('Production')

  const filteredClusters = useMemo(
    () =>
      topicsMock.clusters.filter((cluster) => {
        const topicKey = selectedTopic.toLowerCase()
        const clusterText = `${cluster.title} ${cluster.summary} ${cluster.category || ''}`.toLowerCase()
        return clusterText.includes(topicKey)
      }),
    [selectedTopic],
  )

  return (
    <div className="topic-page">
      {!hideHeader && (
        <div className="page-header">
          <div>
            <p className="eyebrow">Topic Intelligence</p>
            <h1>Analytical topic tracking</h1>
          </div>
        </div>
      )}

      <div className="topic-grid">
        <Card className="topic-card">
          <div className="section-header">
            <div>
              <p className="eyebrow">Distribution</p>
              <h2>Current topic emphasis</h2>
            </div>
          </div>
          <WordCloud items={topicsMock.distribution} />
        </Card>

        <Card className="topic-card">
          <div className="section-header">
            <div>
              <p className="eyebrow">Historical trend</p>
              <h2>Topic evolution</h2>
            </div>
          </div>
          <TopicTrendChart data={topicsMock.trend} />
        </Card>
      </div>

      <div className="topic-filter-row">
        {topicsMock.distribution.map((item) => (
          <button
            key={item.label}
            type="button"
            className={`topic-filter ${selectedTopic === item.label ? 'is-active' : ''}`}
            onClick={() => setSelectedTopic(item.label)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="topic-cluster-grid">
        {filteredClusters.length === 0 ? (
          <EmptyState title="No clusters for this topic" description="Choose another emphasis filter to continue exploring the topic map." />
        ) : (
          filteredClusters.map((cluster) => <TopicClusterCard key={cluster.title} cluster={cluster} />)
        )}
      </div>
    </div>
  )
}
