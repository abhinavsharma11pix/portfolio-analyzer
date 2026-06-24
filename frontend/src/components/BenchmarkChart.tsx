/**
 * components/BenchmarkChart.tsx
 * Portfolio return vs NIFTY50 / S&P500 comparison.
 * Uses existing /api/analytics/benchmark endpoint.
 *
 * Usage in Dashboard.tsx:
 *   import BenchmarkChart from './components/BenchmarkChart'
 *   <BenchmarkChart holdings={holdings} />
 */
import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine, CartesianGrid,
} from 'recharts'
import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'
import { apiClient } from '../services/api'

// ─── Types ────────────────────────────────────────────────────────────────────

interface BenchmarkPoint {
  date:      string
  portfolio: number
  benchmark: number
}

interface BenchmarkResult {
  portfolio_return:  number
  benchmark_return:  number
  alpha:             number
  beta:              number
  correlation:       number
  tracking_error:    number
  information_ratio: number
  chart_data:        BenchmarkPoint[]
  benchmark_name:    string
}

interface Props {
  holdings:   any[]
  className?: string
}

// ─── Constants ────────────────────────────────────────────────────────────────

const BENCHMARKS = [
  { value: '^NSEI',  label: 'NIFTY 50',  flag: '🇮🇳' },
  { value: '^BSESN', label: 'SENSEX',    flag: '🇮🇳' },
  { value: '^GSPC',  label: 'S&P 500',   flag: '🇺🇸' },
  { value: '^IXIC',  label: 'NASDAQ 100', flag: '🇺🇸' },
]

