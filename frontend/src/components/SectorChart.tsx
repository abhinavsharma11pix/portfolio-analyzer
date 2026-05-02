import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface Holding {
  symbol: string
  sector?: string
  current_value: number | null
  invested_value: number
}

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16']

export default function SectorChart({ holdings }: { holdings: Holding[] }) {
  if (!holdings || holdings.length === 0) return null

  const sectorMap: Record<string, number> = {}
  holdings.forEach(h => {
    const sector = h.sector || 'Unknown'
    const value = h.current_value ?? h.invested_value ?? 0
    sectorMap[sector] = (sectorMap[sector] || 0) + value
  })

  const data = Object.entries(sectorMap)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value: Math.round(value) }))

  if (data.length === 0) return null

  const total = data.reduce((sum, d) => sum + d.value, 0)

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
      <h3 className="text-white font-semibold text-lg mb-6">Sector Allocation</h3>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={70} outerRadius={110} paddingAngle={3} dataKey="value">
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
            <Tooltip
            formatter={(value) => {
              const num = typeof value === 'number' ? value : 0
              return [`₹${num.toLocaleString()} (${((num / total) * 100).toFixed(1)}%)`, 'Value']
            }}
            contentStyle={{
              backgroundColor: '#111827',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#fff'
            }}
          />
          <Legend formatter={(value) => <span className="text-gray-300 text-sm">{value}</span>} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}