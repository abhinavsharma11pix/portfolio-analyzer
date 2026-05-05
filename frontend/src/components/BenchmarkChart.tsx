import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  Legend, ResponsiveContainer, CartesianGrid, ReferenceLine
} from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface BenchmarkResult {
  name: string
  portfolio_return: number
  benchmark_return: number
  outperformance: number
  portfolio_vol: number
  benchmark_vol: number
  beta: number
  beating: boolean
  chart_data: { date: string; portfolio: number; benchmark: number }[]
}

interface Props {
  holdings: any[]
}

function safeFormat(value: unknown): string {
  const num = typeof value === 'number' ? value : Number(value)
  return isFinite(num) ? num.toFixed(2) : '—'
}

function safePercent(value: number): string {
  if (!isFinite(value)) return '—'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

export default function BenchmarkChart({ holdings }: Props) {
  const [data, setData]         = useState<Record<string, BenchmarkResult> | null>(null)
  const [loading, setLoading]   = useState(false)
  const [selected, setSelected] = useState<string>('nifty50')
  const [error, setError]       = useState<string | null>(null)

  useEffect(() => {
    if (!holdings?.length) return

    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await axios.post(
          'http://localhost:8000/api/analytics/benchmark',
          { holdings }
        )
        setData(res.data)
      } catch {
        setError('Could not load benchmark data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [holdings])

  if (loading) return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center">
      <div className="w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
      <p className="text-gray-400 text-sm">Comparing vs benchmarks...</p>
    </div>
  )

  if (error) return (
    <div className="bg-gray-900 border border-red-800 rounded-2xl p-4 text-red-400 text-sm">
      ⚠️ {error}
    </div>
  )

  if (!data || !Object.keys(data).length) return null

  const current = data[selected]
  if (!current) return null

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-white font-semibold text-lg">
          📊 Benchmark Comparison
        </h3>
        <div className="flex gap-2">
          {Object.entries(data).map(([key, val]) => (
            <button
              key={key}
              onClick={() => setSelected(key)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                selected === key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {val.name}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-800/50 rounded-xl p-3">
          <p className="text-gray-500 text-xs mb-1">Your Return</p>
          <p className={`text-xl font-bold ${
            current.portfolio_return >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {safePercent(current.portfolio_return)}
          </p>
        </div>

        <div className="bg-gray-800/50 rounded-xl p-3">
          <p className="text-gray-500 text-xs mb-1">{current.name}</p>
          <p className={`text-xl font-bold ${
            current.benchmark_return >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {safePercent(current.benchmark_return)}
          </p>
        </div>

        <div className="bg-gray-800/50 rounded-xl p-3">
          <p className="text-gray-500 text-xs mb-1">Outperformance</p>
          <p className={`text-xl font-bold flex items-center gap-1 ${
            current.beating ? 'text-green-400' : 'text-red-400'
          }`}>
            {current.beating
              ? <TrendingUp size={16} />
              : <TrendingDown size={16} />
            }
            {safePercent(current.outperformance)}
          </p>
        </div>

        <div className="bg-gray-800/50 rounded-xl p-3">
          <p className="text-gray-500 text-xs mb-1">Beta</p>
          <p className="text-xl font-bold text-blue-400">
            {safeFormat(current.beta)}
          </p>
        </div>
      </div>

      {/* Chart */}
      {current.chart_data?.length > 0 && (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={current.chart_data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="date"
              tick={{ fill: '#6b7280', fontSize: 10 }}
              tickFormatter={(v) => v.slice(5)}
              axisLine={{ stroke: '#374151' }}
            />
            <YAxis
              tick={{ fill: '#6b7280', fontSize: 10 }}
              axisLine={{ stroke: '#374151' }}
              tickFormatter={(v) => safeFormat(v)}
            />
            <Tooltip
              formatter={(value, name) => [
                safeFormat(value),
                name === 'portfolio' ? 'Your Portfolio' : current.name
              ]}
              contentStyle={{
                backgroundColor: '#111827',
                border: '1px solid #374151',
                borderRadius: '8px',
                color: '#fff',
                fontSize: '12px'
              }}
            />
            <ReferenceLine y={100} stroke="#374151" strokeDasharray="4 4" />
            <Legend
              formatter={(v) => (
                <span className="text-gray-300 text-xs">
                  {v === 'portfolio' ? 'Your Portfolio' : current.name}
                </span>
              )}
            />
            <Line
              dataKey="portfolio"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
            />
            <Line
              dataKey="benchmark"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
              strokeDasharray="5 3"
            />
          </LineChart>
        </ResponsiveContainer>
      )}

    </div>
  )
}