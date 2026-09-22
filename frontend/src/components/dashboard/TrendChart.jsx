import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export default function TrendChart({ data }) {
  return (
    <div className="trend-chart">
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="docsTrendGradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="5%" stopColor="#123a3e" stopOpacity={0.28} />
              <stop offset="95%" stopColor="#123a3e" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#d7e0ea" />
          <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: '#53657b', fontSize: 12 }} />
          <YAxis tickLine={false} axisLine={false} tick={{ fill: '#53657b', fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              borderRadius: 12,
              border: '1px solid #d7e0ea',
              boxShadow: '0 8px 24px rgba(16, 31, 52, 0.08)',
            }}
          />
          <Area type="monotone" dataKey="value" stroke="#123a3e" fill="url(#docsTrendGradient)" strokeWidth={2.5} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
