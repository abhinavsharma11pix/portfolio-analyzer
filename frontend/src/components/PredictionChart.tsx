import { useState } from 'react'
import axios from 'axios'
import {
  ComposedChart, Line, Area, XAxis, YAxis,
  Tooltip, Legend, ResponsiveContainer,
  ReferenceLine, CartesianGrid
} from 'recharts'
import {
  TrendingUp, TrendingDown, Brain,
  ChevronDown, ChevronUp, Zap, Shield
} from 'lucide-react'

/* -------------------- TYPES -------------------- */

interface ModelBreakdown {
  price_30d: number
  change_pct: number
  model_name: string
  weight: number
}

interface Reliability {
  score: number
  grade: string
  label: string
  n_models: number
  disagreement_pct: number
  breakdown: {
    agreement: number
    data_quality: number
    model_coverage: number
  }
}

interface PredictionData {
  symbol: string
  current_price: number
  predicted_price_7d: number
  predicted_price_30d: number
  predicted_change_pct_7d: number
  predicted_change_pct_30d: number
  confidence_high: number
  confidence_low: number
  reliability: Reliability
  model_breakdown: Record<string, ModelBreakdown>
  models_used: string[]
  historical: { date: string; price: number }[]
  forecast: { date: string; predicted: number; upper: number; lower: number }[]
  data_points: number
  elapsed_seconds: number
  from_cache: boolean
}

interface Props {
  symbol: string
  currency: string
}

/* -------------------- HELPERS -------------------- */

function safeNum(v: unknown): number {
  const n = Number(v)
  return isFinite(n) ? n : 0
}

