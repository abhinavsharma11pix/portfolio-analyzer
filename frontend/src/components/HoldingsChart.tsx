import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts'

interface Holding {
  symbol: string
  invested_value: number
  current_value: number | null
}

export default function HoldingsChart({ holdings }: { holdings: Holding[] }) {
  if (!holdings || holdings.length === 0) return null

  const data = holdings
    .filter(h => h.invested_value > 0)
    .map(h => ({
      symbol: h.symbol.replace('.NS', '').replace('.BO', ''),
      Invested: h.invested_value || 0,
      Current: h.current_value ?? h.invested_value ?? 0,
    }))

  if (data.length === 0) return null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
      <h3 className="text-white font-semibold text-lg mb-6">Holdings Breakdown</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} barGap={4}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="symbol" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={{ stroke: '#374151' }} />
          <YAxis
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={{ stroke: '#374151' }}
            tickFormatter={(v) => v >= 1000 ? `₹${(v / 1000).toFixed(0)}K` : `₹${v}`}
          />
          <Tooltip
            formatter={(value) => {
              const num = typeof value === 'number' ? value : 0
              return [`₹${num.toLocaleString()}`, '']
            }}
            contentStyle={{
              backgroundColor: '#111827',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#fff'
            }}
          />
          <Legend formatter={(value) => <span className="text-gray-300 text-sm">{value}</span>} />
          <Bar dataKey="Invested" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Current" fill="#10b981" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}