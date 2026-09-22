export const topicsMock = {
  distribution: [
    { label: 'Production', value: 92, tone: 'green' },
    { label: 'Exploration', value: 84, tone: 'blue' },
    { label: 'Environment', value: 63, tone: 'amber' },
    { label: 'Coal Quality', value: 78, tone: 'purple' },
    { label: 'Reserves', value: 87, tone: 'green' },
    { label: 'Mine Development', value: 69, tone: 'cyan' },
    { label: 'Safety', value: 72, tone: 'red' },
    { label: 'Infrastructure', value: 58, tone: 'steel' },
  ],
  clusters: [
    {
      title: 'Production ramp-up',
      category: 'Production',
      summary: 'Coal production is accelerating in eastern and central districts with consistent extraction throughput.',
      intensity: 'High',
      score: 92,
    },
    {
      title: 'Resource conversion',
      category: 'Reserves',
      summary: 'Reserves and exploration activity are converting into actionable project pipelines and mine expansion.',
      intensity: 'High',
      score: 87,
    },
    {
      title: 'Environmental monitoring',
      category: 'Environment',
      summary: 'Environment-related commentary remains concentrated around active mining corridors and water-sensitive areas.',
      intensity: 'Medium',
      score: 63,
    },
    {
      title: 'Quality and safety',
      category: 'Safety',
      summary: 'Coal quality and safety signals remain layered with strong operational attention in mature regions.',
      intensity: 'Medium',
      score: 72,
    },
  ],
  trend: [
    { period: 'Jan', Production: 68, Exploration: 55, Environment: 40, 'Coal Quality': 52, Reserves: 58, 'Mine Development': 44, Safety: 46, Infrastructure: 39 },
    { period: 'Feb', Production: 72, Exploration: 57, Environment: 43, 'Coal Quality': 55, Reserves: 60, 'Mine Development': 47, Safety: 50, Infrastructure: 42 },
    { period: 'Mar', Production: 75, Exploration: 60, Environment: 46, 'Coal Quality': 58, Reserves: 64, 'Mine Development': 52, Safety: 53, Infrastructure: 46 },
    { period: 'Apr', Production: 78, Exploration: 62, Environment: 48, 'Coal Quality': 61, Reserves: 67, 'Mine Development': 55, Safety: 56, Infrastructure: 49 },
    { period: 'May', Production: 82, Exploration: 66, Environment: 52, 'Coal Quality': 63, Reserves: 71, 'Mine Development': 59, Safety: 58, Infrastructure: 53 },
    { period: 'Jun', Production: 86, Exploration: 70, Environment: 58, 'Coal Quality': 68, Reserves: 76, 'Mine Development': 64, Safety: 59, Infrastructure: 56 },
  ],
}

export default topicsMock