const PERIODS = [
  { value: '1M',  label: '1M' },
  { value: '3M',  label: '3M' },
  { value: '6M',  label: '6M' },
  { value: '1Y',  label: '1Y' },
  { value: '3Y',  label: '3Y' },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

function MetricCard({ label, value, sub, positive }: {
  label: string
  value: string
  sub?: string
  positive?: boolean
}) {
  return (
    <div className="bg-gray-800/40 rounded-xl p-3">
      <p className="text-gray-500 text-xs mb-1">{label}</p>
      <p className={`text-base font-bold tabular-nums ${
        positive === undefined ? 'text-white' :
        positive ? 'text-green-400' : 'text-red-400'
      }`}>
        {value}
      </p>
      {sub && <p className="text-gray-600 text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function BenchmarkChart({ holdings, className = '' }: Props) {
  const [data,      setData]      = useState<BenchmarkResult | null>(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [benchmark, setBenchmark] = useState('^NSEI')
  const [period,    setPeriod]    = useState('1Y')

  useEffect(() => {
    if (!holdings || holdings.length === 0) return
    let cancelled = false

    // FIX: renamed inner function from `fetch` (shadows global) to `loadData`
    const loadData = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await apiClient.post('/api/analytics/benchmark', {
          holdings,
          benchmark,
          period,   // FIX: added missing period parameter
        })
        if (!cancelled) setData(res.data)
      } catch (e: any) {
        if (!cancelled) setError(e.response?.data?.detail ?? 'Benchmark comparison failed')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadData()
    return () => { cancelled = true }
  }, [holdings, benchmark, period]) // FIX: added `period` to dependency array

  const isOutperforming = (data?.alpha ?? 0) > 0
  const benchmarkLabel  = BENCHMARKS.find(b => b.value === benchmark)?.label ?? benchmark

  // FIX: explicit empty-state instead of rendering nothing
  if (!holdings || holdings.length === 0) {
    return (
      <div className={`card p-5 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={16} className="text-blue-400" />
          <h3 className="text-white font-semibold text-sm">vs Benchmark</h3>
        </div>
        <div className="h-32 flex items-center justify-center text-gray-500 text-sm">
          Add holdings to see benchmark comparison
        </div>
      </div>
    )
  }

  return (
    <div className={`card p-5 ${className}`}>

      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <BarChart3 size={16} className="text-blue-400" />
          <h3 className="text-white font-semibold text-sm">vs Benchmark</h3>
          {data && !loading && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
              isOutperforming
                ? 'bg-green-900/30 text-green-400'
                : 'bg-red-900/30 text-red-400'
            }`}>
              {isOutperforming ? '↑ Outperforming' : '↓ Underperforming'}
            </span>
          )}
        </div>

        {/* Benchmark selector */}
        <div className="flex gap-1 flex-wrap">
          {BENCHMARKS.map(b => (
            <button
              key={b.value}
              onClick={() => setBenchmark(b.value)}
              className={`text-xs px-2.5 py-1 rounded-lg transition-all ${
                benchmark === b.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800/60 text-gray-400 hover:text-white'
              }`}
            >
              {b.flag} {b.label}
            </button>
          ))}
        </div>
      </div>

      {/* FIX: Period selector (was missing entirely) */}
      <div className="flex gap-1 mb-4">
        {PERIODS.map(p => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            className={`text-xs px-2.5 py-1 rounded-lg transition-all ${
              period === p.value
                ? 'bg-gray-600 text-white'
                : 'bg-gray-800/60 text-gray-400 hover:text-white'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div className="h-48 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* ── Error ── */}
      {error && !loading && (
        <div className="h-32 flex items-center justify-center text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* ── Data ── */}
      {data && !loading && (
        <>
          {/* Metric cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
            <MetricCard
              label="Your Return"
              value={`${data.portfolio_return >= 0 ? '+' : ''}${data.portfolio_return.toFixed(1)}%`}
              positive={data.portfolio_return >= 0}
            />
            <MetricCard
              label={`${benchmarkLabel} Return`}
              value={`${data.benchmark_return >= 0 ? '+' : ''}${data.benchmark_return.toFixed(1)}%`}
              positive={data.benchmark_return >= 0}
            />
            <MetricCard
              label="Alpha"
              value={`${data.alpha >= 0 ? '+' : ''}${data.alpha.toFixed(2)}%`}
              sub="Return above benchmark"
              positive={data.alpha >= 0}
            />
            <MetricCard
              label="Beta"
              value={data.beta.toFixed(2)}
              sub={
                data.beta > 1 ? 'More volatile' :
                data.beta < 1 ? 'Less volatile' :
                'Matches market'
              }
            />
          </div>

          {/* Line chart */}
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.chart_data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#6b7280', fontSize: 10 }}
                tickFormatter={v => v.slice(5)}   // "YYYY-MM-DD" → "MM-DD"
                axisLine={{ stroke: '#374151' }}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 10 }}
                axisLine={{ stroke: '#374151' }}
                tickFormatter={v => `${v >= 0 ? '+' : ''}${(v as number).toFixed(0)}%`}
                domain={['auto', 'auto']}
                width={52}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#111827',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: '12px',
                }}
                formatter={(v: any, name?: string | number) => [
                  `${(v as number) >= 0 ? '+' : ''}${(v as number).toFixed(1)}%`,
                  name === 'portfolio' ? 'Your Portfolio' : benchmarkLabel,
                ]}
              />
              <Legend
                formatter={v =>
                  // FIX: return a plain string to avoid ReactNode type mismatch warning
                  v === 'portfolio' ? 'Your Portfolio' : benchmarkLabel
                }
                wrapperStyle={{ fontSize: '12px', color: '#d1d5db' }}
              />
              <ReferenceLine y={0} stroke="#374151" />
              <Line
                dataKey="portfolio"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                name="portfolio"
              />
              <Line
                dataKey="benchmark"
                stroke="#9ca3af"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                name="benchmark"
              />
            </LineChart>
          </ResponsiveContainer>

          {/* Footer */}
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/[0.04]">
            <div className="flex items-center gap-2">
              {isOutperforming
                ? <TrendingUp  size={13} className="text-green-400" />
                : <TrendingDown size={13} className="text-red-400"  />
              }
              <span className={`text-xs ${isOutperforming ? 'text-green-400' : 'text-red-400'}`}>
                {Math.abs(data.alpha).toFixed(1)}%{' '}
                {isOutperforming ? 'above' : 'below'} {benchmarkLabel}
              </span>
            </div>
            {/* FIX: also surface tracking_error alongside the other stats */}
            <div className="flex gap-3 text-xs text-gray-600">
              <span>Correlation: {(data.correlation * 100).toFixed(0)}%</span>
              <span>Track. Err: {data.tracking_error.toFixed(2)}%</span>
              <span>Info Ratio: {data.information_ratio.toFixed(2)}</span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
