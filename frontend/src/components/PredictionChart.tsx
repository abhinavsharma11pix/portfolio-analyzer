import { useState } from 'react'
import axios from 'axios'
import {
  ComposedChart, Line, Area, XAxis, YAxis,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { TrendingUp, TrendingDown, Brain, ChevronDown, ChevronUp } from 'lucide-react'

interface PredictionData {
  symbol: string
  current_price: number
  predicted_price_30d: number
  predicted_change_pct_30d: number
  predicted_price_7d: number
  predicted_change_pct_7d: number
  confidence_high: number
  confidence_low: number
  historical: { date: string; price: number }[]
  forecast: { date: string; predicted: number; upper: number; lower: number }[]
  model: string
  data_points: number
}

interface Props {
  symbol: string
  currency: string
}

function StatBox({ label, value, change, prefix }: {
  label: string
  value: number
  change: number
  prefix: string
}) {
  const isUp = change >= 0
  return (
    <div className="bg-gray-800/50 rounded-xl p-4">
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className="text-white font-bold text-lg">{prefix}{value.toLocaleString()}</p>
      <p className={`text-sm font-medium flex items-center gap-1 mt-1 ${isUp ? 'text-green-400' : 'text-red-400'}`}>
        {isUp ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
        {isUp ? '+' : ''}{change.toFixed(2)}%
      </p>
    </div>
  )
}

export default function PredictionChart({ symbol, currency }: Props) {
  const [data, setData] = useState<PredictionData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)

  const prefix = currency === 'USD' ? '$' : '₹'

  const fetchPrediction = async () => {
    if (data) { setExpanded(!expanded); return }
    setLoading(true)
    setError(null)
    try {
      const res = await axios.get(
        `http://localhost:8000/api/portfolio/predict/${symbol}`
      )
      setData(res.data)
      setExpanded(true)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  // Merge historical + forecast for chart
  const chartData = data ? [
    ...data.historical.map(h => ({
      date: h.date.slice(5), // MM-DD
      historical: h.price,
      predicted: null,
      upper: null,
      lower: null,
    })),
    // Bridge point
    {
      date: data.historical[data.historical.length - 1].date.slice(5),
      historical: data.current_price,
      predicted: data.current_price,
      upper: data.current_price,
      lower: data.current_price,
    },
    ...data.forecast.map(f => ({
      date: f.date.slice(5),
      historical: null,
      predicted: f.predicted,
      upper: f.upper,
      lower: f.lower,
    }))
  ] : []

  // Show only every 10th label to avoid crowding
  const tickFormatter = (_: any, index: number) =>
    index % 15 === 0 ? chartData[index]?.date || '' : ''

  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={fetchPrediction}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Brain size={16} className="text-purple-400" />
          <span className="text-white font-medium text-sm">
            {symbol} — 30-Day AI Forecast
          </span>
          {data && (
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              data.predicted_change_pct_30d >= 0
                ? 'bg-green-900/50 text-green-400'
                : 'bg-red-900/50 text-red-400'
            }`}>
              {data.predicted_change_pct_30d >= 0 ? '+' : ''}
              {data.predicted_change_pct_30d.toFixed(1)}% expected
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {loading && (
            <div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
          )}
          {!loading && (expanded
            ? <ChevronUp size={16} className="text-gray-400" />
            : <ChevronDown size={16} className="text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && data && (
        <div className="px-5 pb-5 border-t border-gray-800">

          {/* Stat boxes */}
          <div className="grid grid-cols-3 gap-3 my-4">
            <StatBox
              label="Current Price"
              value={data.current_price}
              change={0}
              prefix={prefix}
            />
            <StatBox
              label="7-Day Forecast"
              value={data.predicted_price_7d}
              change={data.predicted_change_pct_7d}
              prefix={prefix}
            />
            <StatBox
              label="30-Day Forecast"
              value={data.predicted_price_30d}
              change={data.predicted_change_pct_30d}
              prefix={prefix}
            />
          </div>

          {/* Chart */}
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={chartData}>
              <XAxis
                dataKey="date"
                tick={{ fill: '#6b7280', fontSize: 10 }}
                tickFormatter={tickFormatter}
                axisLine={{ stroke: '#374151' }}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 10 }}
                axisLine={{ stroke: '#374151' }}
                tickFormatter={(v) => `${prefix}${v.toLocaleString()}`}
                domain={['auto', 'auto']}
                width={70}
              />
              <Tooltip
                formatter={(value, name) => {
                  const num = typeof value === 'number' ? value : 0
                  const labels: Record<string, string> = {
                    historical: 'Historical',
                    predicted: 'Predicted',
                    upper: 'Upper Band',
                    lower: 'Lower Band'
                  }
                  return [`${prefix}${num.toLocaleString()}`, labels[name as string] || name]
                }}
                contentStyle={{
                  backgroundColor: '#111827',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: '12px'
                }}
              />
              <Legend
                formatter={(value) => (
                  <span className="text-gray-300 text-xs capitalize">{value}</span>
                )}
              />

              {/* Confidence band */}
              <Area
                dataKey="upper"
                stroke="none"
                fill="#7c3aed"
                fillOpacity={0.1}
                connectNulls={false}
                legendType="none"
              />
              <Area
                dataKey="lower"
                stroke="none"
                fill="#7c3aed"
                fillOpacity={0.1}
                connectNulls={false}
                legendType="none"
              />

              {/* Historical line */}
              <Line
                dataKey="historical"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                name="historical"
              />

              {/* Prediction line */}
              <Line
                dataKey="predicted"
                stroke="#a855f7"
                strokeWidth={2}
                strokeDasharray="6 3"
                dot={false}
                connectNulls={false}
                name="predicted"
              />

              {/* Today marker */}
              <ReferenceLine
                x={data.historical[data.historical.length - 1].date.slice(5)}
                stroke="#6b7280"
                strokeDasharray="4 4"
                label={{ value: 'Today', fill: '#9ca3af', fontSize: 10 }}
              />
            </ComposedChart>
          </ResponsiveContainer>

          {/* Disclaimer */}
          <p className="text-gray-600 text-xs mt-3 text-center">
            ⚠️ {data.model} · {data.data_points} data points ·
            Predictions are probabilistic estimates, not financial advice.
          </p>
        </div>
      )}

      {error && (
        <div className="px-5 pb-4 text-red-400 text-sm border-t border-gray-800 pt-3">
          ⚠️ {error}
        </div>
      )}
    </div>
  )
}