function fmt(v: unknown, prefix: string): string {
  const n = safeNum(v)
  return n ? `${prefix}${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '—'
}

function ReliabilityBadge({ r }: { r: Reliability }) {
  const color =
    r.grade === 'A' ? 'text-green-400 bg-green-900/30 border-green-700' :
    r.grade === 'B' ? 'text-blue-400 bg-blue-900/30 border-blue-700' :
    r.grade === 'C' ? 'text-yellow-400 bg-yellow-900/30 border-yellow-700' :
                      'text-red-400 bg-red-900/30 border-red-700'

  return (
    <div className={`flex items-center gap-1.5 border px-2 py-1 rounded-lg text-xs ${color}`}>
      <Shield size={11} />
      <span className="font-semibold">{r.grade}</span>
      <span>{r.score.toFixed(0)}/100</span>
      <span className="opacity-60">· {r.label}</span>
    </div>
  )
}

/* -------------------- COMPONENT -------------------- */

export default function PredictionChart({ symbol, currency }: Props) {
  const [data, setData]       = useState<PredictionData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [showModels, setShowModels] = useState(false)

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
      date:       h.date.slice(5),
      historical: h.price,
      predicted:  null as number | null,
      upper:      null as number | null,
      lower:      null as number | null,
    })),
    // Bridge point
    {
      date:       data.historical[data.historical.length - 1].date.slice(5),
      historical: data.current_price,
      predicted:  data.current_price,
      upper:      data.current_price,
      lower:      data.current_price,
    },
    ...data.forecast.map(f => ({
      date:       f.date.slice(5),
      historical: null as number | null,
      predicted:  f.predicted,
      upper:      f.upper,
      lower:      f.lower,
    })),
  ] : []

  const isUp30 = (data?.predicted_change_pct_30d ?? 0) >= 0

  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden bg-gray-900/50">

      {/* ── Header (always visible) ── */}
      <button
        onClick={fetchPrediction}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Brain size={15} className="text-purple-400 shrink-0" />
          <span className="text-white font-medium text-sm">{symbol}</span>

          {data && (
            <>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                isUp30
                  ? 'bg-green-900/50 text-green-400'
                  : 'bg-red-900/50 text-red-400'
              }`}>
                {isUp30 ? '+' : ''}{data.predicted_change_pct_30d.toFixed(1)}% (30d)
              </span>
              <ReliabilityBadge r={data.reliability} />
              {data.from_cache && (
                <span className="text-xs text-gray-500 flex items-center gap-1">
                  <Zap size={10} /> cached
                </span>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          {loading && (
            <div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
          )}
          {!loading && (
            expanded
              ? <ChevronUp size={16} className="text-gray-400" />
              : <ChevronDown size={16} className="text-gray-400" />
          )}
        </div>
      </button>

      {/* ── Expanded Content ── */}
      {expanded && data && (
        <div className="border-t border-gray-800 px-5 pb-5">

          {/* Stat boxes */}
          <div className="grid grid-cols-3 gap-3 my-4">
            <div className="bg-gray-800/50 rounded-xl p-4">
              <p className="text-gray-400 text-xs mb-1">Current</p>
              <p className="text-white font-bold text-lg">
                {fmt(data.current_price, prefix)}
              </p>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-4">
              <p className="text-gray-400 text-xs mb-1">7-Day Forecast</p>
              <p className="text-white font-bold text-lg">
                {fmt(data.predicted_price_7d, prefix)}
              </p>
              <p className={`text-xs mt-0.5 ${
                data.predicted_change_pct_7d >= 0
                  ? 'text-green-400' : 'text-red-400'
              }`}>
                {data.predicted_change_pct_7d >= 0 ? '+' : ''}
                {data.predicted_change_pct_7d.toFixed(2)}%
              </p>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-4">
              <p className="text-gray-400 text-xs mb-1">30-Day Forecast</p>
              <p className="text-white font-bold text-lg">
                {fmt(data.predicted_price_30d, prefix)}
              </p>
              <p className={`text-xs mt-0.5 ${
                isUp30 ? 'text-green-400' : 'text-red-400'
              }`}>
                {isUp30 ? '+' : ''}{data.predicted_change_pct_30d.toFixed(2)}%
              </p>
            </div>
          </div>

          {/* Reliability breakdown */}
          <div className="bg-gray-800/30 rounded-xl p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Shield size={14} className="text-blue-400" />
                <span className="text-white text-sm font-medium">
                  Reliability: {data.reliability.grade} · {data.reliability.score.toFixed(0)}/100
                </span>
              </div>
              <span className="text-gray-500 text-xs">
                {data.reliability.n_models}/3 models · {data.data_points} data pts
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(data.reliability.breakdown).map(([k, v]) => (
                <div key={k}>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span className="capitalize">{k.replace('_', ' ')}</span>
                    <span>{v.toFixed(0)}</span>
                  </div>
                  <div className="bg-gray-700 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full bg-blue-500"
                      style={{ width: `${(v / 40) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            {data.reliability.disagreement_pct > 5 && (
              <p className="text-yellow-400 text-xs mt-2">
                ⚠️ Models disagree by {data.reliability.disagreement_pct.toFixed(1)}% — treat with caution
              </p>
            )}
          </div>

          {/* Model breakdown toggle */}
          <button
            onClick={() => setShowModels(!showModels)}
            className="text-xs text-gray-500 hover:text-gray-300 mb-3 flex items-center gap-1"
          >
            {showModels ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {showModels ? 'Hide' : 'Show'} model breakdown
          </button>

          {showModels && (
            <div className="grid grid-cols-3 gap-2 mb-4">
              {Object.entries(data.model_breakdown).map(([key, m]) => (
                <div key={key} className="bg-gray-800/50 rounded-lg p-3">
                  <p className="text-gray-400 text-xs mb-1">{m.model_name}</p>
                  <p className="text-white text-sm font-semibold">
                    {fmt(m.price_30d, prefix)}
                  </p>
                  <p className={`text-xs ${
                    m.change_pct >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {m.change_pct >= 0 ? '+' : ''}{m.change_pct.toFixed(2)}%
                  </p>
                  <p className="text-gray-600 text-xs mt-1">
                    Weight: {m.weight}%
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Main chart */}
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#6b7280', fontSize: 10 }}
                tickFormatter={(_, i) => i % 20 === 0 ? chartData[i]?.date || '' : ''}
                axisLine={{ stroke: '#374151' }}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 10 }}
                axisLine={{ stroke: '#374151' }}
                tickFormatter={v => `${prefix}${safeNum(v).toLocaleString()}`}
                domain={['auto', 'auto']}
                width={70}
              />
              <Tooltip
                formatter={(value, name) => {
                  const labels: Record<string, string> = {
                    historical: 'Historical',
                    predicted:  'Predicted',
                    upper:      'Upper Band',
                    lower:      'Lower Band',
                  }
                  return [
                    fmt(value, prefix),
                    labels[name as string] || String(name)
                  ]
                }}
                contentStyle={{
                  backgroundColor: '#111827',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: '12px',
                }}
              />
              <Legend
                formatter={v => (
                  <span className="text-gray-300 text-xs capitalize">{v}</span>
                )}
              />

              {/* Confidence band */}
              <Area
                dataKey="upper"
                stroke="none"
                fill="#7c3aed"
                fillOpacity={0.08}
                connectNulls={false}
                legendType="none"
              />
              <Area
                dataKey="lower"
                stroke="none"
                fill="#7c3aed"
                fillOpacity={0.08}
                connectNulls={false}
                legendType="none"
              />

              {/* Historical */}
              <Line
                dataKey="historical"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                name="historical"
              />

              {/* Forecast */}
              <Line
                dataKey="predicted"
                stroke="#a855f7"
                strokeWidth={2}
                strokeDasharray="6 3"
                dot={false}
                connectNulls={false}
                name="predicted"
              />

              {/* Today line */}
              <ReferenceLine
                x={data.historical[data.historical.length - 1].date.slice(5)}
                stroke="#6b7280"
                strokeDasharray="4 4"
                label={{ value: 'Today', fill: '#9ca3af', fontSize: 10 }}
              />
            </ComposedChart>
          </ResponsiveContainer>

          {/* Footer */}
          <p className="text-gray-600 text-xs mt-3 text-center">
            Ensemble ({data.models_used.join(' + ')}) ·
            {data.data_points} data pts ·
            {data.elapsed_seconds}s
            {data.from_cache ? ' · from cache' : ''}
            · Not financial advice
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-5 pb-4 text-red-400 text-sm border-t border-gray-800 pt-3">
          ⚠️ {error}
        </div>
      )}
    </div>
  )
}