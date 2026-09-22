import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export default function TopicTrendChart({ data }) {
  return (
    <div className="topic-chart">
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="topicTrendFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="5%" stopColor="#3a709c" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#3a709c" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#dfe7f2" />
          <XAxis dataKey="period" stroke="#5d6b82" />
          <YAxis stroke="#5d6b82" />
          <Tooltip />
          <Area type="monotone" dataKey="Production" stroke="#295d8a" fill="url(#topicTrendFill)" strokeWidth={2.5} />
          <Area type="monotone" dataKey="Exploration" stroke="#4e74c9" fill="none" strokeWidth={2} />
          <Area type="monotone" dataKey="Environment" stroke="#d9962a" fill="none" strokeWidth={2} />
          <Area type="monotone" dataKey="Coal Quality" stroke="#8c5ad4" fill="none" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
